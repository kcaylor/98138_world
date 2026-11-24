"""Margin treatment (T042; data-model.md MarginTreatment; research R12; spec Edge Cases, US1-4,
US1-5): the recipe's ``[margin]`` overridden per field by ``--margin-color`` and ``--ring-color``.
Not affiliated with or endorsed by The LEGO Group.
"""

import numpy as np
import pytest

from lego_image_processor.kit.part_colors import load_part_colors
from lego_image_processor.maps.margin import (DEFAULT_MARGIN_COLOR, MARGIN_PART_ID, NO_RING,
                                              MarginError, MarginTreatment, margin_colors,
                                              margin_labels, resolve_margin, ring_cells,
                                              ring_rule)


def _assert_lists_colors(msg):
    """The error lists the available 3070b color keys and points to ``kit part-colors``."""
    assert "part 3070b" in msg and "kit part-colors --part 3070b" in msg
    for key in margin_colors():
        assert key in msg


def test_part_and_default():
    assert MARGIN_PART_ID == "3070b"
    assert MarginTreatment() == MarginTreatment(color=DEFAULT_MARGIN_COLOR, ring=None)
    assert DEFAULT_MARGIN_COLOR == "lego_black" and NO_RING == "none"


def test_margin_colors_are_the_cited_square_tile_colors():
    keys = margin_colors()
    assert keys == tuple(c.key for c in load_part_colors().for_part("3070b"))
    assert "lego_black" in keys and len(keys) == len(set(keys))


class TestResolve:
    def test_default_black_no_ring(self):  # US1-4
        assert resolve_margin(None) == MarginTreatment("lego_black", None)

    def test_recipe_used(self):
        base = MarginTreatment("lego_dark_stone_grey", "lego_bright_yellow")
        assert resolve_margin(base) == base

    def test_options_override_per_field(self):
        base = MarginTreatment("lego_dark_stone_grey", "lego_bright_yellow")
        assert resolve_margin(base, margin_color="lego_white") == MarginTreatment("lego_white", "lego_bright_yellow")
        assert resolve_margin(base, ring_color="lego_white") == MarginTreatment("lego_dark_stone_grey", "lego_white")
        assert resolve_margin(None, ring_color="lego_white") == MarginTreatment("lego_black", "lego_white")

    def test_none_turns_a_recipe_ring_off(self):
        base = MarginTreatment("lego_black", "lego_bright_yellow")
        assert resolve_margin(base, ring_color="none") == MarginTreatment("lego_black", None)
        assert resolve_margin(base, ring_color="NONE") == MarginTreatment("lego_black", None)

    @pytest.mark.parametrize("kw,where", [({"margin_color": "lego_vibrant_coral"}, "--margin-color"),
                                          ({"ring_color": "lego_vibrant_coral"}, "--ring-color")])
    def test_option_color_not_a_square_tile_color(self, kw, where):
        with pytest.raises(MarginError) as e:
            resolve_margin(None, **kw)
        msg = str(e.value)
        assert e.value.where == where and msg.startswith(where)
        assert "lego_vibrant_coral" in msg and "part 3070b" in msg
        assert "kit part-colors --part 3070b" in msg
        for key in margin_colors():  # the available 3070b color keys
            assert key in msg

    def test_unknown_key(self):
        with pytest.raises(MarginError, match=r"--margin-color.*'not-a-color'"):
            resolve_margin(None, margin_color="not-a-color")

    def test_ring_equal_to_margin_option(self):
        with pytest.raises(MarginError) as e:
            resolve_margin(None, ring_color="lego_black")
        assert e.value.where == "--ring-color" and "differ" in str(e.value)
        _assert_lists_colors(str(e.value))

    def test_ring_equal_to_margin_from_margin_option(self):
        """The recipe's ring is fine, the option's margin color makes them equal: the option is named."""
        with pytest.raises(MarginError) as e:
            resolve_margin(MarginTreatment("lego_black", "lego_white"), margin_color="lego_white")
        assert e.value.where == "--margin-color"
        _assert_lists_colors(str(e.value))

    def test_ring_equal_in_recipe_values(self):
        with pytest.raises(MarginError) as e:
            resolve_margin(MarginTreatment("lego_white", "lego_white"))
        assert e.value.where == "margin.ring"
        _assert_lists_colors(str(e.value))

    def test_ring_rule_text(self):
        """Spec Edge Cases ("the same color for both: error naming the available colors"),
        contracts/cli.md error table, research R12 (T111)."""
        rule = ring_rule("lego_white", "lego_white")
        assert rule.startswith("the ring color 'lego_white' must differ from the margin color 'lego_white'")
        _assert_lists_colors(rule)

    def test_recipe_color_checked(self):
        with pytest.raises(MarginError) as e:
            resolve_margin(MarginTreatment("lego_vibrant_coral", None))
        assert e.value.where == "margin.color"

    def test_provenance(self):
        t = MarginTreatment("lego_black", "lego_white")
        assert t.provenance({"margin": 1708, "ring": 288}) == {
            "part_id": "3070b", "color": "lego_black", "ring": "lego_white",
            "cells": {"margin": 1708, "ring": 288}}


class TestRingCells:
    def test_ring_is_margin_with_an_on_globe_neighbour(self, confirmed_winkel):
        t = confirmed_winkel
        ring = ring_cells(t)
        on = t.on_globe
        H, W = on.shape
        expect = np.zeros_like(on)
        for y in range(H):
            for x in range(W):
                if on[y, x]:
                    continue
                expect[y, x] = any(0 <= y + dy < H and 0 <= x + dx < W and on[y + dy, x + dx]
                                   for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        assert (ring == expect).all()
        assert int(ring.sum()) == t.counts["ring"]
        assert not (ring & on).any()

    def test_kit_has_no_ring(self):
        from lego_image_processor.templates import kit_template

        assert not ring_cells(kit_template()).any()

    def test_labels(self, confirmed_winkel):
        t = confirmed_winkel
        lab = margin_labels(t, MarginTreatment("lego_black", None))
        assert set(lab[t.margin]) == {"lego_black"} and (lab[t.on_globe] == None).all()  # noqa: E711
        lab = margin_labels(t, MarginTreatment("lego_black", "lego_white"))
        ring = ring_cells(t)
        assert set(lab[ring]) == {"lego_white"}
        assert set(lab[t.margin & ~ring]) == {"lego_black"}
        assert int((lab == "lego_white").sum()) == t.counts["ring"]
