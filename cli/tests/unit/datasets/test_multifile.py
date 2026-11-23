"""netCDF-4 and multi-file registry entries, cache and reading (feature 013: FR-001, FR-003, FR-008).

Not affiliated with or endorsed by The LEGO Group.
"""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from tests.conftest import FakeResponse
from lego_image_processor.datasets import cache as cache_mod
from lego_image_processor.datasets.cache import (ChecksumMismatchError, DatasetNotCachedError,
                                                 cached_path, fetch, is_cached, resolve)
from lego_image_processor.datasets.readers import read_dataset
from lego_image_processor.datasets.registry import RegistryError, get_entry, parse_entry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "datasets"
NSIDC_FILES = sorted(FIXTURES.glob("nsidc_cdr_v6_*_4x.nc"))


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _files(blobs):
    return [{"url": f"https://example.org/d/f{i}.nc", "size": len(b), "sha256": _sha(b)}
            for i, b in enumerate(blobs)]


def _row(blobs=(b"aaaa", b"bbbbbb"), **kw):
    row = {"id": "multi", "version": "1", "kind": "download", "title": "t", "format": "netcdf4",
           "license": "l", "citation": "c", "url": "https://example.org/d/",
           "size": sum(len(b) for b in blobs), "files": _files(blobs),
           "variables": {"v": {"reduce": "climatology-mean"}}}
    row.update(kw)
    return {k: v for k, v in row.items() if v is not None}


class TestRegistryRules:
    def test_netcdf4_single_file(self):
        e = parse_entry({"id": "one", "version": "1", "kind": "download", "title": "t", "format": "netcdf4",
                         "license": "l", "citation": "c", "url": "https://example.org/x.nc", "size": 1,
                         "sha256": "a" * 64, "filename": "x.nc",
                         "variables": {"v": {"reduce": "annual-mean"}}})
        assert e.format == "netcdf4" and not e.files and e.files_sha256 == ""

    def test_files_entry(self):
        e = parse_entry(_row())
        assert [f.name for f in e.files] == ["f0.nc", "f1.nc"] and e.size == 10
        prov = e.provenance()
        assert prov["files"] == 2 and len(prov["files_sha256"]) == 64 and "sha256" not in prov
        manifest = "".join(f"{f['sha256']}  f{i}.nc\n" for i, f in enumerate(_files((b"aaaa", b"bbbbbb"))))
        assert e.files_sha256 == _sha(manifest.encode())

    @pytest.mark.parametrize("change,match", [
        ({"files": _files([b"a"]), "size": 1}, "at least 2"),
        ({"files": [{"url": "https://e/a", "size": 1}, {"url": "https://e/b", "size": 1, "sha256": "a" * 64}]},
         r"\{url, size, sha256\}"),
        ({"files": [{"url": "ftp://e/a", "size": 1, "sha256": "a" * 64},
                    {"url": "https://e/b", "size": 1, "sha256": "a" * 64}], "size": 2}, "url must use https"),
        ({"files": [{"url": "https://e/a", "size": 0, "sha256": "a" * 64},
                    {"url": "https://e/b", "size": 1, "sha256": "a" * 64}]}, "positive integer"),
        ({"files": [{"url": "https://e/a", "size": 1, "sha256": "x"},
                    {"url": "https://e/b", "size": 1, "sha256": "a" * 64}], "size": 2}, "64 lowercase hex"),
        ({"files": [{"url": "https://e/a", "size": 1, "sha256": "a" * 64},
                    {"url": "https://f/a", "size": 1, "sha256": "a" * 64}], "size": 2}, "unique"),
        ({"size": 11}, "total of the files"),
        ({"sha256": "a" * 64}, "leave out sha256"),
        ({"kind": "local", "path": "/x", "sha256": None}, "download entries only"),
        ({"http_only": "reason"}, "http_only is only for http"),
    ])
    def test_files_rules(self, change, match):
        with pytest.raises(RegistryError, match=match):
            parse_entry(_row(**change))

    def test_climatology_mean_formats(self):
        parse_entry(_row())  # netcdf4 is fine
        with pytest.raises(RegistryError, match="netcdf3 or netcdf4"):
            parse_entry({"id": "g", "version": "1", "kind": "download", "title": "t", "format": "geotiff",
                         "license": "l", "citation": "c", "url": "https://e/x.tif", "size": 1,
                         "sha256": "a" * 64, "filename": "x.tif", "variables": {"v": {"reduce": "climatology-mean"}}})


