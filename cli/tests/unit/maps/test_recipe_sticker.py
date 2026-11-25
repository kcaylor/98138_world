"""The optional recipe ``[sticker]`` table (feature 017, FR-004; contracts/recipe-sticker.md;
research R5; data-model.md StickerText).

The table adds sticker text only: a recipe without it parses exactly as before, and a recipe with
it differs from the same recipe without it only in ``sticker`` and its own SHA-256.
Not affiliated with or endorsed by The LEGO Group.
"""

import dataclasses
import hashlib

import pytest

from lego_image_processor.maps.recipe import (
    Recipe, RecipeError, StickerText, bundled_recipes, parse_recipe,
)
from tests.integration.stickers_guard import prefix_bytes

HEAD = 'format = "1"\nid = "sticker-demo"\ntitle = "Demo"\ndescription = "A demo map."\n'
LAND = '[land]\nrole = "background"\ncolors = ["lego_white"]\n'
OCEAN = '''[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_earth_blue", "lego_medium_azur", "lego_bright_bluish_green"]
[ocean.classification]
method = "bins"
bounds = [0, 200, 3000, 12000]
'''
OCEAN_NO_DATA = '[ocean.no_data]\ncolor = "lego_white"\nrule = "unobserved"\nmin_lat = 60\n'
BASE = HEAD + LAND + OCEAN
LINE = 'line = "Ocean depth on three tile colors."\n'
ALLOWED = "credit, line, no_data, title"
OLD_FIELDS = ["format", "id", "title", "land", "ocean", "sha256", "description", "seed", "path",
              "shadow", "arrangement",
              "template", "margin"]   # feature 016 (merged before 017's field, T053)


def _parse(text):
    return parse_recipe(text)


def _err(text):
    with pytest.raises(RecipeError) as e:
        parse_recipe(text)
    return e.value


class TestParse:
    def test_absent_table_is_none(self):
        assert _parse(BASE).sticker is None

    def test_line_only(self):
        s = _parse(BASE + "[sticker]\n" + LINE).sticker
        assert s == StickerText(line="Ocean depth on three tile colors.")
        assert s.title is None and s.credit is None and s.no_data == {}

    def test_every_key(self):
        text = (HEAD + LAND + OCEAN + OCEAN_NO_DATA + "[sticker]\n"
                'title = "Sea floor"\n' + LINE +
                'credit = "Depths from ETOPO 2022."\n'
                'no_data = { ocean = "sea ice" }\n')
        s = _parse(text).sticker
        assert s.title == "Sea floor"
        assert s.line == "Ocean depth on three tile colors."
        assert s.credit == "Depths from ETOPO 2022."
        assert s.no_data == {"ocean": "sea ice"}

    def test_no_data_for_both_layers(self):
        path = bundled_recipes()["living-planet"]
        text = prefix_bytes(path) + ('[sticker]\n' + LINE + 'no_data = { land = "ice", ocean = "sea ice" }\n'
                                     ).encode("utf-8")
        assert parse_recipe(text, path=path).sticker.no_data == {"land": "ice", "ocean": "sea ice"}

    def test_no_data_as_a_sub_table(self):
        text = BASE + OCEAN_NO_DATA + "[sticker]\n" + LINE + '[sticker.no_data]\nocean = "sea ice"\n'
        assert _parse(text).sticker.no_data == {"ocean": "sea ice"}

    @pytest.mark.parametrize("where", ["first table", "between layers", "end", "inline"])
    def test_table_may_appear_anywhere(self, where):
        table = '[sticker]\ntitle = "T"\n' + LINE
        if where == "first table":
            text = HEAD + table + LAND + OCEAN
        elif where == "between layers":
            text = HEAD + LAND + table + OCEAN
        elif where == "end":
            text = BASE + table
        else:
            text = HEAD + 'sticker = { title = "T", line = "Ocean depth on three tile colors." }\n' + LAND + OCEAN
        r = _parse(text)
        assert r.sticker == StickerText(title="T", line="Ocean depth on three tile colors.")
        assert r.ocean.classification.bounds == (0, 200, 3000, 12000)

    def test_text_outside_latin1_parses(self):
        # the PDF writer checks Latin-1, not the parser (research R5; contracts/cli.md)
        line = "Depth — 0 ≤ z ≤ 12,000 m ✓ 海"
        s = _parse(BASE + f'[sticker]\ntitle = "Tiefe – Meer"\nline = "{line}"\n').sticker
        assert s.line == line and s.title == "Tiefe – Meer"

    def test_sha256_changes_with_the_table_bytes(self):
        plain = BASE.encode("utf-8")
        one = plain + b"[sticker]\n" + LINE.encode("utf-8")
        two = plain + b'[sticker]\nline = "Another line."\n'
        shas = [_parse(t).sha256 for t in (plain, one, two)]
        assert shas == [hashlib.sha256(t).hexdigest() for t in (plain, one, two)]
        assert len(set(shas)) == 3

    def test_the_table_is_additive(self):
        plain = _parse(BASE)
        with_table = _parse(BASE + '[sticker]\ntitle = "T"\n' + LINE)
        assert with_table != plain
        assert dataclasses.replace(with_table, sticker=None, sha256=plain.sha256) == plain


