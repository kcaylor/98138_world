"""SC-006: each bundled recipe builds from cached data well under 30 s (fixtures here)."""

import time

import pytest

from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import bundled_recipes, load_recipe


@pytest.mark.parametrize("rid", sorted(bundled_recipes()))
def test_build_time(rid, fixture_registry):
    fixture_registry.place_all()
    t0 = time.monotonic()
    build_map(load_recipe(rid))
    assert time.monotonic() - t0 < 30


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
