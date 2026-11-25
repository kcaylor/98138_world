"""The two stickers as page models (feature 017, T030; FR-002, FR-003, FR-008, FR-012, FR-013;
research R3, R4; data-model.md Sticker, StickerSet; contracts/sticker-files.md "Sticker
content").

Maps are built from the dataset fixtures (``fixture_registry``); final texts come from the
bundled recipes' approved sticker tables (T043; ``tests.stickers_support.sticker_recipe``).
Not affiliated with or endorsed by The LEGO Group.
"""

import json

import pytest

from lego_image_processor import __version__
from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.kit.plaque_parts import load_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import parse_recipe
from lego_image_processor.sheets.compose import text_width
from lego_image_processor.sheets.model import PT_MM, WHITE, Circle, Line, Rect, Text
from lego_image_processor.stickers import compose
from lego_image_processor.stickers import (KIT_TEMPLATE_ID, Sticker, StickerError, StickerSet,
                                           sticker_set)
from lego_image_processor.stickers.credits import credits_for
from lego_image_processor.stickers.geometry import sticker_geometry
from lego_image_processor.stickers.legend import map_legend
from lego_image_processor.stickers.text import resolve_text
from tests.stickers_support import fallback_recipe, sticker_recipe

EPS = 1e-6
CAP = 0.718      # Helvetica cap height (em)
DESCENT = 0.21   # Helvetica descender (em)
OUTLINE = (210, 210, 210)
CONTENT_TAGS = {"sticker-bg", "bleed", "title", "line", "site", "legend-heading", "swatch",
                "swatch-ring", "legend-label", "credit", "disclaimer"}

# A custom map: depth bins on the ocean and three same-colored region overrides whose long names
# merge on one swatch, so its label is wider than the large sticker at 5 pt.
LONG_OVERRIDES = '''format = "1"
id = "long-overrides"
title = "Long overrides"
description = "Depth classes and three long override names."
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_medium_azur", "lego_bright_bluish_green", "lego_earth_blue"]
[ocean.classification]
method = "bins"
bounds = [-9000, 200, 4000, 12000]
[[ocean.override]]
name = "The southern band of the ocean between sixty and thirty degrees south"
color = "lego_white"
lat_min = -60
lat_max = -30
[[ocean.override]]
name = "The tropical band of the ocean between thirty south and the equator"
color = "lego_white"
lat_min = -30
lat_max = 0
[[ocean.override]]
name = "The northern band of the ocean from the equator to thirty degrees north"
color = "lego_white"
lat_min = 0
lat_max = 30
[shadow]
enabled = false
'''

PLAIN = '''format = "1"
id = "plain-map"
title = "Plain map"
description = "White land on depth classes."
[land]
role = "background"
colors = ["lego_white"]
[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_medium_azur", "lego_bright_bluish_green", "lego_earth_blue"]
[ocean.classification]
method = "bins"
bounds = [-9000, 200, 4000, 12000]
'''


@pytest.fixture
def build(fixture_registry):
    fixture_registry.place_all()

    def _build(recipe, arrangement=None):
        if isinstance(recipe, str):
            recipe = sticker_recipe(recipe)
        return build_map(recipe, cache_dir=fixture_registry.cache_dir, compare_official=False,
                         arrangement=parse_arrangement(arrangement) if arrangement else None)
    return _build


def tagged(items, tag, kind=None):
    return [i for i in items if i.tag == tag and (kind is None or isinstance(i, kind))]


def joined(block):
    return " ".join(block.lines)


def text_extent(t: Text):
    """(left, top, right, bottom) of a text item from Helvetica's metrics."""
    w = text_width(t.text, t.size_pt, t.bold)
    left = {"left": t.x, "center": t.x - w / 2, "right": t.x - w}[t.align]
    em = t.size_pt * PT_MM
    return left, t.y - CAP * em, left + w, t.y + DESCENT * em


