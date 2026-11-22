"""Dataset registry (FR-007, FR-011; data-model.md DatasetEntry)."""

import copy

import pytest

from lego_image_processor.datasets.registry import (
    RegistryError, get_entry, load_registry, parse_registry,
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
        downloads = [e for e in reg.entries if e.kind == "download"]
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
