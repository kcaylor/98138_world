"""Dataset registry (FR-007, FR-011; data-model.md DatasetEntry)."""

import copy

import pytest

from lego_image_processor.datasets.registry import (
    RegistryError, get_entry, load_registry, parse_entry, parse_registry,
)

GOOD = {
    "registry_version": "1",
    "source": {"title": "t", "generated_on": "2026-11-22",
               "disclaimer": "Not affiliated with or endorsed by The LEGO Group."},
    "datasets": [{
        "id": "a", "version": "1", "kind": "download", "title": "A", "publisher": "P",
        "url": "https://example.invalid/a.nc", "size": 10, "sha256": "0" * 64,
        "format": "netcdf3", "filename": "a.nc", "variables": {"v": {"units": "K"}},
        "class_rule": {"missing_is_land": True}, "license": "Public domain", "citation": "C.",
    }],
}


def _with(**changes):
    data = copy.deepcopy(GOOD)
    data["datasets"][0].update(changes)
    return data


class TestShipped:
    def test_loads(self):
        reg = load_registry()
        ids = [e.id for e in reg.entries]
        assert {"etopo2022-surface-10m", "ersst-v5-ltm-1991-2020", "kit31203-design"} <= set(ids)

    def test_downloads_are_small_open_and_pinned(self):
        reg = load_registry()
        # feature 012 entries are checked in TestLivingPlanetEntries (large, NASA open data)
        downloads = [e for e in reg.entries if e.kind == "download" and e.id not in LIVING_PLANET]
        assert len(downloads) >= 2
        for e in downloads:
            assert e.url.startswith("https://")
            assert e.size < 20_000_000
            assert len(e.sha256) == 64
            assert "public domain" in e.license.lower()
            assert e.citation and e.doi
        assert sum(e.size for e in downloads) < 15_000_000

    def test_get_entry(self):
        assert get_entry("etopo2022-surface-10m").size == 9_357_398
        assert get_entry("ersst-v5-ltm-1991-2020").sha256.startswith("b4f20ecf")
        with pytest.raises(KeyError):
            get_entry("nope")


class TestRules:
    def test_good(self):
        assert parse_registry(GOOD).entries[0].id == "a"

    def test_duplicate_ids(self):
        data = copy.deepcopy(GOOD)
        data["datasets"].append(copy.deepcopy(data["datasets"][0]))
        with pytest.raises(RegistryError, match="duplicate"):
            parse_registry(data)

    @pytest.mark.parametrize("field", ["url", "size", "sha256", "filename"])
    def test_download_needs(self, field):
        data = copy.deepcopy(GOOD)
        del data["datasets"][0][field]
        with pytest.raises(RegistryError, match=field):
            parse_registry(data)

    def test_http_rejected(self):
        with pytest.raises(RegistryError, match="https"):
            parse_registry(_with(url="http://example.invalid/a"))

    def test_bad_sha(self):
        with pytest.raises(RegistryError, match="sha256"):
            parse_registry(_with(sha256="ABC"))

    @pytest.mark.parametrize("field", ["license", "citation"])
    def test_license_and_citation_required(self, field):
        with pytest.raises(RegistryError, match=field):
            parse_registry(_with(**{field: ""}))

    def test_unknown_format(self):
        with pytest.raises(RegistryError, match="format"):
            parse_registry(_with(format="grib"))

    def test_unknown_class_rule(self):
        with pytest.raises(RegistryError, match="class_rule"):
            parse_registry(_with(class_rule={"magic": 1}))


ENSO = {
    "ersst-v5-1997-12": ("v5-1997-12", "ersst.v5.199712.nc",
                         "9f96dbe3aadf8b261e607a8337de02425c65e67803929c592bf1271b2c4e9ebe"),
    "ersst-v5-1988-12": ("v5-1988-12", "ersst.v5.198812.nc",
                         "f6d21ff447213c6abd32ee32bb1a4a26b5d847a5abb3dee33baed3f250bb14db"),
}


class TestEnsoEntries:
    """Feature 009: the two ERSST v5 per-month files (contracts/datasets.md)."""

    @pytest.mark.parametrize("dataset_id", sorted(ENSO))
    def test_pinned_entry(self, dataset_id):
        version, filename, sha = ENSO[dataset_id]
        e = get_entry(dataset_id)
        assert e.version == version
        assert e.kind == "download" and e.format == "netcdf3"
        assert e.size == 134_832 and e.sha256 == sha
        assert e.filename == filename
        assert e.url == f"https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/netcdf/{filename}"
        assert set(e.variables) == {"ssta"}
        assert e.variables["ssta"]["units"] == "degC"
        assert "reduce" not in e.variables["ssta"]
        assert e.class_rule == {"missing_is_land": True}
        assert e.doi == "10.1175/JCLI-D-16-0836.1"
        assert "10.7289/V5T72FNM" in e.citation
        assert "No constraints on data access or use" in e.license
        assert "NCEI" in e.publisher


LIVING_PLANET = ("mod17a3-npp-mean-2000-2015", "modis-aqua-chla-2013-2024")


