"""Feature 017 guards (research R13 G1-G4; FR-017, SC-006): stickers change no other output.

- G1 ``test_recipe_prefix_is_af3ce57``: the bytes of each bundled recipe before its sticker block
  are exactly the af3ce57 file.
- G2 ``test_outputs_differ_only_in_recipe_checksum``: for each bundled recipe built in A, the kit
  outputs from the prefix bytes equal those from the full file once the recipe and layout
  checksums are replaced by placeholders. Since T043 the full files carry the approved sticker
  tables, so G2 shows FR-017 and SC-006 on them (T021 showed it on the research R6 drafts
  before the owner's approval; that test went with the drafts).
- G3 ``test_guard_golden``: digests of every kit output of the eight bundled recipes in A, B and C
  (built from the prefix bytes) equal ``tests/fixtures/golden/stickers_017_guard.json``, written
  once from code without any feature 017 change and never regenerated in this feature. With
  ``STICKERS_017_GUARD_WRITE=1`` (and only then) the test writes that file instead.
- G4 ``test_map_part_blocks_unchanged`` and ``test_cells_palette_lists_only_map_parts``: the
  6141 and 98138 blocks of the part data are unchanged, and the palette chooser lists only them.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import os

import pytest

from . import stickers_guard as guard

# af3ce57 SHA-256 of each bundled recipe file (research R13; byte-identical at 6038d9c)
AF3CE57_RECIPE_SHA256 = {
    "land-elevation": "659b67ad222c6fae15e514ba35d6e256297055b82588c4e3dabd3546bbf9c2e5",
    "living-planet": "cf7a805b65f751299545181a025cd3096a6a2466508e3e8cbe7575c8babf0dfc",
    "ocean-el-nino": "0095a9da442d29b04dde0b9df467efc812c9a6ea952e165c1b44d91c7d5f98cd",
    "ocean-la-nina": "973535a1c1487ed071c0b70a9a4bf1f55196bd50614ffed50bebeeb3ff3eeec8",
    "ocean-sst": "d7aaececf7f444b37f7cbca3a92ff8aedef735b770f58be2b87e3b1d9a0d6ddb",
    "official-31203-bathymetry": "f7412b1c05148e7ca253913fc940a18d835ddec1c1f7eeaaee664ee13fd9b97e",
    "official-31203": "e08f4d1747cab16a58d45c8dbb94dfe0725cf7f0ad558cb26e10f7f9aba764f7",
    "rainfall": "0fdc586705803f3ff6522d30e999a317dd7fb8cfa2d83b039c57d0921b7cfa5a",
}

# af3ce57 canonical-JSON digests of the map parts' blocks (guard.map_part_blocks; the data files
# are byte-identical at 6038d9c, and feature 016's kit golden records the same values)
AF3CE57_PART_BLOCKS = {
    "part_colors.json": {
        "parts.6141": "db08dcb335c54d37eb1924e5cb14be908ab992fc91357acd0afd07063fa5852a",
        "parts.98138": "0a3a69a71bb1b90072602f334bcd2385e43374f0b3478260b48f808c5554ca13",
        "citations": "0c7e0c01770d04a914e1c18a6cdb91689d3e02a8d9f88a68745f748a6b0a94b9",
        "excluded": "809ff9b8976bdf9e98de12f212c668c7e0aa7a652689999054fe68c2145353d0",
    },
    "part_numbers.json": {
        "parts.6141": "c4bf262b07b32e1f80e87ed0cb3f2edf8e4126e424e0f08869ba20d49e80e248",
        "parts.98138": "4c66971a358d9c22a5bcbb8f36971c58e9e494e5e38197a7047992b3bb89a020",
        "citations": "b5dbc046377c72bda2c736ca59fa260292564f04553992e3356e94c5ff9a4ef3",
    },
}

WRITE_VARIABLE = "STICKERS_017_GUARD_WRITE"
BUNDLED = sorted(AF3CE57_RECIPE_SHA256)


@pytest.fixture
def placed(fixture_registry):
    fixture_registry.place_all()
    return fixture_registry


# --- G1 ---------------------------------------------------------------------------------------

def test_bundled_recipes_are_the_eight_pinned():
    assert sorted(guard.bundled_recipe_paths()) == BUNDLED


@pytest.mark.parametrize("recipe_id", BUNDLED)
def test_recipe_prefix_is_af3ce57(recipe_id):
    path = guard.bundled_recipe_paths()[recipe_id]
    got = hashlib.sha256(guard.prefix_bytes(path)).hexdigest()
    assert got == AF3CE57_RECIPE_SHA256[recipe_id], (
        f"{path.name}: the bytes before the sticker block changed (SHA-256 {got}); feature 017 may "
        "only append a sticker table after a '# Map stickers (feature 017):' line")


def test_prefix_bytes_stops_at_the_sticker_marker(tmp_path):
    body = b'format = "1"\nid = "x"\n'
    p = tmp_path / "x.toml"
    p.write_bytes(body + b"# Map stickers (feature 017): draft\n[sticker]\nline = \"y\"\n")
    assert guard.prefix_bytes(p) == body
    p.write_bytes(body)
    assert guard.prefix_bytes(p) == body
    p.write_bytes(body + b"  # Map stickers (feature 017): not at the start of the line\n")
    assert guard.prefix_bytes(p) == p.read_bytes()


# --- G2 ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("recipe_id", BUNDLED)
def test_outputs_differ_only_in_recipe_checksum(placed, recipe_id):
    path = guard.bundled_recipe_paths()[recipe_id]
    # The full file carries the approved sticker table (T043), the prefix is the af3ce57 file: the
    # outputs differ only in the recipe checksum (FR-017, SC-006).
    before = guard.kit_outputs(guard.prefix_bytes(path), path, placed.cache_dir)
    after = guard.kit_outputs(path.read_bytes(), path, placed.cache_dir)
    _assert_only_the_checksum_differs(recipe_id, before, after, placed)


def _assert_only_the_checksum_differs(recipe_id, before, after, placed):
    assert sorted(before) == sorted(after)
    diffs = [f"{name}: {guard.first_difference(before[name], after[name])}"
             for name in sorted(before) if before[name] != after[name]]
    assert not diffs, f"{recipe_id}: outputs differ beyond the recipe checksum:\n" + "\n".join(diffs)
    assert guard.RECIPE_PLACEHOLDER.encode() in before["layout.json"]
    assert any(name.startswith("sheets-letter.svg/") for name in before)
    # no checkout or temporary path reaches an output (the guard golden is machine independent)
    roots = {str(p).encode() for r in (guard.CLI_DIR, placed.root) for p in (r, r.resolve())}
    leaks = [name for name, data in before.items() if data and any(r in data for r in roots)]
    assert not leaks, f"{recipe_id}: a local path reaches {leaks}"


# --- G3 ---------------------------------------------------------------------------------------

def test_guard_golden(placed):
    actual = guard.guard_digests(placed.cache_dir)
    assert actual["inputs"]["recipes"] == AF3CE57_RECIPE_SHA256
    if os.environ.get(WRITE_VARIABLE) == "1":
        guard.GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        guard.GOLDEN_PATH.write_text(guard.to_text(actual), encoding="utf-8")
        return
    assert guard.GOLDEN_PATH.is_file(), (
        f"{guard.GOLDEN_PATH} is missing; it is written once, from code without any feature 017 "
        f"change, with {WRITE_VARIABLE}=1")
    raw = guard.GOLDEN_PATH.read_bytes()
    source = json.loads(guard.GOLDEN_PATH.with_name("stickers_017_guard.source.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw).hexdigest() == source["sha256"], (
        "the guard golden is not the file written before any feature 017 change (its SHA-256 "
        "differs from stickers_017_guard.source.json); restore it instead of regenerating it")
    expected = json.loads(raw.decode("utf-8"))
    diffs = guard.compare(expected, actual)
    assert not diffs, ("kit outputs changed (FR-017, SC-006); a changed guard digest is a bug in "
                       "the new code, never a reason to rewrite the golden:\n" + "\n".join(diffs))


def test_compare_names_the_recipe_combination_and_output():
    def doc(sha):
        return {"format_version": "1", "inputs": {}, "datasets": [],
                "variants": [{"recipe": "ocean-sst", "combination": "B",
                              "outputs": {"layout.json": {"bytes": 1, "sha256": sha}}}]}

    assert guard.compare(doc("a"), doc("a")) == []
    assert guard.compare(doc("a"), doc("b")) == [
        "ocean-sst B: layout.json differs (expected {'bytes': 1, 'sha256': 'a'}, "
        "got {'bytes': 1, 'sha256': 'b'})"]
    missing = doc("a")
    missing["variants"][0]["outputs"] = {}
    assert guard.compare(doc("a"), missing) == ["ocean-sst B: layout.json missing"]


# --- G4 ---------------------------------------------------------------------------------------

def test_map_part_blocks_unchanged():
    assert guard.map_part_blocks() == AF3CE57_PART_BLOCKS


def test_cells_palette_lists_only_map_parts(placed):
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.cells import map_cells, part_palette
    from lego_image_processor.maps.recipe import load_recipe

    assert sorted(part_palette()) == sorted(guard.KIT_PARTS)
    for recipe_id in BUNDLED:
        for c in guard.COMBINATIONS:
            result = build_map(load_recipe(recipe_id), cache_dir=placed.cache_dir,
                               arrangement=parse_arrangement(c))
            assert sorted(map_cells(result)["palette"]) == sorted(guard.KIT_PARTS), (recipe_id, c)
