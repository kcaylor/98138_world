"""A dataset registry whose download entries are the committed small fixtures (feature 004, FR-025).

Moved from ``tests/conftest.py`` in feature 016 (research R9) so that the CLI tests
(``fixture_registry``) and the kit golden harness (``python -m maptemplates kit-golden
--fixtures``) place exactly the same fixture files under the same registry ids and versions.

``make_fixture_registry(root)`` writes ``root/datasets.json``: the packaged registry with each
fixture dataset's row pointed at its file in ``tests/fixtures/datasets/`` (size, SHA-256 and, where
the fixture differs from the source, format, grid or variables). It does not activate it: the
caller points ``lego_image_processor.datasets.registry.REGISTRY_PATH`` at ``registry_path`` and the
cache at ``cache_dir`` (``LEGO_IMAGE_PROCESSOR_CACHE``), then calls ``place_all``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union

FIXTURE_DATASETS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "datasets"

FixtureFiles = Union[Path, List[Path]]


class FixtureRegistry:
    """A registry whose download entries are the committed fixtures (same ids and versions)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.cache_dir = self.root / "cache"
        self.registry_path = self.root / "datasets.json"
        self.files: Dict[str, FixtureFiles] = {}

    def place(self, dataset_id: str) -> Path:
        """Copy the fixture into the cache as if it had been fetched."""
        from lego_image_processor.datasets import cached_path, get_entry

        e = get_entry(dataset_id)
        dest = cached_path(e, self.cache_dir)
        src = self.files[dataset_id]
        if isinstance(src, list):  # feature 013: a multi-file entry (dest is its directory)
            dest.mkdir(parents=True, exist_ok=True)
            for f in src:
                shutil.copyfile(f, dest / f.name)
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        return dest

    def place_all(self):
        for i in self.files:
            self.place(i)
        return self


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def point_rows_at_fixtures(data: dict, fixtures: Path = FIXTURE_DATASETS) -> Dict[str, FixtureFiles]:
    """Point the fixture datasets' rows of registry ``data`` (changed in place) at the committed
    fixtures; return dataset id -> fixture file (or files, for a multi-file entry)."""
    files: Dict[str, FixtureFiles] = {}
    etopo = fixtures / "etopo2022_1deg.npy"
    ersst = fixtures / "ersst_v5_annual_2deg.nc"
    months = {"ersst-v5-1997-12": fixtures / "ersst_v5_199712_ssta.nc",  # feature 009
              "ersst-v5-1988-12": fixtures / "ersst_v5_198812_ssta.nc"}
    npp = fixtures / "mod17a3_npp_1deg.tif"       # feature 012
    chla = fixtures / "modis_chla_4deg_6mo.nc"    # feature 012
    gpcp = fixtures / "gpcp_v23_ltm_10deg.nc"     # feature 013
    nsidc = sorted(fixtures.glob("nsidc_cdr_v6_*_4x.nc"))  # feature 013: 4 of the 60 files
    for row in data["datasets"]:
        if row["id"] == "etopo2022-surface-10m":
            row.update(format="npy", filename=etopo.name, size=etopo.stat().st_size, sha256=_sha(etopo),
                       grid={"lat": [-90, 90], "lon": [-180, 180]})
            files[row["id"]] = etopo
        elif row["id"] == "ersst-v5-ltm-1991-2020":
            row.update(filename=ersst.name, size=ersst.stat().st_size, sha256=_sha(ersst),
                       variables={"sst": {"units": "degC"}})
            files[row["id"]] = ersst
        elif row["id"] in months:
            f = months[row["id"]]
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f))
            files[row["id"]] = f
        elif row["id"] == "mod17a3-npp-mean-2000-2015":  # feature 012: 1 degree, read as 2x2 blocks
            row.update(filename=npp.name, size=npp.stat().st_size, sha256=_sha(npp),
                       grid={**row.get("grid", {}), "block": 2})
            files[row["id"]] = npp
        elif row["id"] == "modis-aqua-chla-2013-2024":  # feature 012: content checksum of the fixture
            from lego_image_processor.datasets.readers import netcdf3_content_sha256
            row.update(filename=chla.name, size=chla.stat().st_size,
                       content_sha256=netcdf3_content_sha256(chla, "chlor_a"))
            files[row["id"]] = chla
        elif row["id"] == "gpcp-v23-ltm-1991-2020":
            row.update(filename=gpcp.name, size=gpcp.stat().st_size, sha256=_sha(gpcp))
            files[row["id"]] = gpcp
        elif row["id"] == "nsidc-cdr-v6-seaice-minimum-1991-2020":
            row["files"] = [{"url": f"https://noaadata.apps.nsidc.org/NOAA/G02202_V6/fixture/{f.name}",
                             "size": f.stat().st_size, "sha256": _sha(f)} for f in nsidc]
            row["size"] = sum(f.stat().st_size for f in nsidc)
            files[row["id"]] = nsidc
    return files


def make_fixture_registry(root: Path, registry_path: Optional[Path] = None) -> FixtureRegistry:
    """Write ``root/datasets.json`` (the packaged registry, or ``registry_path``, with the fixture
    rows) and return its ``FixtureRegistry``; nothing is activated or placed yet."""
    from lego_image_processor.datasets import registry as reg

    data = json.loads(Path(registry_path or reg.REGISTRY_PATH).read_text(encoding="utf-8"))
    fr = FixtureRegistry(root)
    fr.root.mkdir(parents=True, exist_ok=True)
    fr.files = point_rows_at_fixtures(data)
    fr.registry_path.write_text(json.dumps(data), encoding="utf-8")
    return fr
