"""Sticker text (feature 017, T022): the resolved title and line with their sources (FR-004;
data-model.md StickerText), legend numbers and the display step (research R7, R8), and the
wrap-then-shrink fit of a text block (research R3, FR-013).

Not affiliated with or endorsed by The LEGO Group.
"""

import dataclasses
from decimal import Decimal

import pytest

from lego_image_processor.sheets.compose import text_width
from lego_image_processor.stickers import StickerError
from lego_image_processor.stickers.text import (
    MIN_PT, SOURCE_DESCRIPTION, SOURCE_TABLE, SOURCE_TITLE, STEP_PT, TextBlock, TextSpec,
    block_height, display_step, fit_block, fit_stack, format_number, format_quantity,
    line_pitch, number_value, resolve_text, round_to_step, wrap_words,
)
from tests.stickers_support import fallback_recipe, sticker_recipe

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
LONG = ("Annual mean precipitation, 1991-2020, from desert tan to rainforest green on land and "
        "pale to deep blue at sea.")


# --- resolution (FR-004) -----------------------------------------------------------------------

class TestResolveText:
    def test_table_title_and_line(self):
        t = resolve_text(sticker_recipe("official-31203"))
        assert t.title == "World Map, kit 31203 design" and t.title_source == SOURCE_TABLE
        assert t.line.startswith("White land and the kit's ocean pattern")
        assert t.line_source == SOURCE_TABLE == "sticker table"

    def test_table_line_with_the_recipe_title(self):
        r = sticker_recipe("ocean-sst")
        assert r.sticker is not None and r.sticker.title is None
        t = resolve_text(r)
        assert t.title == "Ocean temperature" and t.title_source == SOURCE_TITLE == "recipe title"
        assert t.line == r.sticker.line and t.line_source == SOURCE_TABLE

    def test_fallback_to_title_and_description(self):
        r = fallback_recipe("ocean-sst")                         # the recipe without its table
        assert r.sticker is None
        t = resolve_text(r)
        assert (t.title, t.title_source) == (r.title, "recipe title")
        assert (t.line, t.line_source) == (r.description, "recipe description")
        assert SOURCE_DESCRIPTION == "recipe description"

    def test_no_line_and_no_description(self):
        r = dataclasses.replace(fallback_recipe("ocean-sst"), description="")
        with pytest.raises(StickerError, match=r"add a \[sticker\] line"):
            resolve_text(r)

    def test_blank_description_is_no_line(self):
        r = dataclasses.replace(fallback_recipe("ocean-sst"), description="   ")
        with pytest.raises(StickerError, match=r"add a \[sticker\] line"):
            resolve_text(r)

    def test_to_dict(self):
        t = resolve_text(sticker_recipe("ocean-sst"))
        assert list(t.to_dict()) == ["title", "title_source", "line", "line_source"]

    def test_sticker_error_is_a_value_error(self):
        assert issubclass(StickerError, ValueError)


# --- numbers (research R7, R8) -----------------------------------------------------------------

