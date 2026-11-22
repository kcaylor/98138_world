"""Find the 40 section images and map each to its board position (col, row). Pure functions.

Input is a list of image placements per page (``Placement`` or the adapter's ``ImagePlacement``,
which has the same fields). Coordinates are PDF points, origin bottom left, y up (research R4, R5).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, NamedTuple, Sequence, Tuple

from lego_image_processor.kit.design import SECTION_PAGES  # noqa: F401  (re-exported)

SECTION_SIZES = frozenset({(154, 154), (154, 153)})
SECTION_SCALE_RANGE = (30.0, 45.0)  # drawn width in pt (about 36.8)
PANEL_HEIGHT_PX = 381
PANEL_WIDTHS_PX = frozenset({154, 306})
PX_PER_COLUMN = 77  # panel widths: 154 px = 2 columns, 306 px = 4 columns
COLUMNS, ROWS = 8, 5
TOLERANCE_PT = 3.0
ROWS_PER_COLUMN = 5


class SectionsError(Exception):
    """Section images missing or extra on the pinned pages."""

    exit_code = 5


class PlacementError(Exception):
    """Section placement off the grid, or disagreeing with page order, or a slot collision."""

    exit_code = 6


class Placement(NamedTuple):
    page: int
    width: int    # px
    height: int   # px
    x: float      # drawn origin, pt
    y: float
    scale: float  # drawn width, pt
    height_pt: float = 0.0  # drawn height, pt


class Geometry(NamedTuple):
    col_origins: List[float]  # x of each column's left edge, left to right
    row_origins: List[float]  # y of each row's bottom edge, row 0 (top) first


def is_section_image(p) -> bool:
    lo, hi = SECTION_SCALE_RANGE
    return (p.width, p.height) in SECTION_SIZES and lo <= p.scale <= hi


def find_section_images(placements_by_page: Mapping[int, Sequence],
                        pages: Iterable[int] = SECTION_PAGES) -> Dict[int, object]:
    """Exactly one section image on each page; otherwise SectionsError naming every bad page."""
    pages = list(pages)
    missing = [p for p in pages if p not in placements_by_page]
    found, none, several = {}, [], []
    for page in pages:
        if page in missing:
            continue
        hits = [p for p in placements_by_page[page] if is_section_image(p)]
        if not hits:
            none.append(page)
        elif len(hits) > 1:
            several.append(page)
        else:
            found[page] = hits[0]
    problems = []
    if missing:
        problems.append(f"pages missing from the PDF: {missing}")
    if none:
        problems.append(f"no section image (154x154 or 154x153) on pages {none}")
    if several:
        problems.append(f"more than one section image on pages {several}")
    if problems:
        raise SectionsError("; ".join(problems))
    return found


def grid_geometry(placements: Sequence) -> Geometry:
    """Column and row origins from the three grey locator panels drawn on the page."""
    panels = sorted((p for p in placements
                     if p.height == PANEL_HEIGHT_PX and p.width in PANEL_WIDTHS_PX),
                    key=lambda p: p.x)
    page = placements[0].page if placements else "?"
    n_cols = [round(p.width / PX_PER_COLUMN) for p in panels]
    if len(panels) != 3 or sum(n_cols) != COLUMNS:
        raise PlacementError(
            f"page {page}: expected 3 locator panels spanning {COLUMNS} columns, found "
            f"{len(panels)} panels ({[(p.width, p.height) for p in panels]})")
    cols: List[float] = []
    for p, n in zip(panels, n_cols):
        cols += [p.x + k * p.scale / n for k in range(n)]
    ref = panels[0]
    height_pt = ref.height_pt or ref.scale * ref.height / ref.width
    pitch = height_pt / ROWS
    rows = [ref.y + (ROWS - 1 - r) * pitch for r in range(ROWS)]
    return Geometry(col_origins=cols, row_origins=rows)


def _nearest(value: float, origins: Sequence[float]) -> Tuple[int, float]:
    idx = min(range(len(origins)), key=lambda i: abs(origins[i] - value))
    return idx, abs(origins[idx] - value)


def slot_from_placement(p, geometry: Geometry, tolerance: float = TOLERANCE_PT) -> Tuple[int, int]:
    col, dx = _nearest(p.x, geometry.col_origins)
    row, dy = _nearest(p.y, geometry.row_origins)
    if dx > tolerance or dy > tolerance:
        raise PlacementError(
            f"page {p.page}: section image at ({p.x:.1f}, {p.y:.1f}) pt is {max(dx, dy):.1f} pt "
            f"from the nearest grid slot {(col, row)} (limit {tolerance} pt)")
    return col, row


def page_order_slot(page: int, pages: Sequence[int] = SECTION_PAGES) -> Tuple[int, int]:
    """Column-major build order: five pages per column, top to bottom."""
    k = sorted(pages).index(page)
    return k // ROWS_PER_COLUMN, k % ROWS_PER_COLUMN


def map_sections(placements_by_page: Mapping[int, Sequence],
                 pages: Sequence[int] = SECTION_PAGES) -> List[dict]:
    """Section records (data-model.md Section), sorted by (col, row)."""
    found = find_section_images(placements_by_page, pages)
    records, by_slot, errors = [], {}, []
    for page in pages:
        p = found[page]
        slot = slot_from_placement(p, grid_geometry(placements_by_page[page]))
        expected = page_order_slot(page, pages)
        if slot != expected:
            errors.append(f"page {page}: placement gives {slot}, page order gives {expected}")
        if slot in by_slot:
            errors.append(f"pages {by_slot[slot]} and {page} both map to slot {slot}")
        by_slot[slot] = page
        records.append({
            "col": slot[0], "row": slot[1], "page": page, "image_size": [p.width, p.height],
            "placement": {"x": round(p.x, 3), "y": round(p.y, 3), "scale": round(p.scale, 3)},
            "order_check": slot == expected,
        })
    if errors:
        raise PlacementError("; ".join(errors))
    return sorted(records, key=lambda r: (r["col"], r["row"]))
