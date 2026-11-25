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


# --- Feature 016 (T054; FR-012; research R13): margin squares on template previews -------------
# Main 6038d9c draws every stud as a round on black; template previews use the same drawing, with
# the margin's 1x1 square tiles filling their cells.

import numpy as np  # noqa: E402

from lego_image_processor.maps import preview as preview_mod  # noqa: E402

BG_RECIPE = """
format = "1"
id = "bg-map"
title = "Background"

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "background"
colors = ["lego_medium_azur"]
weights = [1]

[margin]
color = "lego_dark_stone_grey"
ring = "lego_bright_yellow"
"""

BLACK = preview_mod.DEFAULT_BACKGROUND


def _template_layout():
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.recipe import parse_recipe

    return build_map(parse_recipe(BG_RECIPE), template="winkel-tripel").layout


def test_template_preview_rounds_and_squares(tmp_path, confirmed_winkel):
    t = confirmed_winkel
    layout = _template_layout()
    out = tmp_path / "w.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB"))
    assert img.shape == (640, 1024, 3)
    rgb = preview_mod.color_rgb()
    seen = {"land": 0, "ocean": 0, "margin": 0, "ring": 0}
    for p in layout.positions:
        if (p.x + 3 * p.y) % 7:  # a spread of studs
            continue
        color = rgb[(p.lego_part_id, p.color_id)]
        centre = tuple(img[p.y * 8 + 4, p.x * 8 + 4])
        corner = tuple(img[p.y * 8, p.x * 8])
        assert centre == color
        if p.part_type == "square_tile":  # a full square
            assert corner == color and tuple(img[p.y * 8 + 7, p.x * 8 + 7]) == color
            seen["ring" if t.ring[p.y, p.x] else "margin"] += 1
        else:  # a round on black, as on the kit
            assert corner == BLACK and tuple(img[p.y * 8 + 7, p.x * 8 + 7]) == BLACK
            seen[t.class_at(p.y, p.x)] += 1
    assert all(seen.values())


def test_template_rounds_are_the_kit_rounds(tmp_path, confirmed_winkel):
    """One drawing for every round stud: a template land cell equals the kit's round of that color."""
    layout = _template_layout()
    out = tmp_path / "w.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB")).astype(float)
    p = next(q for q in layout.positions if q.part_type == "plate")
    color = np.array(preview_mod.color_rgb()[("6141", p.color_id)], dtype=float)
    a = preview_mod.stud_coverage(8)[..., None]
    expected = np.rint(color * a + np.array(BLACK, dtype=float) * (1.0 - a))
    assert (img[p.y * 8:p.y * 8 + 8, p.x * 8:p.x * 8 + 8] == expected).all()
    edge = img[p.y * 8 + 4, p.x * 8]  # the left edge of the round, part covered: anti-aliased
    black = np.array(BLACK, dtype=float)
    assert (np.minimum(black, color) <= edge).all() and (edge <= np.maximum(black, color)).all()
    assert not (edge == black).all() and not (edge == color).all()


def test_template_preview_square_style_and_background(tmp_path, confirmed_winkel):
    layout = _template_layout()
    rgb = preview_mod.color_rgb()
    out = tmp_path / "s.png"
    write_preview(layout, out, style="square")
    img = np.asarray(Image.open(out).convert("RGB"))
    for p in layout.positions[::89]:
        color = rgb[(p.lego_part_id, p.color_id)]
        assert tuple(img[p.y * 8, p.x * 8]) == color and tuple(img[p.y * 8 + 7, p.x * 8 + 7]) == color
    out = tmp_path / "g.png"
    write_preview(layout, out, background=(233, 233, 233))
    img = np.asarray(Image.open(out).convert("RGB"))
    p = next(q for q in layout.positions if q.part_type == "tile")
    m = next(q for q in layout.positions if q.part_type == "square_tile")
    assert tuple(img[p.y * 8, p.x * 8]) == (233, 233, 233)
    assert tuple(img[m.y * 8, m.x * 8]) == rgb[(m.lego_part_id, m.color_id)]


def test_template_preview_scale_one(tmp_path, confirmed_winkel):
    out = tmp_path / "w.png"
    write_preview(_template_layout(), out, scale=1)
    assert Image.open(out).size == (128, 80)


def test_kit_preview_is_rounds_on_black(tmp_path):
    """Kit previews are main's (6038d9c): every stud a round on black, no square tiles (SC-001)."""
    layout = load_official_design().to_layout()
    assert not any(p.part_type == "square_tile" for p in layout.positions)
    out = tmp_path / "k.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB"))
    table = load_kit_color_table()
    for p in layout.positions[::97]:
        rgb = tuple(table.by_key(p.color_id).rgb)
        assert tuple(img[p.y * 8, p.x * 8]) == BLACK and tuple(img[p.y * 8 + 4, p.x * 8 + 4]) == rgb