class TestShippedEntries:
    def test_gpcp(self):
        e = get_entry("gpcp-v23-ltm-1991-2020")
        assert e.format == "netcdf4" and e.url == "https://downloads.psl.noaa.gov/Datasets/gpcp/precip.mon.ltm.1991-2020.nc"
        assert e.size == 677_810
        assert e.sha256 == "e72475e6687f1a6f940ce89e6645b80c241a47515b03e56d0009d3aa0cf6281c"
        assert e.variables["precip"]["reduce"] == "annual-mean" and e.variables["precip"]["units"] == "mm/day"
        assert "Adler" in e.citation and e.doi == "10.3390/atmos9040138" and "public domain" in e.license.lower()
        assert e.acknowledgement

    def test_nsidc(self):
        e = get_entry("nsidc-cdr-v6-seaice-minimum-1991-2020")
        assert e.format == "netcdf4" and len(e.files) == 60 and e.size == 17_826_152 < 20_000_000
        names = [f.name for f in e.files]
        north = [n for n in names if n.startswith("sic_psn25_")]
        south = [n for n in names if n.startswith("sic_pss25_")]
        assert [n[10:16] for n in north] == [f"{y}09" for y in range(1991, 2021)]
        assert [n[10:16] for n in south] == [f"{y}02" for y in range(1991, 2021)]
        assert all(n.endswith("_v06r00.nc") for n in names)
        assert all(f.url.startswith("https://noaadata.apps.nsidc.org/NOAA/G02202_V6/") for f in e.files)
        assert e.variables["cdr_seaice_conc_monthly"]["reduce"] == "climatology-mean"
        assert e.doi == "10.7265/b18j-z797" and "Meier" in e.citation and e.license


@pytest.fixture
def entry(tmp_path):
    blobs = [p.read_bytes() for p in NSIDC_FILES]
    row = _row(blobs=blobs, variables={"cdr_seaice_conc_monthly": {"reduce": "climatology-mean"}})
    row["files"] = [{"url": f"https://example.org/d/{p.name}", "size": len(b), "sha256": _sha(b)}
                    for p, b in zip(NSIDC_FILES, blobs)]
    return parse_entry(row), dict(zip((f"https://example.org/d/{p.name}" for p in NSIDC_FILES), blobs))


class TestCache:
    def test_paths_status_and_resolve(self, entry, tmp_path):
        e, by_url = entry
        d = cached_path(e, tmp_path)
        assert d == tmp_path / "datasets" / "multi" / "1"
        assert not is_cached(e, tmp_path)
        with pytest.raises(DatasetNotCachedError):
            resolve(e, tmp_path)
        d.mkdir(parents=True)
        for url, b in list(by_url.items())[:3]:
            (d / url.rsplit("/", 1)[1]).write_bytes(b)
        assert not is_cached(e, tmp_path)                       # one file missing
        with pytest.raises(DatasetNotCachedError, match="multi"):
            resolve(e, tmp_path)
        last_url, last = list(by_url.items())[3]
        (d / last_url.rsplit("/", 1)[1]).write_bytes(b"x" * len(last))   # right size, wrong bytes
        assert is_cached(e, tmp_path)
        with pytest.raises(ChecksumMismatchError, match="SHA-256 mismatch"):
            resolve(e, tmp_path)

    def test_fetch_downloads_only_missing_or_bad(self, entry, tmp_path):
        e, by_url = entry
        calls = []

        def opener(url, *a, **k):
            calls.append(url)
            return FakeResponse(by_url[url])

        d, downloaded = fetch(e, cache_dir=tmp_path, opener=opener)
        assert downloaded and len(calls) == 4 and resolve(e, tmp_path) == d
        calls.clear()
        assert fetch(e, cache_dir=tmp_path, opener=opener) == (d, False) and calls == []
        bad = d / NSIDC_FILES[1].name
        bad.write_bytes(b"0" * bad.stat().st_size)
        _, downloaded = fetch(e, cache_dir=tmp_path, opener=opener)
        assert downloaded and calls == [f"https://example.org/d/{NSIDC_FILES[1].name}"]
        resolve(e, tmp_path)

    def test_fetch_mismatch_leaves_no_part(self, entry, tmp_path):
        e, _ = entry
        with pytest.raises(ChecksumMismatchError):
            fetch(e, cache_dir=tmp_path, opener=lambda url, *a, **k: FakeResponse(b"z" * 10))
        assert not list(cached_path(e, tmp_path).glob("*.part"))

    def test_read_dataset_multi_file(self, entry, tmp_path):
        e, by_url = entry
        fetch(e, cache_dir=tmp_path, opener=lambda url, *a, **k: FakeResponse(by_url[url]))
        g = read_dataset(e, resolve(e, tmp_path), "cdr_seaice_conc_monthly")
        assert g.points and g.steps == 4 and np.nanmax(g.values) <= 1.0


def test_dataset_cli_info_and_fetch(fixture_registry, monkeypatch):
    from click.testing import CliRunner

    from lego_image_processor.cli.main import cli

    by_url = {}
    for f, p in zip(get_entry("nsidc-cdr-v6-seaice-minimum-1991-2020").files,
                    fixture_registry.files["nsidc-cdr-v6-seaice-minimum-1991-2020"]):
        by_url[f.url] = p.read_bytes()
    monkeypatch.setattr(cache_mod, "_default_opener", lambda url, *a, **k: FakeResponse(by_url[url]))
    r = CliRunner().invoke(cli, ["dataset", "fetch", "nsidc-cdr-v6-seaice-minimum-1991-2020"])
    assert r.exit_code == 0, r.output
    assert "(4 files, " in r.output and "SHA-256 verified" in r.output
    r = CliRunner().invoke(cli, ["dataset", "info", "nsidc-cdr-v6-seaice-minimum-1991-2020"])
    assert r.exit_code == 0 and "files:" in r.output and "(cached)" in r.output
    assert "Not affiliated with or endorsed by The LEGO Group." in r.output