class TestNumbers:
    @pytest.mark.parametrize("value, text", [
        (3000, "3,000"), (1460.0, "1,460"), (150, "150"), (0, "0"), (-0.0, "0"),
        (-1.5, "-1.5"), (-0.25, "-0.25"), (1.0, "1"), (182.5, "182.5"), (273.75, "273.75"),
        (0.08000000000000002, "0.08"), (0.15000000000000002, "0.15"), (12345.5, "12,345.5"),
        (Decimal("8E+2"), "800"), (Decimal("-2"), "-2"),
    ])
    def test_format_number(self, value, text):
        assert format_number(value) == text

    def test_hyphen_minus(self):
        assert format_number(-2) == "-2" and "−" not in format_number(-2)
        assert format_number(-2)[0] == "-"

    def test_no_trailing_zeros(self):
        assert format_number(2.50) == "2.5" and format_number(100.0) == "100"

    def test_six_significant_digits_without_a_step(self):
        assert format_number(0.1 + 0.2) == "0.3"
        assert format_number(1 / 3) == "0.333333"

    @pytest.mark.parametrize("value, units, text", [
        (3000, "m", "3,000 m"), (1, "degC", "1 °C"), (-2, "°C", "-2 °C"),
        (182.5, "mm/yr", "182.5 mm/yr"), (850, "g C m-2 yr-1", "850 g C m-2 yr-1"), (5, "", "5"),
    ])
    def test_format_quantity(self, value, units, text):
        assert format_quantity(value, units) == text

    @pytest.mark.parametrize("lo, hi, step", [
        (-1.799999475479126, 29.7585391998291, 1),       # ocean-sst (fixtures, A): 1 °C
        (0.0, 6169.666666666667, 100),                   # bathymetry (fixtures, A): 100 m
        (1.0, 6169.0, 100),                              # bathymetry (real data, A)
        (0.0, 0.5, Decimal("0.01")),
        (0.0, 10.0, 1), (0.0, 99.9, 1), (0.0, 100.0, 10),
    ])
    def test_display_step(self, lo, hi, step):
        assert display_step(lo, hi) == step

    def test_display_step_of_one_value(self):
        assert display_step(29.76, 29.76) == 1
        assert display_step(0.0, 0.0) == 1

    @pytest.mark.parametrize("value, step, rounded", [
        (2.5, 1, 3), (-2.5, 1, -3), (-1.8, 1, -2), (0.01, 1, 0), (10.97, 1, 11), (11.01, 1, 11),
        (783.5, 100, 800), (780, 100, 800), (2250, 100, 2300), (2295.72, 100, 2300),
        (2292, 100, 2300), (2287, 100, 2300), (6169.67, 100, 6200), (0.25, Decimal("0.1"), Decimal("0.3")),
    ])
    def test_round_half_away_from_zero(self, value, step, rounded):
        assert round_to_step(value, Decimal(step)) == rounded

    def test_rounded_negative_zero_prints_zero(self):
        assert format_number(round_to_step(-0.4, Decimal(1))) == "0"

    def test_format_number_with_a_step(self):
        assert format_number(2295.72, step=Decimal(100)) == "2,300"
        assert format_number(-1.799999475479126, step=Decimal(1)) == "-2"

    @pytest.mark.parametrize("d, v", [(Decimal("8E+2"), 800), (Decimal("1"), 1),
                                      (Decimal("0.1"), 0.1), (Decimal("-0"), 0),
                                      (Decimal("182.5"), 182.5)])
    def test_number_value(self, d, v):
        out = number_value(d)
        assert out == v and type(out) is type(v)


# --- fitting (research R3, FR-013) -------------------------------------------------------------

def spec(text, field="line", preferred=7.0, max_lines=2, bold=False, align="left"):
    return TextSpec(field=field, text=text, preferred_pt=preferred, max_lines=max_lines, bold=bold,
                    align=align)