# --- Feature 016 (owner, 2026-11-24; research R13 note): Black margin studs blend into the
# preview's background. Margin studs whose color is LEGO Black are drawn in the background color
# (pure black by default, as main 6038d9c draws the gaps between rounds); other margin colors and
# the outline ring keep their cited colors. Parts lists, exports, sheets and cells.json still use
# LEGO Black's cited color.

CITED_BLACK = (5, 19, 29)


def _margin_layout(margin: str):
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.recipe import parse_recipe

    text = BG_RECIPE.split("[margin]")[0] + "[margin]\n" + margin
    return build_map(parse_recipe(text), template="winkel-tripel").layout


def _cells(img, p):
    return img[p.y * 8:p.y * 8 + 8, p.x * 8:p.x * 8 + 8].reshape(-1, 3)


def test_black_margin_blends_into_the_background(tmp_path, confirmed_winkel):
    layout = _margin_layout('color = "lego_black"\n')
    margin = [p for p in layout.positions if p.part_type == "square_tile"]
    assert margin and all(p.color_id == "lego_black" for p in margin)
    assert preview_mod.color_rgb()[("3070b", "lego_black")] == CITED_BLACK
    for kwargs, bg in (({}, BLACK), ({"background": (233, 233, 233)}, (233, 233, 233)),
                       ({"style": "square"}, BLACK)):
        out = tmp_path / "b.png"
        write_preview(layout, out, **kwargs)
        img = np.asarray(Image.open(out).convert("RGB"))
        for p in margin[::37]:
            assert (_cells(img, p) == bg).all(), (kwargs, p.x, p.y)
        # land and ocean keep their cited colors at the stud centre
        p = next(q for q in layout.positions if q.part_type == "plate")
        assert tuple(img[p.y * 8 + 4, p.x * 8 + 4]) == preview_mod.color_rgb()[("6141", p.color_id)]


def test_black_margin_with_a_ring(tmp_path, confirmed_winkel):
    t = confirmed_winkel
    layout = _margin_layout('color = "lego_black"\nring = "lego_bright_yellow"\n')
    yellow = preview_mod.color_rgb()[("3070b", "lego_bright_yellow")]
    out = tmp_path / "r.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB"))
    seen = {"ring": 0, "margin": 0}
    for p in layout.positions:
        if p.part_type != "square_tile":
            continue
        if t.ring[p.y, p.x]:
            assert (_cells(img, p) == yellow).all()
            seen["ring"] += 1
        else:
            assert (_cells(img, p) == BLACK).all()
            seen["margin"] += 1
    assert seen == {"ring": 288, "margin": 1996 - 288}


def test_black_ring_keeps_its_cited_color(tmp_path, confirmed_winkel):
    t = confirmed_winkel
    layout = _margin_layout('color = "lego_white"\nring = "lego_black"\n')
    white = preview_mod.color_rgb()[("3070b", "lego_white")]
    out = tmp_path / "w.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB"))
    for p in layout.positions:
        if p.part_type == "square_tile":
            assert (_cells(img, p) == (CITED_BLACK if t.ring[p.y, p.x] else white)).all()


def test_black_margin_layout_and_parts_keep_cited_black(confirmed_winkel):
    """Only the preview drawing changes: the layout and parts list name LEGO Black on 3070b."""
    from lego_image_processor.parts.partslist import build_parts_list

    layout = _margin_layout('color = "lego_black"\n')
    pl = build_parts_list(layout)
    lots = [lot for lot in pl.lots if lot.part_id == "3070b"]
    assert [(lot.color_key, lot.needed) for lot in lots] == [("lego_black", 1996)]


# --- Feature 017 (T067; FR-024; research R15; contracts/in-margin-plaque.md "Preview"): the
# in-margin plaque is one filled rectangle in the tile's cited Black over its 6 x 6 studs (in the
# round style 6 pitches minus the gap between studs, as a round stud leaves; edge to edge in the
# square style). A layout may lack exactly the plaque's studs and no other position.

PLAQUE_STUDS = (73, 1)  # bottom-left: rows 73-78, columns 1-6


def _plaque_rgb():
    from lego_image_processor.kit.plaque_parts import load_plaque_parts
    tile = load_plaque_parts().plaques["small"].tile
    return tuple(tile.color.rgb)


def _plaque_layout(margin='color = "lego_dark_stone_grey"\n', corner="bottom-left"):
    return _margin_layout(margin + f'plaque = "{corner}"\n')