def _single_line_error(path):
    return f"{path}: must be a non-empty single-line string"


class TestErrors:
    def test_unknown_key(self):
        e = _err(BASE + "[sticker]\n" + LINE + 'subtitle = "x"\n')
        assert e.path == "sticker.subtitle"
        assert str(e) == f"sticker.subtitle: unknown key (allowed: {ALLOWED})"

    def test_unknown_no_data_key(self):
        e = _err(BASE + OCEAN_NO_DATA + "[sticker]\n" + LINE + 'no_data = { ice = "x" }\n')
        assert e.path == "sticker.no_data.ice"
        assert str(e) == "sticker.no_data.ice: unknown key (allowed: land, ocean)"

    def test_line_missing(self):
        e = _err(BASE + '[sticker]\ntitle = "T"\n')
        assert e.path == "sticker.line" and str(e) == "sticker.line: is required"

    def test_empty_table_needs_a_line(self):
        assert str(_err(BASE + "[sticker]\n")) == "sticker.line: is required"

    @pytest.mark.parametrize("key", ["title", "line", "credit"])
    @pytest.mark.parametrize("value", ['""', '"   "', '"two\\nlines"', '"tab\\there"', '"return\\rhere"',
                                       '"ends with a newline\\n"', '"""\nmulti\nline"""', "5", "true",
                                       '["a"]'])
    def test_bad_string(self, key, value):
        lines = {"title": 'title = "T"\n', "line": LINE, "credit": ""}
        lines[key] = f"{key} = {value}\n"
        e = _err(BASE + "[sticker]\n" + "".join(lines.values()))
        assert e.path == f"sticker.{key}"
        assert str(e) == _single_line_error(f"sticker.{key}")

    @pytest.mark.parametrize("value", ['""', '"two\\nlines"', "3"])
    def test_bad_no_data_label(self, value):
        e = _err(BASE + OCEAN_NO_DATA + "[sticker]\n" + LINE + f"no_data = {{ ocean = {value} }}\n")
        assert e.path == "sticker.no_data.ocean"
        assert str(e) == _single_line_error("sticker.no_data.ocean")

    @pytest.mark.parametrize("layer", ["land", "ocean"])
    def test_no_data_for_a_layer_without_a_rule(self, layer):
        e = _err(BASE + "[sticker]\n" + LINE + f'no_data = {{ {layer} = "ice" }}\n')
        assert e.path == f"sticker.no_data.{layer}"
        assert str(e) == f"sticker.no_data.{layer}: the {layer} layer has no no_data rule"

    def test_not_a_table(self):
        e = _err(HEAD + 'sticker = "Ocean depth"\n' + LAND + OCEAN)
        assert e.path == "sticker" and str(e) == "sticker: must be a table"

    def test_no_data_not_a_table(self):
        e = _err(BASE + OCEAN_NO_DATA + "[sticker]\n" + LINE + 'no_data = "sea ice"\n')
        assert e.path == "sticker.no_data" and str(e) == "sticker.no_data: must be a table"


class TestBundled:
    def test_recipe_fields_are_the_old_ones_plus_sticker(self):
        fields = dataclasses.fields(Recipe)
        assert [f.name for f in fields] == OLD_FIELDS + ["sticker"]
        assert fields[-1].default is None

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_bundled_recipe_parses_as_before(self, recipe_id):
        path = bundled_recipes()[recipe_id]
        before = parse_recipe(prefix_bytes(path), path=path)  # the af3ce57 bytes (guard G1)
        assert before.sticker is None
        assert before.sha256 == hashlib.sha256(prefix_bytes(path)).hexdigest()
        now = parse_recipe(path.read_bytes(), path=path)
        # a bundled table (T043) adds sticker text and changes the recipe checksum, nothing else
        assert dataclasses.replace(now, sticker=None, sha256=before.sha256) == before