def inside(box, area, eps=EPS):
    l, t, r, b = box
    x, y, w, h = area
    return l >= x - eps and t >= y - eps and r <= x + w + eps and b <= y + h + eps


def black_rgb():
    return load_plaque_parts().plaques["large"].tile.color.rgb


# --- the small sticker (FR-003) --------------------------------------------------------------

class TestSmall:
    def test_title_line_and_disclaimer_only(self, build):
        s = sticker_set(build("ocean-sst"))
        small = s.small
        assert isinstance(small, Sticker) and small.size == "small"
        assert [b.field for b in small.blocks] == ["title", "line", "disclaimer"]
        assert joined(small.block("title")) == "Ocean temperature"
        assert joined(small.block("line")) == s.text.line
        assert joined(small.block("disclaimer")) == DISCLAIMER
        assert small.legend == ()
        text_tags = {i.tag for i in small.items if isinstance(i, Text)}
        assert text_tags == {"title", "line", "disclaimer"}
        assert not tagged(small.items, "swatch") and not tagged(small.items, "site")
        assert not any("98138.world" in i.text for i in small.items if isinstance(i, Text))

    def test_centred_and_disclaimer_at_the_bottom(self, build):
        small = sticker_set(build("ocean-sst")).small
        g = small.geometry
        sx, sy, sw, sh = g.safe_box
        for b in small.blocks:
            assert b.align == "center"
        for t in small.items:
            if isinstance(t, Text):
                assert abs(t.x - (sx + sw / 2)) <= EPS
        disc = small.block("disclaimer")
        assert abs(disc.box[1] + disc.box[3] - (sy + sh)) <= EPS     # on the safe area's bottom
        title, line = small.block("title"), small.block("line")
        assert title.box[1] + title.box[3] <= line.box[1] + EPS        # title above the line
        assert line.box[1] + line.box[3] < disc.box[1]                 # line above the disclaimer
        # the title and line pair is centred vertically above the disclaimer
        top_gap = title.box[1] - sy
        bottom_gap = disc.box[1] - (line.box[1] + line.box[3])
        assert top_gap > 0 and bottom_gap > 0
        assert abs(top_gap - (bottom_gap - compose.SMALL_DISCLAIMER_GAP_MM)) <= 0.01


# --- the large sticker (FR-002) --------------------------------------------------------------

class TestLarge:
    def test_blocks_in_reading_order(self, build):
        s = sticker_set(build("ocean-sst"))
        large = s.large
        assert large.size == "large"
        assert [b.field for b in large.blocks] == ["title", "site", "line", "legend", "credit",
                                                   "disclaimer"]
        assert joined(large.block("title")) == "Ocean temperature"
        assert large.block("site").lines == ("98138.world",)
        assert joined(large.block("line")) == s.text.line
        assert joined(large.block("disclaimer")) == DISCLAIMER

    def test_site_right_aligned_on_the_first_title_baseline(self, build):
        large = sticker_set(build("ocean-sst")).large
        sx, sy, sw, sh = large.geometry.safe_box
        site = tagged(large.items, "site", Text)
        title = tagged(large.items, "title", Text)
        assert len(site) == 1 and site[0].align == "right" and site[0].bold
        assert abs(site[0].x - (sx + sw)) <= EPS
        assert abs(site[0].y - title[0].y) <= EPS
        assert title[0].align == "left" and title[0].bold and abs(title[0].x - sx) <= EPS
        # the title never runs into the site name
        for t in title:
            assert text_extent(t)[2] < text_extent(site[0])[0]

    def test_data_credit(self, build):
        s = sticker_set(build("rainfall"))
        credit = s.large.block("credit")
        assert credit.lines[0].startswith("Data: ")
        text = joined(credit)
        for c in credits_for(s_recipe("rainfall")):
            assert c.text in text
        assert [c.dataset for c in s.credits] == [c.dataset for c in credits_for(s_recipe("rainfall"))]

    def test_sticker_credit_replaces_the_data_lines(self, build):
        s = sticker_set(build("official-31203"))
        assert joined(s.large.block("credit")) == (
            "Data: Design grid from the LEGO 31203 building instructions, extracted by 98138.world.")
        assert "Official" not in joined(s.large.block("title"))
        # the print sheet keeps every registry credit
        assert [c.dataset for c in s.credits] == ["kit31203-design"]

    def test_legend_labels_and_headings(self, build):
        result = build("ocean-sst")
        s = sticker_set(result)
        legend = map_legend(result)
        assert s.legend == legend
        labels = tagged(s.large.items, "legend-label", Text)
        assert [t.text for t in labels] == [sw.label for sw in legend]
        heads = tagged(s.large.items, "legend-heading", Text)
        assert [t.text for t in heads] == ["Land", "Ocean"] and all(t.bold for t in heads)
        assert [p.swatch for p in s.large.legend] == list(legend)
        block = s.large.block("legend")
        assert block.lines == ("Land", legend.swatches[0].label, "Ocean",
                               *[sw.label for sw in legend.group("ocean").swatches])

    def test_kit_design_heading(self, build):
        s = sticker_set(build("official-31203"))
        heads = [t.text for t in tagged(s.large.items, "legend-heading", Text)]
        assert heads == ["Land", "Ocean: the kit design's colors"]