class TestFitBlock:
    def test_preferred_size_on_one_line(self):
        b = fit_block(spec("Ocean temperature", "title", 14.0, 2, bold=True), sticker="large",
                      x=2.5, y=2.5, width_mm=120.8)
        assert isinstance(b, TextBlock)
        assert b.field == "title" and b.lines == ("Ocean temperature",)
        assert b.size_pt == b.preferred_pt == 14.0 and b.min_pt == MIN_PT == 5.0 and b.bold
        assert b.box == pytest.approx((2.5, 2.5, 120.8, block_height(1, 14.0)))

    def test_wraps_at_spaces_without_truncating(self):
        b = fit_block(spec(LONG, max_lines=5), sticker="small", x=0, y=0, width_mm=40.8)
        assert b.size_pt == 7.0 and 1 < len(b.lines) <= 5
        assert " ".join(b.lines) == LONG
        assert not any("..." in line for line in b.lines)
        for line in b.lines:
            assert text_width(line, b.size_pt) <= 40.8

    def test_wraps_greedily(self):
        b = fit_block(spec(LONG, max_lines=5), sticker="small", x=0, y=0, width_mm=40.8)
        for line, nxt in zip(b.lines, b.lines[1:]):
            assert text_width(f"{line} {nxt.split(' ')[0]}", b.size_pt) > 40.8

    def test_shrinks_in_quarter_points_when_the_lines_run_out(self):
        b = fit_block(spec(LONG, max_lines=2), sticker="small", x=0, y=0, width_mm=60.0)
        assert MIN_PT <= b.size_pt < 7.0 and len(b.lines) <= 2
        assert ((7.0 - b.size_pt) / STEP_PT).is_integer() and STEP_PT == 0.25
        assert " ".join(b.lines) == LONG
        bigger = fit_block(spec(LONG, max_lines=3), sticker="small", x=0, y=0, width_mm=60.0)
        assert bigger.size_pt > b.size_pt   # the largest size that fits is chosen
        # one step larger does not fit in two lines
        with pytest.raises(StickerError):
            fit_block(TextSpec("line", LONG, b.size_pt + STEP_PT, 2, min_pt=b.size_pt + STEP_PT),
                      sticker="small", x=0, y=0, width_mm=60.0)

    def test_height_limit_shrinks(self):
        h = block_height(1, 6.0)
        b = fit_block(spec("Two words", preferred=7.0, max_lines=1), sticker="large", x=0, y=0,
                      width_mm=100.0, height_mm=h)
        assert b.size_pt == 6.0 and b.box[3] <= h + 1e-9

    def test_never_below_five_points(self):
        with pytest.raises(StickerError) as e:
            fit_block(spec(LONG * 3, max_lines=2), sticker="small", x=0, y=0, width_mm=40.8)
        err = e.value
        assert err.sticker == "small" and err.field == "line"
        assert err.needed_mm > err.available_mm
        assert err.available_mm == pytest.approx(block_height(2, MIN_PT))
        msg = str(err)
        assert "small sticker" in msg and "line" in msg and "5 pt" in msg and "mm" in msg
        assert "..." not in msg

    def test_a_word_wider_than_the_block_at_five_points(self):
        word = "W" * 40
        with pytest.raises(StickerError) as e:
            fit_block(spec(f"A {word} title", "title", 11.0, 3, bold=True), sticker="small",
                      x=0, y=0, width_mm=40.8)
        err = e.value
        assert err.sticker == "small" and err.field == "title"
        assert err.needed_mm == pytest.approx(text_width(word, MIN_PT, bold=True))
        assert err.available_mm == pytest.approx(40.8)
        assert "small sticker" in str(err) and "title" in str(err) and "40.8 mm" in str(err)

    def test_disclaimer_fits_the_small_sticker_at_five_points(self):
        b = fit_block(spec(DISCLAIMER, "disclaimer", 5.0, 2), sticker="small", x=0, y=0,
                      width_mm=40.8)
        assert b.lines == (DISCLAIMER,) and b.size_pt == 5.0

    def test_normalises_spaces(self):
        b = fit_block(spec("Two  spaces "), sticker="large", x=0, y=0, width_mm=100.0)
        assert b.lines == ("Two spaces",)

    def test_baselines_inside_the_box(self):
        b = fit_block(spec(LONG, max_lines=5), sticker="small", x=0, y=10.0, width_mm=40.8)
        ys = b.baselines()
        assert len(ys) == len(b.lines)
        assert all(10.0 < y < 10.0 + b.box[3] for y in ys)
        assert ys == sorted(ys)
        assert ys[1] - ys[0] == pytest.approx(line_pitch(b.size_pt))

    @pytest.mark.parametrize("align, x", [("left", 3.0), ("center", 23.4), ("right", 43.8)])
    def test_items(self, align, x):
        b = fit_block(spec("Ocean temperature", align=align), sticker="small", x=3.0, y=0,
                      width_mm=40.8)
        items = b.items(color=(255, 255, 255))
        assert [t.text for t in items] == ["Ocean temperature"]
        t = items[0]
        assert (t.x, t.align, t.size_pt, t.tag, t.color) == (pytest.approx(x), align, 7.0, "line",
                                                            (255, 255, 255))