def test_plaque_is_one_black_rectangle(tmp_path, confirmed_winkel):
    layout = _plaque_layout()
    black = _plaque_rgb()
    grey = preview_mod.color_rgb()[("3070b", "lego_dark_stone_grey")]
    assert black == CITED_BLACK
    out = tmp_path / "p.png"
    write_preview(layout, out)
    img = np.asarray(Image.open(out).convert("RGB"))
    r0, c0 = PLAQUE_STUDS
    for y in range(r0, r0 + 6):
        for x in range(c0, c0 + 6):
            assert tuple(img[y * 8 + 4, x * 8 + 4]) == black  # on a stud
    for (y, x) in ((r0 + 1, c0 + 1), (r0 + 3, c0 + 4), (r0 + 4, c0 + 2)):  # inner studs
        assert tuple(img[y * 8, x * 8]) == black            # between studs: no gap inside the tile
        assert tuple(img[y * 8 + 7, x * 8 + 7]) == black
    top, left, bottom, right = r0 * 8, c0 * 8, (r0 + 6) * 8 - 1, (c0 + 6) * 8 - 1
    assert tuple(img[top + 1, left + 1]) == black and tuple(img[bottom - 1, right - 1]) == black
    # just outside: the neighbouring margin square tiles, edge to edge
    for (py, px) in ((top - 1, left + 20), (bottom + 1, left + 20), (top + 20, left - 1), (top + 20, right + 1)):
        assert tuple(img[py, px]) == grey
    # the outermost pixel ring is part covered (the gap a round stud leaves), so neither colour
    edge = tuple(img[top + 20, left])
    assert edge != black and edge != grey


def test_plaque_in_the_square_style_fills_its_cells(tmp_path, confirmed_winkel):
    layout = _plaque_layout()
    black = _plaque_rgb()
    out = tmp_path / "s.png"
    write_preview(layout, out, style="square")
    img = np.asarray(Image.open(out).convert("RGB"))
    r0, c0 = PLAQUE_STUDS
    assert (img[r0 * 8:(r0 + 6) * 8, c0 * 8:(c0 + 6) * 8] == black).all()
    grey = preview_mod.color_rgb()[("3070b", "lego_dark_stone_grey")]
    assert tuple(img[r0 * 8 - 1, c0 * 8]) == grey and tuple(img[r0 * 8, c0 * 8 - 1]) == grey


def test_plaque_on_a_black_margin_and_a_light_background(tmp_path, confirmed_winkel):
    """A Black margin blends into the background (016); the plaque keeps the tile's cited Black."""
    layout = _plaque_layout('color = "lego_black"\n')
    out = tmp_path / "b.png"
    write_preview(layout, out, background=(233, 233, 233))
    img = np.asarray(Image.open(out).convert("RGB"))
    r0, c0 = PLAQUE_STUDS
    assert tuple(img[(r0 + 2) * 8, (c0 + 2) * 8]) == _plaque_rgb()
    assert tuple(img[(r0 + 2) * 8, c0 * 8 - 1]) == (233, 233, 233)


@pytest.mark.parametrize("corner", ["top-left", "top-right", "bottom-right"])
def test_plaque_in_every_corner(tmp_path, confirmed_winkel, corner):
    layout = _plaque_layout(corner=corner)
    s = layout.plaque["studs"]
    out = tmp_path / "c.png"
    write_preview(layout, out, scale=1, style="square")
    img = np.asarray(Image.open(out).convert("RGB"))
    assert (img[s["row"]:s["row"] + 6, s["col"]:s["col"] + 6] == _plaque_rgb()).all()


def test_preview_without_a_plaque_is_unchanged(tmp_path, confirmed_winkel):
    """The same layout built without the plaque draws the margin there, as 016 does."""
    plain = _margin_layout('color = "lego_dark_stone_grey"\n')
    with_plaque = _plaque_layout()
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    write_preview(plain, a)
    write_preview(with_plaque, b)
    ia = np.asarray(Image.open(a).convert("RGB"))
    ib = np.asarray(Image.open(b).convert("RGB"))
    r0, c0 = PLAQUE_STUDS
    outside = np.ones(ia.shape[:2], dtype=bool)
    outside[r0 * 8:(r0 + 6) * 8, c0 * 8:(c0 + 6) * 8] = False
    assert (ia[outside] == ib[outside]).all()
    assert tuple(ia[(r0 + 2) * 8, (c0 + 2) * 8]) == preview_mod.color_rgb()[("3070b", "lego_dark_stone_grey")]


def _regrid(layout, positions, plaque="same"):
    from lego_image_processor.layout.grid import PositionPlacementGrid
    return PositionPlacementGrid(width=layout.width, height=layout.height, positions=positions,
                                 source_image=layout.source_image, generated_at=layout.generated_at,
                                 map_metadata=layout.map_metadata, template=layout.template,
                                 plaque=layout.plaque if plaque == "same" else plaque)


def test_a_layout_may_lack_only_the_plaque_studs(tmp_path, confirmed_winkel):
    layout = _plaque_layout()
    gone = layout.positions[500]
    with pytest.raises(ValueError, match=f"no piece at column {gone.x}, row {gone.y}"):
        write_preview(_regrid(layout, [p for p in layout.positions if p is not gone]), tmp_path / "x.png")
    plain = _margin_layout('color = "lego_dark_stone_grey"\n')
    with pytest.raises(ValueError, match="under the plaque"):
        write_preview(_regrid(plain, plain.positions, plaque=layout.plaque), tmp_path / "y.png")
    with pytest.raises(ValueError, match="no piece"):
        write_preview(_regrid(plain, plain.positions[1:]), tmp_path / "z.png")
