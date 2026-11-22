"""Section finding and (col,row) mapping over image placements (pure; factual fixture)."""

import json
from pathlib import Path

import pytest

from kit31203 import sections

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "kit31203"

PAGES_BY_COLUMN = [
    [22, 24, 26, 28, 30], [36, 38, 40, 42, 44], [52, 54, 56, 58, 60], [66, 68, 70, 72, 74],
    [80, 82, 84, 86, 88], [94, 96, 98, 100, 102], [110, 112, 114, 116, 118],
    [124, 126, 128, 130, 132],
]


def _load(kind):
    data = json.loads((FIXTURES / "placements.json").read_text())[kind]
    return {
        int(page): [sections.Placement(page=int(page), **p) for p in rows]
        for page, rows in data.items()
    }


@pytest.fixture
def measured():
    return _load("measured")


@pytest.fixture
def synthetic():
    return _load("synthetic")


def test_pinned_pages_match_spec():
    assert list(sections.SECTION_PAGES) == [p for col in PAGES_BY_COLUMN for p in col]


class TestGeometry:
    def test_column_origins_from_the_three_panels(self, measured):
        geo = sections.grid_geometry(measured[22])
        research = [13.9, 50.2, 90.6, 127.2, 163.8, 200.4, 240.2, 276.6]
        assert len(geo.col_origins) == 8
        for got, want in zip(geo.col_origins, research):
            assert got == pytest.approx(want, abs=0.6)
        assert len(geo.row_origins) == 5
        assert geo.row_origins[0] == pytest.approx(493.5, abs=0.7)
        assert geo.row_origins[0] > geo.row_origins[4]

    def test_wrong_panel_set_fails(self, measured):
        panels_missing = [p for p in measured[22] if p.width != 306]
        with pytest.raises(sections.PlacementError) as exc:
            sections.grid_geometry(panels_missing)
        assert exc.value.exit_code == 6
        assert "22" in str(exc.value)


class TestMeasuredPages:
    @pytest.mark.parametrize("page,slot,size", [
        (22, (0, 0), (154, 154)), (26, (0, 2), (154, 153)),
        (66, (3, 0), (154, 154)), (132, (7, 4), (154, 154)),
    ])
    def test_slot_from_placement(self, measured, page, slot, size):
        found = sections.find_section_images(measured, pages=[page])
        assert set(found) == {page}
        assert (found[page].width, found[page].height) == size
        assert sections.slot_from_placement(found[page], sections.grid_geometry(measured[page])) == slot
        assert sections.page_order_slot(page) == slot


class TestAllSections:
    def test_placement_equals_page_order_for_all_40(self, synthetic):
        result = sections.map_sections(synthetic)
        assert len(result) == 40
        assert len({(s["col"], s["row"]) for s in result}) == 40
        assert sorted(s["page"] for s in result) == sorted(sections.SECTION_PAGES)
        for s in result:
            assert s["order_check"] is True
            assert s["page"] == PAGES_BY_COLUMN[s["col"]][s["row"]]
            assert s["image_size"] == ([154, 153] if s["row"] == 2 else [154, 154])
            assert set(s["placement"]) == {"x", "y", "scale"}
        assert [(s["col"], s["row"]) for s in result] == sorted((s["col"], s["row"]) for s in result)

    def test_page_without_section_image_fails(self, synthetic):
        synthetic[40] = [p for p in synthetic[40] if p.width != 154 or p.height not in (153, 154)]
        with pytest.raises(sections.SectionsError) as exc:
            sections.map_sections(synthetic)
        assert exc.value.exit_code == 5
        assert "40" in str(exc.value)

    def test_page_with_two_section_images_fails(self, synthetic):
        extra = [p for p in synthetic[54] if (p.width, p.height) == (154, 154)][0]
        synthetic[54].append(extra._replace(x=extra.x + 40))
        with pytest.raises(sections.SectionsError) as exc:
            sections.map_sections(synthetic)
        assert exc.value.exit_code == 5
        assert "54" in str(exc.value)

    def test_missing_pinned_page_fails(self, synthetic):
        del synthetic[88]
        del synthetic[130]
        with pytest.raises(sections.SectionsError) as exc:
            sections.map_sections(synthetic)
        assert exc.value.exit_code == 5
        assert "88" in str(exc.value) and "130" in str(exc.value)

    def test_placement_off_slot_fails(self, synthetic):
        i, sec = next((i, p) for i, p in enumerate(synthetic[24]) if p.width == 154 and p.height == 154)
        synthetic[24][i] = sec._replace(x=sec.x + 18.0)
        with pytest.raises(sections.PlacementError) as exc:
            sections.map_sections(synthetic)
        assert exc.value.exit_code == 6
        assert "24" in str(exc.value)

    def test_placement_disagreeing_with_page_order_fails(self, synthetic):
        # swap the section images of pages 36 (col 1,row 0) and 52 (col 2,row 0)
        def split(page):
            sec = [p for p in synthetic[page] if (p.width, p.height) == (154, 154)][0]
            return sec, [p for p in synthetic[page] if p is not sec]
        a, rest_a = split(36)
        b, rest_b = split(52)
        synthetic[36] = rest_a + [b._replace(page=36)]
        synthetic[52] = rest_b + [a._replace(page=52)]
        with pytest.raises(sections.PlacementError) as exc:
            sections.map_sections(synthetic)
        assert exc.value.exit_code == 6
        msg = str(exc.value)
        assert "36" in msg and "(2, 0)" in msg and "(1, 0)" in msg


class TestImageSizes:
    def test_section_sizes_accepted_overview_sizes_excluded(self, synthetic):
        page = synthetic[22]
        sec = [p for p in page if (p.width, p.height) == (154, 154)][0]
        page += [sec._replace(width=247, height=247, scale=118.2),
                 sec._replace(width=132, height=132, scale=63.0)]
        found = sections.find_section_images(synthetic, pages=[22, 26])
        assert (found[22].width, found[22].height) == (154, 154)
        assert (found[26].width, found[26].height) == (154, 153)

    def test_is_section_image(self):
        mk = lambda w, h, s=36.86: sections.Placement(page=1, width=w, height=h, x=0, y=0, scale=s)
        assert sections.is_section_image(mk(154, 154))
        assert sections.is_section_image(mk(154, 153))
        assert not sections.is_section_image(mk(247, 247))
        assert not sections.is_section_image(mk(132, 132))
        assert not sections.is_section_image(mk(154, 381, 73.68))
        assert not sections.is_section_image(mk(154, 154, 120.0))