class TestFitStack:
    def test_fits_at_preferred_sizes_top_down(self):
        blocks = fit_stack([spec("Ocean temperature", "title", 11.0, 3, bold=True, align="center"),
                            spec(LONG, "line", 7.0, 5, align="center")],
                           sticker="small", x=2.5, y=2.5, width_mm=40.8, height_mm=35.0, gap_mm=1.5)
        title, line = blocks
        assert (title.size_pt, line.size_pt) == (11.0, 7.0)
        assert title.box[1] == pytest.approx(2.5)
        assert line.box[1] == pytest.approx(2.5 + title.box[3] + 1.5)

    def test_shrinks_together_until_the_stack_fits(self):
        specs = [spec("Ocean temperature", "title", 11.0, 3, bold=True),
                 spec(LONG, "line", 7.0, 5)]
        full = fit_stack(specs, sticker="small", x=0, y=0, width_mm=40.8, height_mm=100.0)
        need = sum(b.box[3] for b in full)
        blocks = fit_stack(specs, sticker="small", x=0, y=0, width_mm=40.8, height_mm=need * 0.8)
        assert sum(b.box[3] for b in blocks) <= need * 0.8 + 1e-9
        assert blocks[0].size_pt < 11.0 and blocks[1].size_pt < 7.0
        assert all(b.size_pt >= MIN_PT for b in blocks)
        # the same number of quarter steps off each preferred size (until a block reaches 5 pt)
        assert 11.0 - blocks[0].size_pt == pytest.approx(7.0 - blocks[1].size_pt)

    def test_a_stack_that_does_not_fit_names_its_fields(self):
        specs = [spec("Ocean temperature", "title", 11.0, 3, bold=True), spec(LONG, "line", 7.0, 5)]
        with pytest.raises(StickerError) as e:
            fit_stack(specs, sticker="small", x=0, y=0, width_mm=40.8, height_mm=5.0)
        err = e.value
        assert err.sticker == "small" and "title" in err.field and "line" in err.field
        assert err.available_mm == pytest.approx(5.0) and err.needed_mm > 5.0


class TestParagraphs:
    """A block of several paragraphs, each on a new line, all at one size (the large sticker's
    "Data:" credit, one dataset per line; research R3, R9)."""

    def test_each_paragraph_starts_a_new_line(self):
        s = TextSpec("credit", "", 5.5, 6, paragraphs=("Data: A, doi:1", "B, doi:2"))
        b = fit_block(s, sticker="large", x=0, y=0, width_mm=120.8)
        assert b.lines == ("Data: A, doi:1", "B, doi:2") and b.size_pt == 5.5

    def test_paragraphs_wrap_and_shrink_together(self):
        paras = (f"Data: {LONG}", LONG)
        wide = fit_block(TextSpec("credit", "", 5.5, 6, paragraphs=paras), sticker="large", x=0,
                         y=0, width_mm=60.0)
        assert len(wide.lines) > 2 and wide.size_pt == 5.5
        assert " ".join(wide.lines) == " ".join(paras)            # never truncated
        tight = fit_block(TextSpec("credit", "", 5.5, 3, paragraphs=paras), sticker="large", x=0,
                          y=0, width_mm=90.0)
        assert len(tight.lines) == 3 and MIN_PT <= tight.size_pt < 5.5
        with pytest.raises(StickerError) as e:   # two paragraphs never share a line
            fit_block(TextSpec("credit", "", 5.5, 1, paragraphs=paras), sticker="large", x=0, y=0,
                      width_mm=90.0)
        assert e.value.field == "credit" and e.value.needed_mm > e.value.available_mm

    def test_text_is_unused_when_paragraphs_are_set(self):
        s = TextSpec("credit", "ignored", 5.5, 2, paragraphs=("one",))
        assert s.parts() == ("one",) and s.words() == ["one"]
        assert TextSpec("line", "a b", 7.0, 1).parts() == ("a b",)