def s_recipe(recipe_id):
    return sticker_recipe(recipe_id)


# --- colors and swatches (FR-008) -------------------------------------------------------------

class TestColors:
    @pytest.mark.parametrize("size", ["small", "large"])
    def test_black_background_and_bleed_white_text(self, build, size):
        st = getattr(sticker_set(build("ocean-sst")), size)
        black = black_rgb()
        assert black == (5, 19, 29)
        bleed = tagged(st.items, "bleed", Rect)
        bg = tagged(st.items, "sticker-bg", Rect)
        assert len(bleed) == 1 and len(bg) == 1
        w, h = st.geometry.cut_mm
        b = bleed[0]
        assert (b.x, b.y) == (-2.0, -2.0) and abs(b.w - (w + 4)) <= EPS and abs(b.h - (h + 4)) <= EPS
        assert (bg[0].x, bg[0].y, bg[0].w, bg[0].h) == (0.0, 0.0, w, h)
        assert b.fill == bg[0].fill == black and b.stroke is None and bg[0].stroke is None
        assert st.items[0] is b and st.items[1] is bg[0]       # drawn first, under the content
        texts = [i for i in st.items if isinstance(i, Text)]
        assert texts and all(t.color == WHITE for t in texts)

    def test_swatches_cited_srgb_with_outline_and_rings(self, build):
        s = sticker_set(build("rainfall"))
        table = load_part_colors()
        swatches = tagged(s.large.items, "swatch", Circle)
        assert len(swatches) == len(s.legend)
        for c, sw in zip(swatches, s.legend):
            assert abs(c.r * 2 - 2.8) <= EPS
            assert c.fill == tuple(table.get(sw.part_id, sw.color).rgb) == sw.rgb
            assert c.stroke == OUTLINE and c.stroke_w == 0.15
            assert dict(c.data) == {"layer": sw.layer, "color": sw.color, "part": sw.part_id}
        rings = tagged(s.large.items, "swatch-ring", Circle)
        plates = [c for c in swatches if dict(c.data)["part"] == "6141"]
        assert len(rings) == len(plates) > 0
        for ring, plate in zip(rings, plates):
            assert (ring.cx, ring.cy) == (plate.cx, plate.cy) and ring.r < plate.r
            assert ring.fill is None
        # the Black shadow swatch shows on the Black sticker through its light outline
        shadow = [c for c in swatches if dict(c.data)["color"] == "lego_black"]
        assert shadow and shadow[0].stroke == OUTLINE

    def test_no_image_or_logo_items(self, build):
        s = sticker_set(build("ocean-sst"))
        for st in (s.small, s.large):
            assert all(isinstance(i, (Rect, Circle, Line, Text)) for i in st.items)
            assert not tagged(st.items, "cut-mark") and not tagged(st.items, "cut-line")


