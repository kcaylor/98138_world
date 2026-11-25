"""SC-006: each bundled recipe builds from cached data well under 30 s (fixtures here).

Feature 017 SC-007: making a map's sticker set (composing both stickers, the print sheet PDF on
Letter and A4, both SVGs and the JSON summary) adds less than 5 s to building the map.
"""

import time

import pytest

from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe
from lego_image_processor.stickers import (render_sticker_json, render_sticker_pdf,
                                           render_sticker_svgs, sticker_set)
from tests.stickers_support import sticker_recipe


@pytest.mark.parametrize("rid", sorted(bundled_recipes()))
def test_build_time(rid, fixture_registry):
    fixture_registry.place_all()
    t0 = time.monotonic()
    build_map(load_recipe(rid))
    assert time.monotonic() - t0 < 30


def _full_sticker_set(result):
    """Everything `map stickers` and the web prebuild make from one built map."""
    s = sticker_set(result)
    out = [render_sticker_pdf(s, "letter"), render_sticker_pdf(s, "a4")]
    out += [text.encode("utf-8") for _, text in render_sticker_svgs(s)]
    out.append(render_sticker_json(s).encode("utf-8"))
    return out


def test_sticker_set_adds_less_than_5_s(fixture_registry):
    """SC-007 (feature 017): on the slowest fixture map, and on every other one, the full
    sticker set takes less than 5 s on top of the build."""
    fixture_registry.place_all()
    timings = {}
    for rid in sorted(bundled_recipes()):
        recipe = sticker_recipe(rid)
        t0 = time.monotonic()
        result = build_map(recipe, cache_dir=fixture_registry.cache_dir, compare_official=False)
        t1 = time.monotonic()
        files = _full_sticker_set(result)
        t2 = time.monotonic()
        assert len(files) == 5 and all(files)
        timings[rid] = (t1 - t0, t2 - t1)
    slowest = max(timings, key=lambda rid: timings[rid][0])
    build_s, stickers_s = timings[slowest]
    assert stickers_s < 5, f"{slowest}: stickers took {stickers_s:.2f} s after a {build_s:.2f} s build"
    for rid, (build_s, stickers_s) in timings.items():
        assert stickers_s < 5, f"{rid}: stickers took {stickers_s:.2f} s"


# --- Feature 016 (T060; plan Performance Goals): Winkel builds and template loads ---------------

WINKEL_RECIPES = ("land-elevation", "ocean-sst", "rainfall")
_SLACK = 0.02  # seconds: fixture builds take about 10-30 ms, so allow for timer and scheduler noise


def _best(fn, n=5):
    best = float("inf")
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


@pytest.mark.parametrize("rid", WINKEL_RECIPES)
def test_winkel_build_within_twice_the_kit_build(rid, fixture_registry, confirmed_winkel):
    fixture_registry.place_all()
    recipe = load_recipe(rid)
    build_map(recipe), build_map(recipe, template="winkel-tripel")  # warm the readers and caches
    kit = _best(lambda: build_map(recipe))
    winkel = _best(lambda: build_map(recipe, template="winkel-tripel"))
    assert winkel <= 2 * kit + _SLACK, (rid, kit, winkel)


def test_template_load_when_cached(confirmed_winkel):
    from lego_image_processor.templates import load_template

    load_template("winkel-tripel")
    assert _best(lambda: load_template("winkel-tripel"), n=3) < 0.1
