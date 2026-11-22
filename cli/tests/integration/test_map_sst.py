"""ocean-sst on the ERSST fixture (US3 scenarios 2, 3, 5)."""

import numpy as np
import pytest

from lego_image_processor.layout.kit_spec import load_kit_specification
from lego_image_processor.layout.validator import LayoutValidator
from lego_image_processor.maps import build as b
from lego_image_processor.maps.build import build_map, land_mask_array
from lego_image_processor.maps.recipe import load_recipe
from lego_image_processor.palette.loader import LegoPalette


@pytest.fixture
def built(fixture_registry):
    fixture_registry.place_all()
    return build_map(load_recipe("ocean-sst"))


def test_monotonic_before_texture(fixture_registry):
    fixture_registry.place_all()
    r = load_recipe("ocean-sst")
    mask = ~land_mask_array()
    _, fld, cr = b._layer_classes(r.ocean, mask, r.seed, None)
    v, c = fld.values[mask], cr.classes[mask]
    assert (np.diff(c[np.argsort(v, kind="stable")]) >= 0).all()
    ocean = r.ocean.colors
    assert ocean[0] == "lego_earth_blue" and ocean[-1] == "lego_vibrant_coral"


def test_within_supply_and_buildable(built):
    spec = load_kit_specification()
    counts = built.layout.compute_statistics().color_frequency_by_part_type["tile"]
    assert all(n <= spec.get_tile_quantity(k) for k, n in counts.items())
    assert LayoutValidator(spec, LegoPalette.load_default()).validate(built.layout, "x").buildable


def test_filled_share_reported(built):
    ocean = next(l for l in built.report["layers"] if l["class"] == "ocean")
    assert 0.02 < ocean["filled_share"] < 0.05
    assert ocean["filled_cells"] == round(ocean["filled_share"] * 7178)
    assert not [w for w in ocean["warnings"] if w["code"] in ("filled", "detail_lost", "empty_class")]


def test_deterministic(built, fixture_registry):
    again = build_map(load_recipe("ocean-sst"))
    assert [p.color_id for p in again.layout.positions] == [p.color_id for p in built.layout.positions]


def test_citation_in_layout(built):
    ds = built.layout.map_metadata["layers"][1]["dataset"]
    assert ds["id"] == "ersst-v5-ltm-1991-2020"
    assert "Public domain" in ds["license"] and ds["doi"] == "10.1175/JCLI-D-16-0836.1"
    assert "psl.noaa.gov" in ds["acknowledgement"]
