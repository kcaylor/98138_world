"""Cell sampling, CIEDE2000 classification, ambiguity flagging and overrides (synthetic images)."""

import numpy as np
import pytest
from PIL import Image

from kit31203 import classify
from lego_image_processor.core import color_quantizer

from .synthetic_sections import patterned_grid, reference_colors, render_section, uniform_grid

KEYS, REFS = classify.load_reference_colors()


def _override(x, y, chosen, **extra):
    row = {"x": x, "y": y, "chosen": chosen, "reason": "test", "decided_by": "test",
           "decided_on": "2026-11-21"}
    row.update(extra)
    return row


class TestReferenceColors:
    def test_ten_kit_colours_in_kit_order(self):
        from lego_image_processor.kit import load_kit_colors
        assert list(KEYS) == [c.key for c in load_kit_colors()]
        assert REFS.shape == (10, 3)


class TestSampling:
    def test_cell_centres_use_own_width_and_height(self):
        c154 = {(i, j): (cx, cy) for i, j, cx, cy in classify.cell_centres(154, 154)}
        c153 = {(i, j): (cx, cy) for i, j, cx, cy in classify.cell_centres(154, 153)}
        assert len(c154) == 256
        assert c154[(0, 0)] == (int(0.5 * 154 / 16), int(0.5 * 154 / 16))
        assert c153[(15, 15)] == (int(15.5 * 154 / 16), int(15.5 * 153 / 16))
        assert c153[(15, 15)][1] < c154[(15, 15)][1]

    def test_median_of_5x5_patch(self):
        arr = np.full((154, 154, 3), 100, dtype=np.uint8)
        cx, cy = int(0.5 * 154 / 16), int(0.5 * 154 / 16)
        arr[cy - 2, cx - 2] = 255  # stud highlight: 2 of 25 pixels
        arr[cy + 2, cx + 2] = 255
        arr[cy, cx + 3] = 0        # outside the patch
        samples = classify.sample_cells(Image.fromarray(arr))
        assert samples.shape == (16, 16, 3)
        assert samples[0, 0].tolist() == [100, 100, 100]

    @pytest.mark.parametrize("size", [(154, 154), (154, 153)])
    def test_clean_synthetic_section_classified_correctly(self, size):
        grid = patterned_grid(list(KEYS))
        samples = classify.sample_cells(render_section(grid, size=size, seed=3))
        result = classify.classify(samples, KEYS, REFS)
        assert not result.flagged.any()
        got = [[KEYS[result.auto[j, i]] for i in range(16)] for j in range(16)]
        assert got == grid


class TestClassification:
    def test_uses_ciede2000_from_core(self):
        assert classify.delta_e_2000 is color_quantizer.delta_e_2000

    def test_follows_ciede2000_where_euclidean_rgb_disagrees(self):
        sample = np.array([[[111.0, 181.0, 182.0]]])
        rgb_nearest = KEYS[int(((REFS - sample[0, 0]) ** 2).sum(1).argmin())]
        result = classify.classify(sample, KEYS, REFS)
        assert rgb_nearest == "lego_medium_azur"
        assert KEYS[result.auto[0, 0]] == "lego_bright_bluish_green"

    def test_halfway_between_two_blues_is_flagged(self):
        colors = reference_colors()
        mid = [(a + b) / 2 for a, b in zip(colors["lego_medium_azur"], colors["lego_bright_bluish_green"])]
        grid = uniform_grid("lego_white")
        grid[5][7] = mid
        samples = classify.sample_cells(render_section(grid, seed=1))
        result = classify.classify(samples, KEYS, REFS)
        assert result.flagged[5, 7]
        assert result.ratio[5, 7] > classify.RATIO_THRESHOLD
        assert {KEYS[result.auto[5, 7]], KEYS[result.second[5, 7]]} == {
            "lego_medium_azur", "lego_bright_bluish_green"}
        assert result.flagged.sum() == 1

    def test_far_from_every_reference_is_flagged(self):
        sample = np.array([[[128.0, 0.0, 128.0]]])  # purple: no kit colour
        result = classify.classify(sample, KEYS, REFS, ratio_threshold=1.01)
        assert result.d1[0, 0] > classify.MAX_DELTA_E
        assert result.flagged[0, 0]


