"""Derived acceptance tier on the 1-degree ETOPO fixture (FR-021, SC-003, Q5).

Measured agreement on the fixture: 26.71% before the land shadow, 31.88% with it (004 amendment
2026-11-22: the shadow draws the official Earth Blue cells). The fixture threshold is the measured
value minus 1 point (30.8%), above the spec's 24% floor.
"""

import numpy as np
import pytest

from lego_image_processor.kit import load_official_design
from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.validator import LayoutValidator
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.palette.loader import LegoPalette

FIXTURE_THRESHOLD = 0.308


@pytest.fixture
def built(fixture_registry):
    fixture_registry.place_all()
    return build_map(load_recipe("official-31203-bathymetry"))


def test_land_identical_to_kit(built):
    land = [p for p in built.layout.positions if p.part_type == "plate"]
    assert len(land) == 3_062 and all(p.color_id == "lego_white" for p in land)
    assert built.agreement["land"]["share"] == 1.0


def test_within_supply_and_buildable(built):
    spec = load_kit_specification()
    counts = built.layout.compute_statistics().color_frequency_by_part_type["tile"]
    for key, n in counts.items():
        assert n <= spec.get_tile_quantity(key), key
    report = LayoutValidator(spec, LegoPalette.load_default()).validate(built.layout, "x")
    assert report.buildable


def test_counts_equal_official(built):
    official = {c.key: c.used for c in load_official_design().counts}
    counts = built.layout.compute_statistics().color_frequency_by_part_type["tile"]
    assert counts == {k: v for k, v in official.items() if k != "lego_white"}


def test_agreement_threshold(built):
    share = built.agreement["ocean"]["share"]
    assert share >= FIXTURE_THRESHOLD >= 0.24
    assert built.report["agreement_with_official"]["ocean"]["share"] == share


def test_median_depth_order(built):
    ocean = next(l for l in built.report["layers"] if l["class"] == "ocean")
    medians = [m["median"] for m in ocean["median_by_color"]]
    assert medians == sorted(medians)
    assert [m["key"] for m in ocean["median_by_color"]] == list(load_recipe("official-31203-bathymetry").ocean.colors)


def test_monotonic_before_texture(fixture_registry):
    fixture_registry.place_all()
    from lego_image_processor.maps import build as b
    r = load_recipe("official-31203-bathymetry")
    mask = ~land_mask_array()
    _, fld, cr = b._layer_classes(r.ocean, mask, r.seed, None)
    v, c = fld.values[mask], cr.classes[mask]
    assert (np.diff(c[np.argsort(v, kind="stable")]) >= 0).all()