class TestBalancedTitle:
    """A sticker title that wraps is balanced (the project owner's approval of the sticker texts,
    2026-11-24, T042): the greedy wrap's line count, with break points at spaces that make the
    widest line as narrow as possible, so the last line is not a single short word. A title does
    not break between a word and the number after it ("kit 31203", "December 1997") unless no
    split with that line count fits otherwise. Only the ``title`` field; the sizes chosen are the
    greedy wrap's (research R3 unchanged)."""

    SMALL_W = 40.8          # the small sticker's safe width (geometry: 45.8 - 2 x 2.5 mm)

    @staticmethod
    def title(text, max_lines=3, preferred=11.0):
        return TextSpec("title", text, preferred, max_lines, bold=True, align="center")

    @staticmethod
    def splits(words, n):
        import itertools

        for cuts in itertools.combinations(range(1, len(words)), n - 1):
            b = (0, *cuts, len(words))
            yield [" ".join(words[b[i]:b[i + 1]]) for i in range(n)]

    @pytest.mark.parametrize("text, lines", [
        ("El Niño, December 1997", ("El Niño,", "December 1997")),
        ("La Niña, December 1988", ("La Niña,", "December 1988")),
        ("World Map, kit 31203 design", ("World Map,", "kit 31203 design")),
        ("Kit 31203 look, from bathymetry", ("Kit 31203 look,", "from bathymetry")),
        ("Rainfall over land and sea", ("Rainfall over", "land and sea")),
    ])
    def test_two_line_titles_are_balanced(self, text, lines):
        b = fit_block(self.title(text), sticker="small", x=0, y=0, width_mm=self.SMALL_W)
        assert b.lines == lines and b.size_pt == 11.0
        greedy = wrap_words(text, 11.0, self.SMALL_W, True)
        assert len(greedy) == len(lines) and tuple(greedy) != lines   # greedy ends badly
        assert len(lines[-1].split()) > 1                               # not a single word
        assert " ".join(b.lines) == text

    @pytest.mark.parametrize("text, width", [
        ("Plant productivity and ocean chlorophyll", 40.8),
        ("Sea surface temperature anomaly of a strong El Niño", 40.8),
        ("Rainfall over land and sea", 40.8),
        ("Annual mean precipitation over land and sea", 30.0),
    ])
    def test_the_widest_line_is_as_narrow_as_it_can_be(self, text, width):
        b = fit_block(self.title(text), sticker="small", x=0, y=0, width_mm=width)
        greedy = wrap_words(text, b.size_pt, width, True)
        assert len(b.lines) == len(greedy) > 1          # the greedy wrap's line count
        widest = max(text_width(ln, b.size_pt, True) for ln in b.lines)
        best = min(max(text_width(ln, b.size_pt, True) for ln in ls)
                   for ls in self.splits(text.split(), len(greedy)))
        assert widest == pytest.approx(best)
        assert widest <= max(text_width(ln, b.size_pt, True) for ln in greedy) + 1e-9
        assert all(text_width(ln, b.size_pt, True) <= width + 1e-9 for ln in b.lines)

    def test_no_break_before_a_number(self):
        text = "World Map, kit 31203 design"
        b = fit_block(self.title(text), sticker="small", x=0, y=0, width_mm=self.SMALL_W)
        assert b.lines == ("World Map,", "kit 31203 design")
        # a split before "31203" has a narrower widest line, but keeps "kit 31203" apart
        narrow = max(text_width(ln, 11.0, True) for ln in ("World Map, kit", "31203 design"))
        assert narrow < max(text_width(ln, 11.0, True) for ln in b.lines)

    def test_breaks_before_a_number_when_nothing_else_fits(self):
        # "kit 31203" (16.4 mm) is wider than 15 mm, so the only two-line split that fits is used
        b = fit_block(self.title("Map kit 31203"), sticker="small", x=0, y=0, width_mm=15.0)
        assert b.lines == ("Map kit", "31203") and b.size_pt == 11.0

    @pytest.mark.parametrize("text", ["Ocean temperature", "Land elevation", "Rainfall",
                                      "Living planet"])
    def test_one_line_titles_unchanged(self, text):
        b = fit_block(self.title(text), sticker="small", x=0, y=0, width_mm=self.SMALL_W)
        assert b.lines == (text,)

    @pytest.mark.parametrize("text, width, max_lines", [
        ("El Niño, December 1997", 40.8, 3), ("World Map, kit 31203 design", 40.8, 3),
        ("Sea surface temperature anomaly of a strong El Niño", 40.8, 3),
        ("Sea surface temperature anomaly of a strong El Niño", 40.8, 2),
        ("Kit 31203 look, from bathymetry", 30.0, 2), (LONG, 103.7, 2), (LONG, 40.8, 3),
    ])
    def test_sizes_and_line_counts_are_the_greedy_wraps(self, text, width, max_lines):
        """Shrinking (research R3) is unchanged: the same size and number of lines as a greedy
        block of the same text, only the break points move."""
        title = self.title(text, max_lines=max_lines)
        greedy = dataclasses.replace(title, field="line")
        b = fit_block(title, sticker="small", x=0, y=0, width_mm=width)
        g = fit_block(greedy, sticker="small", x=0, y=0, width_mm=width)
        assert (b.size_pt, len(b.lines), b.box) == (g.size_pt, len(g.lines), g.box)
        assert " ".join(b.lines) == " ".join(g.lines) == " ".join(text.split())

    def test_too_long_still_names_the_title(self):
        with pytest.raises(StickerError) as e:
            fit_block(self.title(LONG * 2), sticker="small", x=0, y=0, width_mm=self.SMALL_W)
        assert e.value.field == "title" and e.value.needed_mm > e.value.available_mm

    def test_other_fields_wrap_greedily(self):
        text = "El Niño, December 1997"
        for field in ("line", "credit", "disclaimer", "header"):
            s = TextSpec(field, text, 11.0, 3, bold=True)
            b = fit_block(s, sticker="small", x=0, y=0, width_mm=self.SMALL_W)
            assert list(b.lines) == wrap_words(text, 11.0, self.SMALL_W, True) == [
                "El Niño, December", "1997"], field

    def test_in_a_stack(self):
        """The small sticker sets its title and line as one stack (``fit_stack``)."""
        blocks = fit_stack([self.title("El Niño, December 1997"),
                            spec(LONG, "line", 7.0, 5, align="center")],
                           sticker="small", x=0, y=0, width_mm=self.SMALL_W, height_mm=30.0,
                           gap_mm=2.0)
        assert blocks[0].lines == ("El Niño,", "December 1997")
        # shrunk together, the title stays balanced
        tight = fit_stack([self.title("El Niño, December 1997"),
                           spec(LONG, "line", 7.0, 5, align="center")],
                          sticker="small", x=0, y=0, width_mm=self.SMALL_W, height_mm=16.0,
                          gap_mm=2.0)
        assert tight[0].size_pt < 11.0
        assert tight[0].lines in {("El Niño,", "December 1997"), ("El Niño, December 1997",)}

    def test_balanced_wrap_function(self):
        from lego_image_processor.stickers.text import balanced_wrap

        assert balanced_wrap("El Niño, December 1997", 11.0, self.SMALL_W, True) == [
            "El Niño,", "December 1997"]
        assert balanced_wrap("Ocean temperature", 11.0, self.SMALL_W, True) == ["Ocean temperature"]
        assert balanced_wrap("", 11.0, self.SMALL_W, True) == []
        # more lines than allowed: the greedy wrap as it is (the block does not fit anyway)
        assert balanced_wrap(LONG, 11.0, self.SMALL_W, True, max_lines=2) == wrap_words(
            LONG, 11.0, self.SMALL_W, True)
