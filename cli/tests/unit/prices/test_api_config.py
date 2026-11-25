"""BrickLink API reference data `data/bricklink_api.json` (011 T025; data-model.md ApiConfig)."""

import copy
import json

import pytest

from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.prices.api_config import (API_CONFIG_PATH, ApiConfig, load_api_config,
                                                    parse_api_config)


@pytest.fixture
def raw():
    return json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))


def test_packaged_file_loads():
    api = load_api_config()
    assert isinstance(api, ApiConfig)
    assert api.base_url == "https://api.bricklink.com/api/store/v1"
    assert api.price_guide_path == "/items/{type}/{no}/price"
    assert api.item_types == {"P": "PART"}
    assert api.oauth == {"version": "1.0", "signature_method": "HMAC-SHA1", "realm": ""}
    assert api.daily_request_limit == 5000
    assert api.checked is False
    assert api.source["disclaimer"] == DISCLAIMER
    ids = [d["id"] for d in api.source["documentation"]]
    assert ids == ["bricklink-api-price-guide", "bricklink-api-auth", "bricklink-api-errors",
                   "bricklink-api-terms"]


def test_price_guide_url_and_snapshot_block():
    api = load_api_config()
    assert api.price_guide_url("P", "98138") == "https://api.bricklink.com/api/store/v1/items/PART/98138/price"
    assert api.endpoint == "GET /items/{type}/{no}/price"
    block = api.snapshot_block()
    assert list(block) == ["base_url", "endpoint", "documentation", "checked"]
    assert block["documentation"][0]["id"] == "bricklink-api-price-guide"
    assert block["checked"] is False


def test_file_matches_the_contract_exactly(raw):
    assert list(raw) == ["format_version", "source", "base_url", "price_guide_path", "item_types",
                         "oauth", "daily_request_limit"]
    assert list(raw["source"]) == ["title", "documentation", "accessed", "checked", "note", "disclaimer"]


def _bad(raw, mutate):
    data = copy.deepcopy(raw)
    mutate(data)
    with pytest.raises(ValueError) as info:
        parse_api_config(data)
    return str(info.value)


@pytest.mark.parametrize("field, value", [
    ("base_url", "http://api.bricklink.com/api/store/v1"),
    ("base_url", "https://api.bricklink.com/api/store/v1/"),
    ("base_url", "https://api.bricklink.com/api/store/v1?x=1"),
    ("base_url", ""),
    ("price_guide_path", "/items/PART/{no}/price"),
    ("price_guide_path", "/items/{type}/price"),
    ("price_guide_path", "items/{type}/{no}/price"),
])
def test_bad_url_fields(raw, field, value):
    assert field in _bad(raw, lambda d: d.__setitem__(field, value))


def test_item_types_need_p_to_part(raw):
    assert "item_types" in _bad(raw, lambda d: d.__setitem__("item_types", {"P": "MINIFIG"}))
    assert "item_types" in _bad(raw, lambda d: d.__setitem__("item_types", {}))


@pytest.mark.parametrize("key, value", [("version", "1.0a"), ("signature_method", "PLAINTEXT"),
                                        ("signature_method", "RSA-SHA1")])
def test_oauth_version_and_method(raw, key, value):
    assert f"oauth.{key}" in _bad(raw, lambda d: d["oauth"].__setitem__(key, value))


@pytest.mark.parametrize("value", [0, -1, "5000", True, 1.5])
def test_daily_limit(raw, value):
    assert "daily_request_limit" in _bad(raw, lambda d: d.__setitem__("daily_request_limit", value))


@pytest.mark.parametrize("key", ["documentation", "accessed", "checked", "disclaimer", "title"])
def test_source_requires(raw, key):
    assert f"source.{key}" in _bad(raw, lambda d: d["source"].pop(key))


def test_source_rules(raw):
    assert "source.documentation" in _bad(raw, lambda d: d["source"].__setitem__("documentation", []))
    assert "source.documentation[0].url" in _bad(
        raw, lambda d: d["source"]["documentation"][0].__setitem__("url", "ftp://x"))
    assert "source.accessed" in _bad(raw, lambda d: d["source"].__setitem__("accessed", "22 Nov 2026"))
    assert "source.checked" in _bad(raw, lambda d: d["source"].__setitem__("checked", "no"))
    assert "source.disclaimer" in _bad(raw, lambda d: d["source"].__setitem__("disclaimer", "x"))


def test_format_version_and_unknown_keys(raw):
    assert "format_version" in _bad(raw, lambda d: d.__setitem__("format_version", "2"))
    assert "extra" in _bad(raw, lambda d: d.__setitem__("extra", 1))


def test_load_from_another_path(tmp_path, raw):
    raw["source"]["checked"] = True
    p = tmp_path / "api.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    assert load_api_config(p).checked is True
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_api_config(p)