class TestLivingPlanetEntries:
    """Feature 012: the two pinned datasets of the living-planet map (FR-001)."""

    def test_npp_entry(self):
        e = get_entry("mod17a3-npp-mean-2000-2015")
        assert e.kind == "download" and e.format == "geotiff"
        assert e.url.startswith("http://files.ntsg.umt.edu/") and e.http_only
        assert e.size == 384_939_658
        assert e.sha256 == "cba00628246f0d0030f5ab86a52f3d0ffed5e6bfb31a9580b959483522e8ffef"
        assert e.grid["block"] == 12
        assert e.variables["npp"]["scale_factor"] == 0.1 and e.variables["npp"]["fill"] == 65535
        assert e.class_rule == {"land_from": {"dataset": "etopo2022-surface-10m", "variable": "z",
                                              "split_at": 0.0}}
        assert e.mask_dataset_id == "etopo2022-surface-10m" and e.splits_land
        assert "Zhao" in e.citation and e.doi == "10.1016/j.rse.2004.12.011"
        assert e.license

    def test_chla_entry(self):
        e = get_entry("modis-aqua-chla-2013-2024")
        assert e.kind == "download" and e.format == "netcdf3"
        assert e.url.startswith("https://coastwatch.pfeg.noaa.gov/erddap/griddap/erdMH1chlamday_R2022SQ.nc?")
        assert e.size == 147_236_600 and e.sha256 == "" and len(e.content_sha256) == 64
        assert e.variables["chlor_a"]["reduce"] == "climatology-mean"
        assert e.doi == "10.5067/AQUA/MODIS/L3M/CHL/2022" and "R2022.0" in e.citation
        assert "content_sha256" in e.provenance()


def _row(**kw):
    row = {"id": "x", "version": "1", "kind": "download", "title": "t", "format": "netcdf3",
           "license": "l", "citation": "c", "url": "https://example.org/x.nc", "size": 10,
           "sha256": "a" * 64, "filename": "x.nc"}
    row.update(kw)
    return {k: v for k, v in row.items() if v is not None}


class TestRegistryRules012:
    def test_geotiff_block(self):
        assert parse_entry(_row(format="geotiff", grid={"block": 12})).grid["block"] == 12
        for bad in (0, -1, 1.5, True):
            with pytest.raises(RegistryError, match="grid.block"):
                parse_entry(_row(format="geotiff", grid={"block": bad}))

    def test_geotiff_variable_numbers(self):
        with pytest.raises(RegistryError, match="scale_factor must be a number"):
            parse_entry(_row(format="geotiff", variables={"v": {"scale_factor": "0.1"}}))

    def test_http_needs_reason_and_sha(self):
        with pytest.raises(RegistryError, match="https"):
            parse_entry(_row(url="http://example.org/x.nc"))
        e = parse_entry(_row(url="http://example.org/x.nc", http_only="host has no TLS"))
        assert e.http_only == "host has no TLS"
        with pytest.raises(RegistryError, match="needs sha256"):
            parse_entry(_row(url="http://example.org/x.nc", http_only="r", sha256=None,
                             content_sha256="b" * 64))
        with pytest.raises(RegistryError, match="only for http"):
            parse_entry(_row(http_only="r"))
        with pytest.raises(RegistryError, match="https"):
            parse_entry(_row(url="ftp://example.org/x.nc", http_only="r"))

    def test_content_sha256(self):
        e = parse_entry(_row(sha256=None, content_sha256="b" * 64))
        assert e.content_sha256 == "b" * 64 and e.sha256 == ""
        with pytest.raises(RegistryError, match="exactly one"):
            parse_entry(_row(content_sha256="b" * 64))
        with pytest.raises(RegistryError, match="exactly one"):
            parse_entry(_row(sha256=None))
        with pytest.raises(RegistryError, match="netcdf3 files only"):
            parse_entry(_row(format="npy", sha256=None, content_sha256="b" * 64,
                             grid={"lat": [-90, 90], "lon": [-180, 180]}))
        with pytest.raises(RegistryError, match="64 lowercase"):
            parse_entry(_row(sha256=None, content_sha256="B" * 64))

    def test_climatology_mean_reduce(self):
        e = parse_entry(_row(variables={"chl": {"reduce": "climatology-mean"}}))
        assert e.variables["chl"]["reduce"] == "climatology-mean"
        with pytest.raises(RegistryError, match="needs format netcdf3"):
            parse_entry(_row(format="geotiff", variables={"chl": {"reduce": "climatology-mean"}}))

    def test_land_from_rule(self):
        lf = {"dataset": "m", "variable": "z", "split_at": 0}
        e = parse_entry(_row(class_rule={"land_from": lf}))
        assert e.mask_dataset_id == "m" and e.splits_land
        for bad in ({"dataset": "m"}, {"dataset": "m", "variable": "z", "split_at": "0"},
                    {"dataset": 3, "variable": "z", "split_at": 0}, "m"):
            with pytest.raises(RegistryError, match="land_from"):
                parse_entry(_row(class_rule={"land_from": bad}))
        with pytest.raises(RegistryError, match="another dataset"):
            parse_entry(_row(class_rule={"land_from": {**lf, "dataset": "x"}}))

    def test_land_from_target_must_exist_and_be_plain(self):
        lf = {"dataset": "m", "variable": "z", "split_at": 0}
        with pytest.raises(RegistryError, match="unknown dataset"):
            parse_registry({"datasets": [_row(class_rule={"land_from": lf})]})
        chained = _row(id="m", class_rule={"land_from": {**lf, "dataset": "n"}})
        with pytest.raises(RegistryError, match="plain gridded field"):
            parse_registry({"datasets": [_row(class_rule={"land_from": lf}), chained, _row(id="n")]})
        reg = parse_registry({"datasets": [_row(class_rule={"land_from": lf}), _row(id="m")]})
        assert reg.get("x").mask_dataset_id == "m"
