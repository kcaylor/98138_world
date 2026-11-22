"""Preview PNG (FR-024): 8x8 px per stud, cited RGB."""

from PIL import Image

from lego_image_processor.kit import load_kit_color_table, load_official_design
from lego_image_processor.maps.preview import write_preview


def test_preview_size_and_colors(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out)
    img = Image.open(out).convert("RGB")
    assert img.size == (1024, 640)
    table = load_kit_color_table()
    for (x, y) in ((0, 0), (40, 20), (127, 79), (64, 40)):
        key = layout.get_position(x, y).color_id
        rgb = tuple(table.by_key(key).rgb)
        assert img.getpixel((x * 8, y * 8)) == rgb
        assert img.getpixel((x * 8 + 7, y * 8 + 7)) == rgb


def test_preview_scale(tmp_path):
    layout = load_official_design().to_layout()
    out = tmp_path / "p.png"
    write_preview(layout, out, scale=1)
    assert Image.open(out).size == (128, 80)
