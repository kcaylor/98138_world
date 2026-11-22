"""Build sheets (feature 006): printable section-by-section pages with per-section counts.

An overview page, legend pages and one page per section base (40, A1 ... H5) at true scale, as a
PDF (ReportLab) or SVG pages, plus per-section counts as JSON. Lot numbers, names and IDs come
from the 005 parts list. Pages are drawn from layout data with basic shapes and text only. No
function here uses the network.
Not affiliated with or endorsed by The LEGO Group.
"""

from .compose import PITCH, PRINT_NOTE, SheetError, SheetSet, build_sheet_set
from .counts import SectionCount, SectionCounts, section_counts
from .legend import LegendEntry, build_legend, lot_numbers, text_color
from .model import PAPERS, Page, PageSize, paper_size
from .render_pdf import render_pdf
from .render_svg import render_svg
from .sections import Section, parse_section_labels, section_for, sections

__all__ = [
    "sections", "Section", "section_for", "parse_section_labels",
    "build_legend", "LegendEntry", "lot_numbers", "text_color",
    "section_counts", "SectionCounts", "SectionCount",
    "build_sheet_set", "SheetSet", "SheetError", "PITCH", "PRINT_NOTE",
    "PAPERS", "Page", "PageSize", "paper_size",
    "render_pdf", "render_svg",
]
