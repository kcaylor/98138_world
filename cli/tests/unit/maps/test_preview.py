"""Preview PNG (FR-024): 8x8 px per stud, cited RGB; round studs on black by default."""

import pytest
from PIL import Image

from lego_image_processor.kit import load_kit_color_table, load_official_design
from lego_image_processor.maps.preview import stud_coverage, write_preview

SAMPLES = ((0, 0), (40, 20), (127, 79), (64, 40))


def _rgb(layout, x, y):
    return tuple(load_kit_color_table().by_key(layout.get_position(x, y).color_id).rgb)


def test_preview_round_on_black_by_default(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out)
    img = Image.open(out).convert("RGB")
    assert img.size == (1024, 640)
    for (x, y) in SAMPLES:
        assert img.getpixel((x * 8 + 4, y * 8 + 4)) == _rgb(layout, x, y)
        assert img.getpixel((x * 8, y * 8)) == (0, 0, 0)          # corners between studs
        assert img.getpixel((x * 8 + 7, y * 8 + 7)) == (0, 0, 0)


def test_preview_square(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out, style="square")
    img = Image.open(out).convert("RGB")
    for (x, y) in SAMPLES:
        rgb = _rgb(layout, x, y)
        assert img.getpixel((x * 8, y * 8)) == rgb
        assert img.getpixel((x * 8 + 7, y * 8 + 7)) == rgb


def test_preview_background(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out, background=(233, 233, 233))
    assert Image.open(out).convert("RGB").getpixel((0, 0)) == (233, 233, 233)


def test_stud_coverage_is_a_disc():
    a = stud_coverage(10)
    assert a.shape == (10, 10)
    assert a[4:6, 4:6].min() == 1.0 and a[0, 0] == 0.0
    assert a.sum() == pytest.approx(3.14159 * (0.45 * 10) ** 2, rel=0.02)


def test_preview_unknown_style(tmp_path):
    with pytest.raises(ValueError, match="style"):
        write_preview(load_official_design().to_layout(), tmp_path / "p.png", style="hex")


def test_preview_scale(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out, scale=1)
    assert Image.open(out).size == (128, 80)
