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