# --- fitting (FR-013, SC-001) -----------------------------------------------------------------

class TestFit:
    @pytest.mark.parametrize("recipe_id", ["ocean-sst", "land-elevation", "rainfall",
                                           "living-planet", "official-31203"])
    def test_every_text_inside_the_safe_area(self, build, recipe_id):
        s = sticker_set(build(recipe_id))
        for st in (s.small, s.large):
            area = st.geometry.safe_box
            for t in st.items:
                if isinstance(t, Text):
                    assert inside(text_extent(t), area), (st.size, t.tag, t.text)
            for b in st.blocks:
                x, y, w, h = b.box
                assert inside((x, y, x + w, y + h), area), (st.size, b.field)
                assert b.size_pt >= 5.0
            for c in tagged(st.items, "swatch", Circle):
                assert inside((c.cx - c.r, c.cy - c.r, c.cx + c.r, c.cy + c.r), area)

    @pytest.mark.parametrize("recipe_id", ["ocean-sst", "land-elevation", "rainfall"])
    def test_legend_entries_do_not_overlap(self, build, recipe_id):
        large = sticker_set(build(recipe_id)).large
        placed = large.legend
        for p in placed:
            l, _, r, _ = text_extent(p.label)
            assert l >= p.cx + p.r                                   # the label right of its swatch
            assert abs(p.label.y - p.cy) <= p.r                      # on the swatch's row
            for q in placed:
                if q is p or abs(q.cy - p.cy) > 1.0:
                    continue
                assert q.cx + q.r <= l - EPS or q.cx - q.r >= r + EPS, (p.label.text, q.label.text)
        heads = tagged(large.items, "legend-heading", Text)
        swatch_tops = min(p.cy - p.r for p in placed)
        assert all(h.y <= swatch_tops for h in heads)

    def test_cut_sizes(self, build):
        s = sticker_set(build("ocean-sst"))
        assert abs(s.small.geometry.cut_mm[0] - 45.8) <= 0.1
        assert abs(s.large.geometry.cut_mm[0] - 125.8) <= 0.1
        assert abs(s.large.geometry.cut_mm[1] - 61.8) <= 0.1
        assert s.small.geometry == sticker_geometry("small")
        assert s.large.geometry == sticker_geometry("large")
        assert s.small.plaque == load_plaque_parts().plaques["small"]
        assert s.large.plaque == load_plaque_parts().plaques["large"]
        assert s.plaques == (s.small.plaque, s.large.plaque)

    def test_preferred_sizes(self, build):
        s = sticker_set(build("ocean-sst"))
        small = {b.field: b.preferred_pt for b in s.small.blocks}
        large = {b.field: b.preferred_pt for b in s.large.blocks}
        assert small == {"title": 11.0, "line": 7.0, "disclaimer": 5.0}
        assert large == {"title": 14.0, "site": 7.0, "line": 7.0, "legend": 6.0, "credit": 5.5,
                         "disclaimer": 5.5}
        assert all(b.min_pt == 5.0 for b in s.small.blocks + s.large.blocks)
        bold = {b.field for b in s.small.blocks + s.large.blocks if b.bold}
        assert bold == {"title", "site"}
        # ocean-sst fits at the preferred sizes (research R3)
        assert all(b.size_pt == b.preferred_pt for b in s.small.blocks + s.large.blocks)
        assert s.large.text_sizes == (5.5, 14.0) and s.small.text_sizes == (5.0, 11.0)

    def test_legend_that_does_not_fit(self, build):
        result = build(parse_recipe(LONG_OVERRIDES))
        with pytest.raises(StickerError) as exc:
            sticker_set(result)
        e = exc.value
        assert e.sticker == "large" and e.field == "legend: ocean"
        assert e.needed_mm > e.available_mm
        assert "legend: ocean" in str(e) and "mm available" in str(e)

    def test_title_too_long(self, build):
        title = " ".join(["Extraordinarily"] * 40)
        recipe = parse_recipe(PLAIN + f'[sticker]\ntitle = "{title}"\nline = "A short line."\n')
        with pytest.raises(StickerError) as exc:
            sticker_set(build(recipe))
        assert exc.value.field == "title" and exc.value.sticker in ("small", "large")
        assert exc.value.needed_mm > exc.value.available_mm

    def test_line_too_long(self, build):
        line = " ".join(["temperature"] * 120)
        recipe = parse_recipe(PLAIN + f'[sticker]\nline = "{line}"\n')
        with pytest.raises(StickerError) as exc:
            sticker_set(build(recipe))
        assert exc.value.field == "line"
        assert exc.value.needed_mm > exc.value.available_mm
        assert "does not fit at 5 pt" in str(exc.value)

    def test_a_long_line_shrinks_before_it_fails(self, build):
        line = " ".join(["temperature"] * 19)      # 2 lines of 120.8 mm only below 7 pt
        recipe = parse_recipe(PLAIN + f'[sticker]\nline = "{line}"\n')
        s = sticker_set(build(recipe))
        b = s.large.block("line")
        assert 5.0 <= b.size_pt < 7.0 and len(b.lines) <= 2
        assert joined(b) == line                                   # never truncated
        assert not any("..." in ln for ln in b.lines)


