"""The kit template ``kit-31203`` (feature 016, T027; FR-002): built in code from the kit's
existing files, the default and always buildable."""

import numpy as np
import pytest

from lego_image_processor.layout.arrangement import ARRANGEMENT_IDS
from lego_image_processor.maps.build import land_mask_array
from lego_image_processor.maps.projection import KitProjection, load_kit_projection
from lego_image_processor.maps.reproject import cell_centres
from lego_image_processor.templates import (KIT_TEMPLATE_ID, MARGIN_PART_ID, confirmed_templates,
                                            list_templates, load_template)
from lego_image_processor.templates.digest import layout_sha256
from maptemplates.testing import use_template_dir


@pytest.fixture
def kit():
    return load_template(KIT_TEMPLATE_ID)


def test_ids():
    assert KIT_TEMPLATE_ID == "kit-31203"
    assert MARGIN_PART_ID == "3070b"


def test_kit_is_the_reference_and_buildable(kit):
    assert kit.id == KIT_TEMPLATE_ID and kit.is_kit
    assert kit.status == "reference" and kit.buildable
    assert kit.confirmation is None and kit.corrections == ()
    assert kit.dataset is None and kit.path is None and kit.file_sha256 is None
    assert kit.title and kit.description


def test_classes_are_the_kit_land_sea_mask(kit):
    land = land_mask_array()
    assert kit.width == 128 and kit.height == 80
    assert (kit.land == land).all() and (kit.ocean == ~land).all()
    assert not kit.margin.any() and kit.on_globe.all()
    assert kit.counts["land"] == 3062 and kit.counts["ocean"] == 7178 and kit.counts["margin"] == 0
    assert kit.counts["ring"] == 0
    assert kit.counts["modules"] == {"full": 40, "partial": 0, "empty": 0}
    assert "".join(kit.classes).count("L") == 3062 and "M" not in "".join(kit.classes)


def test_locations_are_the_kit_cell_centres(kit):
    lat, lon = kit.locations()
    clat, clon = cell_centres(load_kit_projection())
    assert np.array_equal(lat, clat) and np.array_equal(lon, clon)
    p = load_kit_projection()
    assert kit.location(0, 0) == p.cell_center(0, 0)
    assert kit.location(79, 127) == p.cell_center(79, 127)


def test_projection_and_frame(kit):
    assert isinstance(kit.grid_projection, KitProjection)
    assert kit.grid_projection is load_kit_projection()
    assert kit.projection["name"] == "kit-31203-equirectangular"
    assert kit.arrangements == ARRANGEMENT_IDS == ("A", "B", "C")
    assert kit.frame == {"kit": "31203", "arrangements": ["A", "B", "C"], "source": "kit_31203_arrangements.json"}


def test_parts(kit):
    assert kit.parts == {"land": "6141", "ocean": "98138"}
    assert MARGIN_PART_ID not in kit.parts.values()


def test_layout_digest_from_the_in_code_layout(kit):
    assert len(kit.layout_sha256) == 64
    assert kit.layout_sha256 == layout_sha256(kit.document())
    assert load_template(KIT_TEMPLATE_ID).layout_sha256 == kit.layout_sha256


def test_needs_no_template_file(tmp_path):
    with use_template_dir(tmp_path / "does-not-exist"):
        t = load_template(KIT_TEMPLATE_ID)
        assert t.is_kit
        assert [x.id for x in list_templates()] == [KIT_TEMPLATE_ID]
        assert [x.id for x in confirmed_templates()] == [KIT_TEMPLATE_ID]


def test_no_kit_data_file_is_added():
    from lego_image_processor.templates import TEMPLATE_DIR

    assert not (TEMPLATE_DIR / f"{KIT_TEMPLATE_ID}.json").exists()


def test_cached(kit):
    assert load_template(KIT_TEMPLATE_ID) is kit
