"""Ice regions of a map template: ``maptemplates ice-mask ID [--check]`` (feature 016, T074;
FR-020b; research R18; contracts/template-file.md "Ice file").

The kit's rules (``maps/ice.py``) at the template's own stud locations: land ice on land studs in
Antarctica (south of 60° S) and the Greenland box without Iceland; sea ice on ocean studs whose
1991-2020 warmest-month mean SST (the ERSST values forward-binned into the stud, as maps reproject)
is at or below -1.5 °C, or that have no ERSST value and lie poleward of 60°. The file records the
template's layout digest, so confirming the template leaves ``--check`` passing. Offline and
without pyproj: the synthetic template fixture and a small 12-month netCDF-3 file stand in for the
real template and the pinned ERSST v5 file; one test checks the committed package file against
the cached pinned ERSST file when it is present.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner
from scipy.io import netcdf_file

import lego_image_processor.templates as templates
from lego_image_processor.datasets import registry
from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.datasets.readers import read_netcdf3
from lego_image_processor.maps.ice import LAND_ICE_REGIONS, SEA_ICE_RULE, in_region, load_template_ice
from lego_image_processor.templates import load_template, load_template_file
from maptemplates import document, ice, testing
from maptemplates.__main__ import main

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
ERSST_ID = SEA_ICE_RULE["dataset"]
MISSING = -9.96921e36
LAT = np.arange(-88.0, 89.0, 2.0)          # the ERSST v5 2-degree nodes
LON = np.arange(0.0, 360.0, 2.0)


def _last(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


# --- a small 12-month ERSST stand-in ---------------------------------------------------------

def _field() -> np.ndarray:
    """(12, lat, lon) monthly SST: 10 °C plus a month offset (the warmest month is the max), -1.8 °C
    in every month north of 70° N, no value south of 56° S, and no value in an equatorial box
    (10° S - 10° N, 150° E - 160° W)."""
    lat, lon = LAT[:, None], LON[None, :]
    base = np.full((LAT.size, LON.size), 10.0)
    months = np.stack([base + 0.1 * m for m in range(12)])
    months[:, LAT >= 70.0, :] = -1.8
    missing = (lat <= -56.0) | ((np.abs(lat) <= 10.0) & (lon >= 150.0) & (lon <= 200.0))
    months[:, np.broadcast_to(missing, base.shape)] = MISSING
    return months.astype(np.float32)


def _write_netcdf(path: Path, data: np.ndarray) -> Path:
    f = netcdf_file(str(path), "w")
    f.createDimension("time", data.shape[0])
    f.createDimension("lat", data.shape[1])
    f.createDimension("lon", data.shape[2])
    la = f.createVariable("lat", "f4", ("lat",))
    la[:] = LAT
    lo = f.createVariable("lon", "f4", ("lon",))
    lo[:] = LON
    v = f.createVariable("sst", "f4", ("time", "lat", "lon"))
    v.missing_value = np.float32(MISSING)
    v.units = "degC"
    v[:] = data
    f.close()
    return path


def _grid(data: np.ndarray) -> SourceGrid:
    """The warmest-month field as ``read_netcdf3(..., reduce="monthly-max")`` gives it."""
    with tempfile.TemporaryDirectory() as d:
        p = _write_netcdf(Path(d) / "s.nc", data)
        return read_netcdf3(p, "sst", reduce="monthly-max")


@pytest.fixture
def ersst(tmp_path, monkeypatch):
    """A 12-month stand-in for the pinned ERSST v5 file, and a registry whose ERSST entry pins it
    (size and SHA-256), so ``--dataset FILE`` verifies."""
    path = _write_netcdf(tmp_path / "sst.mon.ltm.1991-2020.nc", _field())
    data = json.loads((registry.DATA_DIR / "datasets.json").read_text(encoding="utf-8"))
    for row in data["datasets"]:
        if row["id"] == ERSST_ID:
            row.update(size=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    reg = tmp_path / "datasets.json"
    reg.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(registry, "REGISTRY_PATH", reg)
    return path


@pytest.fixture
def template_dir(tmp_path):
    """The synthetic confirmed template in a template directory of its own (its ice file too)."""
    d = tmp_path / "templates"
    testing.confirmed_copy(Path(__file__).resolve().parents[2] / "fixtures" / "templates", d, "2026-11-23")
    with testing.use_template_dir(d):
        yield d


@pytest.fixture
def runner():
    return CliRunner()


# --- the rules ---------------------------------------------------------------------------------

class TestRules:
    def test_land_ice_by_the_kit_regions_at_stud_locations(self, template_dir):
        t = load_template("winkel-tripel")
        lat, lon = t.locations()
        want = np.zeros(t.land.shape, dtype=bool)
        for r, c in zip(*np.nonzero(t.land)):
            want[r, c] = any(in_region(lat[r, c], lon[r, c], reg) for reg in LAND_ICE_REGIONS)
        got = ice.land_ice_mask(t)
        assert (got == want).all()
        assert got.any() and not (got & ~t.land).any()
        # every land stud south of 60 S is Antarctica's
        south = t.land & (lat < -60.0)
        assert south.any() and got[south].all()

    def test_sea_ice_cold_or_unobserved_polar(self, template_dir):
        t = load_template("winkel-tripel")
        lat, lon = t.locations()
        sea = ice.sea_ice_mask(_grid(_field()), t)
        ocean = np.array(t.ocean)
        assert not (sea & ~ocean).any()
        assert sea[ocean & (lat >= 74.0)].all()                  # frozen all year
        assert sea[ocean & (lat <= -60.0)].all()                 # no value, poleward of 60
        assert (ocean & (lat <= -60.0)).any() and (ocean & (lat >= 74.0)).any()
        assert not sea[(lat > -56.0) & (lat < 66.0)].any()       # warm or no value near the equator
        box = ocean & (np.abs(lat) <= 6.0) & ((lon >= 156.0) | (lon <= -166.0))
        assert box.any() and not sea[box].any()

    def test_threshold_is_inclusive(self, template_dir):
        """Every ocean stud with an ERSST node is sea ice at exactly -1.5 °C; a stud no node falls in
        (studs are smaller than the 2-degree grid in places) has no value: sea ice only poleward of 60."""
        t = load_template("winkel-tripel")
        data = np.full((12, LAT.size, LON.size), SEA_ICE_RULE["max_value"], dtype=np.float32)
        grid = _grid(data)
        sea = ice.sea_ice_mask(grid, t)
        cells = t.grid_projection.cells_for(grid.lat[:, None], grid.lon[None, :])
        nodes = np.bincount(cells[cells >= 0], minlength=t.width * t.height).reshape(t.height, t.width)
        lat, _ = t.locations()
        ocean = np.asarray(t.ocean)
        assert sea[ocean & (nodes > 0)].all()
        no_node = ocean & (nodes == 0)
        assert no_node.any()
        assert (sea[no_node] == (np.abs(lat[no_node]) >= 60.0)).all()
        assert not (sea & ~ocean).any()

    def test_forward_binning(self, template_dir):
        """One very cold node makes exactly the stud it falls in (by the forward projection) sea ice."""
        t = load_template("winkel-tripel")
        proj = t.grid_projection
        lat_s, lon_s = t.locations()
        lon180 = (LON + 180.0) % 360.0 - 180.0
        cells = proj.cells_for(LAT[:, None], lon180[None, :])
        mid = (np.abs(LAT) < 40.0)[:, None] & (cells >= 0)
        ocean_flat = np.asarray(t.ocean).ravel()
        pick = np.argwhere(mid & ocean_flat[np.where(cells >= 0, cells, 0)])
        i, j = map(int, pick[len(pick) // 2])
        stud = int(cells[i, j])
        data = np.full((12, LAT.size, LON.size), 5.0, dtype=np.float32)
        data[:, i, j] = -100.0
        sea = ice.sea_ice_mask(_grid(data), t)
        hit = np.flatnonzero(sea.ravel() & (np.abs(lat_s.ravel()) < 60.0))
        assert hit.tolist() == [stud]

    def test_derive_both(self, template_dir):
        t = load_template("winkel-tripel")
        regions = ice.derive(t, _grid(_field()))
        assert (regions.land == ice.land_ice_mask(t)).all()
        assert (regions.sea == ice.sea_ice_mask(_grid(_field()), t)).all()

    def test_kit_is_not_a_template_here(self):
        with pytest.raises(ValueError, match="kit31203 ice-mask"):
            ice.land_ice_mask(templates.kit_template())


# --- the command ---------------------------------------------------------------------------

class TestCommand:
    def test_writes_the_ice_file(self, runner, template_dir, ersst):
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output
        assert _last(r.output) == DISCLAIMER
        path = template_dir / "winkel-tripel-ice.json"
        t = load_template("winkel-tripel")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert path.read_text(encoding="utf-8") == document.ice_to_text(data)
        assert data["format_version"] == "1" and data["template_id"] == "winkel-tripel"
        assert data["grid"] == {"width": 128, "height": 80,
                                "coordinates": "board, row-major index = row * 128 + column"}
        src = data["source"]
        assert src["template_layout_sha256"] == t.layout_sha256 != t.file_sha256
        assert src["generator"].startswith("cli/tools/maptemplates ice-mask")
        assert src["disclaimer"] == DISCLAIMER
        assert src["land_ice"]["regions"] == [dict(x) for x in LAND_ICE_REGIONS]
        assert src["sea_ice"]["dataset"]["id"] == ERSST_ID
        assert {k: src["sea_ice"][k] for k in ("variable", "reduce", "max_value", "unobserved_lat")} == \
            {k: SEA_ICE_RULE[k] for k in ("variable", "reduce", "max_value", "unobserved_lat")}
        for name in ("land_ice", "sea_ice"):
            assert data[name]["count"] == len(data[name]["cells"]) > 0
            assert data[name]["cells"] == sorted(data[name]["cells"])
        regions = load_template_ice(t)
        assert not (regions.land & ~t.land).any() and not (regions.sea & ~t.ocean).any()
        assert (regions.land == ice.land_ice_mask(t)).all()
        assert f"land ice: {data['land_ice']['count']:,} studs" in r.output
        assert f"sea ice: {data['sea_ice']['count']:,} studs" in r.output

    def test_check_after_write(self, runner, template_dir, ersst):
        assert runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)]).exit_code == 0
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output
        assert "no differences" in r.output and _last(r.output) == DISCLAIMER

    def test_check_writes_nothing(self, runner, template_dir, ersst):
        path = template_dir / "winkel-tripel-ice.json"
        before = path.read_bytes()        # the synthetic fixture's ice file (other rules)
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 1
        assert "difference: " in r.output and _last(r.output) == DISCLAIMER
        assert path.read_bytes() == before

    def test_confirming_the_template_keeps_check_passing(self, runner, template_dir, ersst):
        assert runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)]).exit_code == 0
        tpath = template_dir / "winkel-tripel.json"
        before = load_template_file(tpath)
        doc = json.loads(tpath.read_text(encoding="utf-8"))
        doc["confirmation"] = {"role": "project owner", "date": "2026-12-24"}
        tpath.write_text(document.to_text(doc), encoding="utf-8")
        after = load_template_file(tpath)
        assert after.file_sha256 != before.file_sha256 and after.layout_sha256 == before.layout_sha256
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output
        assert "no differences" in r.output

    def test_unconfirmed_template(self, runner, template_dir, ersst):
        tpath = template_dir / "winkel-tripel.json"
        doc = json.loads(tpath.read_text(encoding="utf-8"))
        doc["confirmation"] = None
        tpath.write_text(document.to_text(doc), encoding="utf-8")
        assert load_template("winkel-tripel").status == "unconfirmed"
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output

    @pytest.mark.parametrize("change", ["cell", "digest"])
    def test_check_names_differences(self, runner, template_dir, ersst, change):
        assert runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)]).exit_code == 0
        path = template_dir / "winkel-tripel-ice.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if change == "cell":
            data["sea_ice"]["cells"] = data["sea_ice"]["cells"][1:]
            data["sea_ice"]["count"] -= 1
            expect = "sea_ice"
        else:
            data["source"]["template_layout_sha256"] = "0" * 64
            expect = "source.template_layout_sha256"
        path.write_text(document.ice_to_text(data), encoding="utf-8")
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 1
        assert f"difference: {expect}" in r.output and _last(r.output) == DISCLAIMER

    def test_check_without_a_file(self, runner, template_dir, ersst):
        (template_dir / "winkel-tripel-ice.json").unlink()
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 1 and "does not exist" in r.output
        assert _last(r.output) == DISCLAIMER

    def test_rewrite_keeps_the_date_when_nothing_changed(self, runner, template_dir, ersst):
        assert runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)]).exit_code == 0
        path = template_dir / "winkel-tripel-ice.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source"]["generated_on"] = "2026-01-02"
        path.write_text(document.ice_to_text(data), encoding="utf-8")
        assert runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)]).exit_code == 0
        assert json.loads(path.read_text(encoding="utf-8"))["source"]["generated_on"] == "2026-01-02"

    def test_needs_no_pyproj(self, runner, template_dir, ersst, monkeypatch):
        monkeypatch.setitem(sys.modules, "pyproj", None)     # any import of pyproj fails
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check", "--dataset", str(ersst)])
        assert r.exit_code == 0, r.output

    def test_kit_and_unknown_ids(self, runner, template_dir):
        r = runner.invoke(main, ["ice-mask", "kit-31203"])
        assert r.exit_code == 2 and "kit31203 ice-mask" in r.output
        r = runner.invoke(main, ["ice-mask", "mollweide"])
        assert r.exit_code == 2 and "winkel-tripel" in r.output

    def test_missing_dataset(self, runner, template_dir, tmp_path):
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--cache-dir", str(tmp_path / "empty")])
        assert r.exit_code == 4, r.output
        assert ERSST_ID in r.output and _last(r.output) == DISCLAIMER

    def test_checksum_mismatch(self, runner, template_dir, tmp_path):
        bogus = tmp_path / "sst.nc"
        bogus.write_bytes(b"not the pinned file")
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--dataset", str(bogus)])
        assert r.exit_code == 4, r.output
        assert _last(r.output) == DISCLAIMER


# --- the committed package file ----------------------------------------------------------

PACKAGE_DIR = Path(templates.__file__).resolve().parent.parent / "data" / "templates"


def test_package_ice_file_matches_the_package_template():
    path = PACKAGE_DIR / "winkel-tripel-ice.json"
    t = load_template_file(PACKAGE_DIR / "winkel-tripel.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.read_text(encoding="utf-8") == document.ice_to_text(data)
    assert data["template_id"] == t.id
    assert data["source"]["template_layout_sha256"] == t.layout_sha256
    entry = registry.load_registry(registry.DATA_DIR / "datasets.json").get(ERSST_ID)
    ds = data["source"]["sea_ice"]["dataset"]
    assert (ds["id"], ds["version"], ds["sha256"]) == (entry.id, entry.version, entry.sha256)
    regions = load_template_ice(t)
    assert regions.land.sum() == data["land_ice"]["count"] > 0
    assert regions.sea.sum() == data["sea_ice"]["count"] > 0
    assert (regions.land == ice.land_ice_mask(t)).all()        # the land rule needs no dataset


def test_package_ice_file_is_reproducible(runner):
    """``ice-mask winkel-tripel --check`` on the package files, with the cached pinned ERSST file."""
    from lego_image_processor.datasets import cache

    entry = registry.load_registry(registry.DATA_DIR / "datasets.json").get(ERSST_ID)
    if not cache.cached_path(entry).is_file():
        pytest.skip("the pinned ERSST v5 1991-2020 file is not cached")
    with testing.use_template_dir(PACKAGE_DIR):
        r = runner.invoke(main, ["ice-mask", "winkel-tripel", "--check"])
    assert r.exit_code == 0, r.output
    assert "no differences" in r.output and _last(r.output) == DISCLAIMER