def _two_flagged():
    """A 1x3 strip: clear white, ambiguous blue, clear coral."""
    colors = reference_colors()
    mid = [(a + b) / 2 for a, b in zip(colors["lego_medium_azur"], colors["lego_bright_bluish_green"])]
    samples = np.array([[colors["lego_white"], mid, colors["lego_vibrant_coral"]]], dtype=float)
    return classify.classify(samples, KEYS, REFS)


class TestOverrides:
    def test_ambiguous_without_override_fails(self):
        result = _two_flagged()
        with pytest.raises(classify.ClassificationError) as exc:
            classify.apply_overrides(result, [])
        assert exc.value.exit_code == 7
        assert "1 ambiguous" in str(exc.value)
        assert "(1, 0)" in str(exc.value)
        assert "review" in str(exc.value)

    def test_lists_first_20_positions(self):
        colors = reference_colors()
        mid = [(a + b) / 2 for a, b in zip(colors["lego_medium_azur"], colors["lego_bright_bluish_green"])]
        samples = np.array([[mid] * 25], dtype=float)
        result = classify.classify(samples, KEYS, REFS)
        with pytest.raises(classify.ClassificationError) as exc:
            classify.apply_overrides(result, [])
        msg = str(exc.value)
        assert "25 ambiguous" in msg
        assert "(19, 0)" in msg and "(20, 0)" not in msg

    def test_override_resolves_and_is_recorded(self):
        result = _two_flagged()
        grid, applied = classify.apply_overrides(result, [_override(1, 0, "lego_medium_azur")])
        assert KEYS[grid[0, 1]] == "lego_medium_azur"
        assert KEYS[grid[0, 0]] == "lego_white"
        assert len(applied) == 1
        rec = applied[0]
        assert set(rec) == {"x", "y", "auto", "chosen", "ratio", "reason", "decided_by", "decided_on"}
        assert rec["auto"] in ("lego_medium_azur", "lego_bright_bluish_green")
        assert 0.6 < rec["ratio"] <= 1.0

    def test_contradicting_a_clear_cell_needs_force(self):
        result = _two_flagged()
        rows = [_override(1, 0, "lego_medium_azur"), _override(2, 0, "lego_bright_orange")]
        with pytest.raises(classify.ClassificationError) as exc:
            classify.apply_overrides(result, rows)
        assert exc.value.exit_code == 7
        assert "(2, 0)" in str(exc.value) and "force" in str(exc.value)
        rows[1]["force"] = True
        grid, applied = classify.apply_overrides(result, rows)
        assert KEYS[grid[0, 2]] == "lego_bright_orange"
        assert len(applied) == 2

    def test_override_agreeing_with_a_clear_cell_is_allowed(self):
        result = _two_flagged()
        rows = [_override(1, 0, "lego_medium_azur"), _override(0, 0, "lego_white")]
        grid, applied = classify.apply_overrides(result, rows)
        assert KEYS[grid[0, 0]] == "lego_white"

    @pytest.mark.parametrize("bad", [
        {"chosen": "lego_purple"},
        {"x": 99},
        {"reason": ""},
        {"decided_on": "yesterday"},
    ])
    def test_invalid_override_rows_fail(self, bad):
        result = _two_flagged()
        row = _override(1, 0, "lego_medium_azur")
        row.update(bad)
        with pytest.raises(classify.ClassificationError):
            classify.apply_overrides(result, [row])

    def test_duplicate_override_fails(self):
        result = _two_flagged()
        rows = [_override(1, 0, "lego_medium_azur"), _override(1, 0, "lego_bright_bluish_green")]
        with pytest.raises(classify.ClassificationError):
            classify.apply_overrides(result, rows)