# The sticker texts the project owner approved on 2026-11-24 (tasks.md T042; run-state.md
# Decisions): the research R6 drafts, with "nine" dropped from the bathymetry line.
APPROVED = {
    "official-31203": {
        "title": "World Map, kit 31203 design",
        "line": "White land and the kit's ocean pattern in nine tile colors, cell for cell from its "
                "building instructions.",
        "credit": "Design grid from the LEGO 31203 building instructions, extracted by 98138.world.",
    },
    "official-31203-bathymetry": {
        "title": "Kit 31203 look, from bathymetry",
        "line": "Ocean depth (ETOPO 2022) ranked into the kit's tile colors in the kit design's "
                "proportions, on white land.",
    },
    "ocean-sst": {
        "line": "Annual mean sea surface temperature, 1991-2020, cold to warm on the kit's nine tile "
                "colors.",
    },
    "land-elevation": {
        "line": "Height of the land in metres, from lowland green through tan and brown to grey and "
                "ice-sheet white.",
    },
    "ocean-el-nino": {
        "line": "Sea surface temperature anomaly of a strong El Niño, in °C against the 1971-2000 "
                "average.",
    },
    "ocean-la-nina": {
        "line": "Sea surface temperature anomaly of a strong La Niña, in °C against the 1971-2000 "
                "average.",
    },
    "living-planet": {
        "line": "Plant productivity on land (2000-2015) and ocean chlorophyll at sea (2013-2024), "
                "with ice in white.",
        "no_data": {"land": "ice", "ocean": "sea ice"},
    },
    "rainfall": {
        "line": "Annual mean precipitation, 1991-2020, from desert tan to rainforest green on land "
                "and pale to deep blue at sea.",
    },
}
MARKER = "# Map stickers (feature 017):"


class TestBundledTables:
    """T042a: the approved ``[sticker]`` tables at the end of the eight bundled recipes (T043;
    contracts/recipe-sticker.md "Bundled recipes")."""

    def test_one_approved_table_per_bundled_recipe(self):
        assert sorted(APPROVED) == sorted(bundled_recipes())

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_table_after_one_comment_line_at_the_end(self, recipe_id):
        import tomllib

        path = bundled_recipes()[recipe_id]
        raw, prefix = path.read_bytes(), prefix_bytes(path)
        assert raw.startswith(prefix) and len(raw) > len(prefix), f"{path.name} has no sticker block"
        assert prefix.endswith(b"\n") and not prefix.endswith(b"\n\n")   # no blank line before
        tail = raw[len(prefix):].decode("utf-8")
        lines = tail.splitlines(keepends=True)
        assert lines[0].startswith(MARKER) and lines[0].endswith("\n")
        assert lines[1] == "[sticker]\n"
        assert tail.endswith("\n") and "\n\n" not in tail
        assert sum(ln.startswith("#") for ln in lines) == 1                # one comment line
        assert sum(ln.startswith("[") for ln in lines) == 1                # one table
        assert MARKER not in prefix.decode("utf-8")
        assert tomllib.loads(tail) == {"sticker": APPROVED[recipe_id]}

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_title_and_description_unchanged(self, recipe_id):
        path = bundled_recipes()[recipe_id]
        before = parse_recipe(prefix_bytes(path), path=path)      # the af3ce57 bytes (guard G1)
        now = parse_recipe(path.read_bytes(), path=path)
        assert (now.title, now.description) == (before.title, before.description)
        assert now.sticker is not None and before.sticker is None

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_texts_are_the_approved_ones(self, recipe_id):
        path = bundled_recipes()[recipe_id]
        r = parse_recipe(path.read_bytes(), path=path)
        t = APPROVED[recipe_id]
        assert r.sticker == StickerText(line=t["line"], title=t.get("title"),
                                        credit=t.get("credit"), no_data=t.get("no_data", {}))

    @pytest.mark.parametrize("recipe_id", sorted(bundled_recipes()))
    def test_text_rules(self, recipe_id):
        path = bundled_recipes()[recipe_id]
        r = parse_recipe(path.read_bytes(), path=path)
        s = r.sticker
        title = s.title or r.title
        assert "official" not in title.lower()                              # FR-004
        for text in (title, s.line, s.credit or "", *s.no_data.values()):
            text.encode("latin-1")                                          # research R6
        assert (s.credit is not None) == (recipe_id == "official-31203")   # research R9
        assert s.no_data == ({"land": "ice", "ocean": "sea ice"} if recipe_id == "living-planet"
                             else {})

    def test_bathymetry_line_without_nine(self):
        path = bundled_recipes()["official-31203-bathymetry"]
        line = parse_recipe(path.read_bytes(), path=path).sticker.line
        assert "nine" not in line and line.startswith("Ocean depth (ETOPO 2022) ranked into the kit's tile")
