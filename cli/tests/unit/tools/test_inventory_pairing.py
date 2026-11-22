"""Pairing of page-159 count tokens with element IDs (pure; factual word-list fixture)."""

import json
from pathlib import Path

import pytest

from kit31203 import inventory

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "kit31203"


def _words():
    data = json.loads((FIXTURES / "page159_words.json").read_text())
    return [(w["x"], w["y"], w["text"]) for w in data["words"]]


def _expected():
    data = json.loads((FIXTURES / "inventory_expected.json").read_text())
    return {e["element_id"]: e["quantity"] for e in data["elements"]}


class TestPairWords:
    def test_fixture_yields_expected_pairs(self):
        pairs = inventory.pair_words(_words())
        assert len(pairs) == 32
        assert dict(pairs) == _expected()
        assert sum(q for _, q in pairs) == 11694

    def test_order_column_by_column_top_to_bottom(self):
        pairs = inventory.pair_words(_words())
        assert pairs[0] == ("4518400", 40)
        assert pairs[1] == ("614101", 3064)
        assert pairs[-1] == ("6302092", 40)

    def test_ignores_other_text(self):
        words = _words() + [(679.0, 96.0, "Customer Service"), (687.0, 25.0, "00800 5346 5555")]
        assert len(inventory.pair_words(words)) == 32

    def test_count_without_id(self):
        words = [(10.0, 100.0, "5x")]
        with pytest.raises(inventory.PairingError, match="5x") as info:
            inventory.pair_words(words)
        assert info.value.exit_code == 9

    def test_id_used_twice(self):
        words = [(10.0, 100.0, "5x"), (10.5, 98.0, "7x"), (10.0, 92.8, "614101")]
        with pytest.raises(inventory.PairingError, match="614101"):
            inventory.pair_words(words)

    def test_unpaired_id(self):
        words = [(10.0, 100.0, "5x"), (10.0, 92.8, "614101"), (200.0, 50.0, "6302092")]
        with pytest.raises(inventory.PairingError, match="6302092"):
            inventory.pair_words(words)

    def test_dx_too_large(self):
        with pytest.raises(inventory.PairingError):
            inventory.pair_words([(10.0, 100.0, "5x"), (13.0, 92.8, "614101")])

    def test_dy_too_large(self):
        with pytest.raises(inventory.PairingError):
            inventory.pair_words([(10.0, 100.0, "5x"), (10.0, 80.0, "614101")])

    def test_id_above_count_not_paired(self):
        with pytest.raises(inventory.PairingError):
            inventory.pair_words([(10.0, 100.0, "5x"), (10.0, 105.0, "614101")])

    def test_close_pair_ok(self):
        assert inventory.pair_words([(10.0, 100.0, "5x"), (12.9, 80.1, "614101")]) == [("614101", 5)]


class TestJoinCatalog:
    def test_catalog_covers_fixture(self):
        catalog = inventory.load_part_catalog()
        pairs = inventory.pair_words(_words())
        elements = inventory.join_catalog(pairs, catalog)
        assert [e["element_id"] for e in elements] == [p[0] for p in pairs]
        land = [e for e in elements if e["role"] == "land"]
        assert len(land) == 1 and land[0]["element_id"] == "614101"
        assert land[0]["part_ids"] == ["6141", "4073"]
        assert all(e["source_page"] == 159 for e in elements)

    def test_missing_catalog_element(self):
        catalog = inventory.load_part_catalog()
        with pytest.raises(inventory.PairingError, match="9999999"):
            inventory.join_catalog([("9999999", 1)], catalog)

    def test_unverified_frame_elements(self):
        catalog = inventory.load_part_catalog()
        by_id = {p["element_id"]: p for p in catalog["parts"]}
        for eid in ("4121715", "4160228"):
            assert by_id[eid]["verified"] is False
            assert by_id[eid]["role"] == "frame_other"
            assert by_id[eid]["note"]
