"""A cached dataset is used offline; an altered cache file fails with the fetch hint (US2 4, 6)."""

import pytest

from lego_image_processor.datasets import ChecksumMismatchError
from lego_image_processor.maps.build import build_map
from lego_image_processor.maps.recipe import load_recipe


def test_cached_builds_offline(fixture_registry):
    fixture_registry.place("ersst-v5-ltm-1991-2020")
    r = build_map(load_recipe("ocean-sst"))   # the session offline guard is active
    assert r.layout.ocean_positions == 7_178


def test_altered_file_fails(fixture_registry):
    p = fixture_registry.place("ersst-v5-ltm-1991-2020")
    data = bytearray(p.read_bytes())
    data[-1] ^= 0xFF
    p.write_bytes(bytes(data))
    with pytest.raises(ChecksumMismatchError) as e:
        build_map(load_recipe("ocean-sst"))
    assert "dataset fetch ersst-v5-ltm-1991-2020" in str(e.value)
