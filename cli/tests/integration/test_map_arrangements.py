"""Recipes built in arrangements A, B and C (feature 007 US1: FR-004-FR-009, SC-001, SC-003, SC-004)."""

from collections import Counter

import numpy as np
import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe, parse_recipe
from lego_image_processor.maps.texture import shadow_mask

ARR = ("A", "B", "C", "D", "E")  # feature 010 adds D and E


def _grid(layout, attr="color_id"):
    g = np.empty((80, 128), dtype=object)
    for p in layout.positions:
        g[p.y, p.x] = getattr(p, attr)
    return g


@pytest.fixture
def maps(fixture_registry):
    fixture_registry.place_all()
    cache = {}

    class _Maps:
        def __getitem__(self, key):
            rid, aid = key
            if key not in cache:
                cache[key] = build_map(load_recipe(rid), arrangement=parse_arrangement(aid))
            return cache[key]
    return _Maps()


@pytest.mark.parametrize("aid", ARR)
def test_official_equals_shifted_design(aid):
    a = parse_arrangement(aid)
    m = build_map(load_recipe("official-31203"), arrangement=a)
    d = load_official_design()
    g = _grid(m.layout)
    for y in range(80):
        for x in range(128):
            assert g[y, x] == d.color_at(a.to_kit(x), y)
    assert m.agreement["total"]["agree"] == 10240
    assert m.layout.arrangement["id"] == aid
    assert m.report["arrangement"]["id"] == aid
    assert m.report["shadow"]["enabled"] is False


def test_default_build_is_a_and_unchanged():
    m = build_map(load_recipe("official-31203"))
    assert m.layout.arrangement["id"] == "A"
    a = build_map(load_recipe("official-31203"), arrangement=parse_arrangement("A"))
    assert [p.to_dict() for p in m.layout.positions] == [p.to_dict() for p in a.layout.positions]


@pytest.mark.parametrize("aid", ARR)
def test_parts_follow_shifted_mask(aid):
    a = parse_arrangement(aid)
    m = build_map(load_recipe("official-31203"), arrangement=a)
    land = a.roll(land_mask_array())
    parts = _grid(m.layout, "part_type")
    assert ((parts == "plate") == land).all()


@pytest.mark.parametrize("rid", ["land-elevation", "ocean-sst"])
@pytest.mark.parametrize("aid", ARR)
def test_shadow_is_east_of_land_as_hung(maps, rid, aid):
    a = parse_arrangement(aid)
    m = maps[rid, aid]
    land = a.roll(land_mask_array())
    expected = np.zeros_like(land)
    expected[:, 1:] = land[:, :-1] & ~land[:, 1:]
    g = _grid(m.layout)
    assert (g[expected] == "lego_earth_blue").all()
    assert not expected[:, 0].any()
    assert m.report["shadow"]["cells"] == int(expected.sum())
    assert (shadow_mask(land) == expected).all()


def test_shadow_counts_differ_only_at_seams(maps):
    land = land_mask_array()
    for aid in ("B", "C", "D", "E"):
        a = parse_arrangement(aid)
        sa = shadow_mask(land)
        sx = a.unroll(shadow_mask(a.roll(land)))  # back in kit columns
        diff = np.flatnonzero((sa != sx).any(axis=0))
        old_seam = {0}
        new_seam = {a.to_kit(0)}  # the kit column now at the outer left edge
        assert set(diff.tolist()) <= old_seam | new_seam


def test_land_counts_and_cells_equal_across_arrangements(maps):
    """bins + blend on land run in kit coordinates: identical land cells in every arrangement."""
    base = _grid(maps["land-elevation", "A"].layout)
    land = land_mask_array()
    for aid in ("B", "C", "D", "E"):
        a = parse_arrangement(aid)
        g = a.unroll(_grid(maps["land-elevation", aid].layout))
        assert (g[land] == base[land]).all()
        assert Counter(g[land]) == Counter(base[land])


def test_ocean_rank_counts_follow_supply(maps):
    """rank-to-supply: counts differ only by how many ocean cells the shadow takes."""
    for aid in ARR:
        m = maps["ocean-sst", aid]
        ocean = next(l for l in m.report["layers"] if l["class"] == "ocean")
        assert ocean["cells"] == 7178 - m.report["shadow"]["cells"]


def test_halo_distance_as_hung(maps):
    """Halo ring cells (within 1.5 studs of land) are computed on the grid as hung, no wrap."""
    from scipy.ndimage import distance_transform_edt

    for aid in ARR:
        a = parse_arrangement(aid)
        land = a.roll(land_mask_array())
        g = _grid(maps["land-elevation", aid].layout)
        shadow = shadow_mask(land)
        dist = distance_transform_edt(~land)
        ring = ~land & ~shadow & (dist <= 1.5)
        assert (g[ring] == "lego_medium_azur").all()


def test_mix_does_not_wrap_columns():
    from lego_image_processor.maps.texture import fill_background

    mask = np.ones((80, 128), dtype=bool)
    a = fill_background(mask, [1, 1], cluster=3, seed=(1, 2))
    # Without a column wrap, the noise at the left edge does not see the right edge: shifting the
    # noise field's columns changes the result near the edges.
    assert a.shape == (80, 128) and set(np.unique(a)) == {0, 1}
    from scipy import ndimage
    rng = np.random.default_rng((1, 2))
    noise = ndimage.gaussian_filter(rng.standard_normal(mask.shape), sigma=3, mode="nearest")
    order = np.argsort(noise.ravel(), kind="stable")
    expect = np.empty(mask.size, dtype=int)
    expect[order] = np.repeat([0, 1], [5120, 5120])
    assert (a.ravel() == expect).all()


def test_mix_background_recipe_in_b():
    text = """
format = "1"
id = "mix-test"
title = "Mix"
seed = 7
[shadow]
enabled = false
[land]
role = "background"
colors = ["lego_white", "lego_black"]
weights = [1, 1]
[land.texture]
kind = "mix"
cluster = 2
[ocean]
role = "background"
colors = ["lego_earth_blue"]
weights = [1]
"""
    r = parse_recipe(text)
    counts = {}
    for aid in ARR:
        m = build_map(r, arrangement=parse_arrangement(aid))
        counts[aid] = Counter(p.color_id for p in m.layout.positions if p.part_type == "plate")
    assert counts["A"] == counts["B"] == counts["C"]


@pytest.mark.parametrize("aid", ("B", "C"))
def test_agreement_compares_shifted_design(maps, aid):
    a_ag = maps["official-31203-bathymetry", "A"].agreement
    x_ag = maps["official-31203-bathymetry", aid].agreement
    assert x_ag["land"] == a_ag["land"]
    # Ocean agreement differs only through the shadow cells at the seams.
    assert abs(x_ag["ocean"]["agree"] - a_ag["ocean"]["agree"]) < 200


def test_metadata_record(maps):
    m = maps["ocean-sst", "C"]
    rec = m.layout.arrangement
    assert rec["id"] == "C" and rec["column_shift"] == -32 and rec["frame_order"] == [2, 3, 1]
    assert rec["source"]["pages"] == [7, 8]