# --- the set (data-model.md StickerSet) -------------------------------------------------------

class TestSet:
    def test_fields(self, build):
        result = build("ocean-sst")
        s = sticker_set(result)
        assert isinstance(s, StickerSet)
        r = s_recipe("ocean-sst")
        assert (s.recipe.id, s.recipe.title, s.recipe.sha256) == (r.id, r.title, r.sha256)
        assert s.template.to_dict() == {"id": KIT_TEMPLATE_ID} == {"id": "kit-31203"}
        assert s.arrangement == "A"
        assert s.text == resolve_text(r)
        assert s.credits == credits_for(r)
        assert s.notes.printed == "The sticker is printed, not a LEGO part."
        assert s.notes.colors == "Printed colors only approximate the LEGO colors."
        assert s.tool_version == __version__ and s.disclaimer == DISCLAIMER

    def test_fallback_texts(self, build):
        r = fallback_recipe("ocean-sst")                         # the recipe without its table
        s = sticker_set(build(r))
        assert (s.text.title, s.text.title_source) == (r.title, "recipe title")
        assert (s.text.line, s.text.line_source) == (r.description, "recipe description")
        assert joined(s.small.block("line")) == r.description

    def test_arrangement_of_the_build(self, build):
        assert sticker_set(build("ocean-el-nino")).arrangement == "D"     # the recipe's own (010)
        assert sticker_set(build("ocean-sst", "C")).arrangement == "C"

    def test_same_result_twice_gives_equal_sets(self, build):
        result = build("rainfall")
        a, b = sticker_set(result), sticker_set(result)
        assert a == b
        assert a.to_dict() == b.to_dict()
        assert json.dumps(a.to_dict(), ensure_ascii=False) == json.dumps(b.to_dict(), ensure_ascii=False)

    def test_two_builds_give_equal_sets(self, build):
        assert sticker_set(build("ocean-sst")) == sticker_set(build("ocean-sst"))

    def test_no_timestamps(self, build):
        text = json.dumps(sticker_set(build("ocean-sst")).to_dict())
        for word in ("generated", "timestamp", "created", "date", "time"):
            assert word not in text.lower()

    def test_every_combination_identical_but_for_arrangement(self, build):
        sets = {c: sticker_set(build("ocean-sst", c)) for c in "ABCDE"}   # D, E: feature 010
        dicts = {c: s.to_dict() for c, s in sets.items()}
        assert [d.pop("arrangement") for d in dicts.values()] == ["A", "B", "C", "D", "E"]
        assert all(dicts[c] == dicts["A"] for c in "BCDE")
        assert all(sets[c].small == sets["A"].small and sets[c].large == sets["A"].large for c in "BCDE")

    def test_to_dict_layout(self, build):
        d = sticker_set(build("living-planet")).to_dict()
        assert list(d) == ["format_version", "recipe", "template", "arrangement", "text",
                           "stickers", "legend", "credits", "plaques", "notes", "tool_version",
                           "disclaimer"]
        assert d["format_version"] == "1"
        assert list(d["recipe"]) == ["id", "title", "sha256"]
        assert d["template"] == {"id": "kit-31203"}
        assert list(d["text"]) == ["title", "title_source", "line", "line_source"]
        assert list(d["stickers"]) == ["small", "large"]
        small, large = d["stickers"]["small"], d["stickers"]["large"]
        assert list(small) == ["plaque", "tile_mm", "cut_mm", "bleed_mm", "safe_mm", "blocks"]
        assert small["plaque"] == "small" and large["plaque"] == "large"
        assert small["tile_mm"] == [47.8, 47.8] and small["cut_mm"] == [45.8, 45.8]
        assert large["tile_mm"] == [127.8, 63.8] and large["cut_mm"] == [125.8, 61.8]
        assert small["bleed_mm"] == 2.0 and small["safe_mm"] == 2.5
        assert [b["field"] for b in large["blocks"]] == ["title", "site", "line", "legend",
                                                        "credit", "disclaimer"]
        assert all(list(b) == ["field", "lines", "size_pt"] for b in large["blocks"])
        assert d["notes"] == {"printed": "The sticker is printed, not a LEGO part.",
                              "colors": "Printed colors only approximate the LEGO colors."}
        assert d["disclaimer"] == DISCLAIMER and d["tool_version"] == __version__
        json.dumps(d, ensure_ascii=False)        # JSON-ready

    def test_plaques_in_the_summary(self, build):
        d = sticker_set(build("ocean-sst")).to_dict()
        table = load_plaque_parts()
        assert [p["size"] for p in d["plaques"]] == ["small", "large"]
        for p in d["plaques"]:
            plaque = table.plaques[p["size"]]
            assert p["studs"] == list(plaque.studs)
            assert p["sticker_mm"] == list(sticker_geometry(p["size"]).cut_mm)
            assert [x["role"] for x in p["parts"]] == ["tile", "plate"]
            for row, part in zip(p["parts"], plaque.parts):
                assert list(row) == ["role", "quantity", "part_id", "name", "color", "element_id",
                                     "lego_design_ids", "bricklink_item", "rebrickable_part",
                                     "citations"]
                assert row["quantity"] == 1 and row["part_id"] == part.part_id
                assert row["name"] == part.name
                c = part.color
                assert row["color"] == {
                    "key": "lego_black",
                    "lego": {"name": c.lego.name, "id": c.lego.id},
                    "bricklink": {"name": c.bricklink.name, "id": c.bricklink.id},
                    "rebrickable": {"name": c.rebrickable.name, "id": c.rebrickable.id}}
                assert row["element_id"] == c.element_id
                assert row["lego_design_ids"] == list(part.numbers.lego_design_ids)
                # the BrickLink item number is read from the file, never assumed to be the part ID
                assert row["bricklink_item"] == part.numbers.bricklink_item_no
                assert row["rebrickable_part"] == part.numbers.rebrickable_part_num
                ids = ({x.id for x in c.citations.values()}
                       | {x.id for x in part.numbers.citations.values()})
                assert set(row["citations"]) == ids and len(row["citations"]) == len(ids)


# --- the kit template (016); sets on other templates: test_template_stickers.py (T055) --------

class TestKitTemplate:
    def test_kit_build_has_the_kit_template(self, build):
        result = build("ocean-sst")
        assert result.template.id == KIT_TEMPLATE_ID and result.template.is_kit
        assert sticker_set(result).template.to_dict() == {"id": KIT_TEMPLATE_ID}
