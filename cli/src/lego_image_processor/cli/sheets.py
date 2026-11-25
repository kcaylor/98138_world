"""`sheets` commands: printable build sheets and per-section counts for a layout (feature 006).

Exit codes: 0 ok; 1 input error (layout, section label, non-Latin-1 title for PDF, output path);
2 usage. Works offline. Pages are drawn from the layout data only (no LEGO artwork).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from ..kit.source import DISCLAIMER
from ..parts import LayoutInputError, read_layout
from ..sheets import SheetError, build_sheet_set, render_pdf, render_svg, section_counts
from ..sheets.legend import PART_LABEL
from ..sheets.model import is_latin1
from .map import CommandError

_PAGE_SVG = re.compile(r"page-\d+\.svg")
PRINT_LINE = "Print at 100% (no fit-to-page); check the 100 mm scale bar."


def _read(layout_path: Path):
    try:
        return read_layout(layout_path)
    except LayoutInputError as exc:
        raise CommandError(str(exc), 1)


@click.group("sheets")
def sheets() -> None:
    """Printable build sheets: overview, legend, one page per section base and an assembly page
    (how to hang the frames), with per-section counts (works offline)."""


@sheets.command("build")
@click.argument("layout_path", metavar="LAYOUT", type=click.Path(path_type=Path))
@click.option("-o", "--output", required=True, type=click.Path(path_type=Path),
              help="PDF file (--format pdf) or directory for page-NN.svg files (--format svg; "
                   "created if missing)")
@click.option("--format", "output_format", type=click.Choice(["pdf", "svg"]), default="pdf",
              show_default=True)
@click.option("--paper", type=click.Choice(["letter", "a4"], case_sensitive=False),
              default="letter", show_default=True, help="Paper size; grids stay at true scale")
@click.option("--sections", "section_list", metavar="LIST",
              help="Comma-separated section labels to print, e.g. B2,C2 (default: all 40, A1-H5)")
@click.option("--title", help="Overview title (default: recipe title, else the layout file name)")
@click.option("-q", "--quiet", is_flag=True, help="No human output (errors still go to stderr)")
def build_cmd(layout_path, output, output_format, paper, section_list, title, quiet):
    """Write build sheets for a full 128 x 80 layout as a PDF or SVG pages."""
    if output_format == "pdf":
        if output.is_dir():
            raise CommandError(f"output {output} is a directory; give a PDF file path", 1)
        if not output.parent.is_dir():
            raise CommandError(f"output directory {output.parent} does not exist", 1)
        if title is not None and not is_latin1(title):
            raise CommandError("--title must be Latin-1 text for PDF output (standard Helvetica "
                               "font); use --format svg for other characters", 1)
    elif output.exists() and not output.is_dir():
        raise CommandError(f"output {output} is not a directory (--format svg writes one file "
                           "per page into a directory)", 1)
    layout = _read(layout_path)
    try:
        sheet_set = build_sheet_set(layout, paper=paper.lower(), sections=section_list, title=title)
        payload = render_pdf(sheet_set) if output_format == "pdf" else render_svg(sheet_set)
    except (SheetError, ValueError) as exc:
        raise CommandError(str(exc), 1)
    if output_format == "pdf":
        output.write_bytes(payload)
    else:
        output.mkdir(parents=True, exist_ok=True)
        # Remove page files left by an earlier, longer build; only our own page-NN.svg names.
        keep = {name for name, _ in payload}
        for stale in output.glob("page-*.svg"):
            if stale.name not in keep and _PAGE_SVG.fullmatch(stale.name) and stale.is_file():
                stale.unlink()
        for name, text in payload:
            (output / name).write_text(text, encoding="utf-8", newline="\n")
    if quiet:
        return
    kinds = sheet_set.page_kinds
    pl = sheet_set.parts_list
    t = pl.totals()
    where = output if output_format == "pdf" else f"{output}/page-01.svg ... page-{len(sheet_set.pages):02d}.svg"
    click.echo(f"Build sheets: {sheet_set.title}")
    click.echo(f"Wrote {where}: {len(sheet_set.pages)} pages ({kinds['overview']} overview, "
               f"{kinds['legend']} legend, {kinds['section']} sections, {kinds['assembly']} assembly), "
               f"{sheet_set.paper.label}")
    lots = f"{t['lots']} lots ({t['verified_lots']} verified"
    lots += f", {t['unverified_lots']} unverified: no cited IDs)" if t["unverified_lots"] else ")"
    click.echo(f"Lots: {lots}; {t['needed']:,} pieces")
    from ..layout.arrangement import arrangement_of
    a = arrangement_of(layout.grid)
    click.echo(f"Arrangement: {a.describe()}; sections labelled as hung")
    click.echo(PRINT_LINE)
    click.echo("Drawn from the layout data only; no LEGO artwork or instruction images.")
    click.echo(DISCLAIMER)


@sheets.command("counts")
@click.argument("layout_path", metavar="LAYOUT", type=click.Path(path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path),
              help="Write the counts as JSON (implies --format json)")
@click.option("-q", "--quiet", is_flag=True, help="No human output (errors still go to stderr)")
def counts_cmd(layout_path, output_format, output, quiet):
    """Pieces per section (A1-H5) and lot, as a table or JSON."""
    layout = _read(layout_path)
    sc = section_counts(layout)
    if output is not None:
        if not output.parent.is_dir():
            raise CommandError(f"output directory {output.parent} does not exist", 1)
        output.write_text(sc.to_json(), encoding="utf-8", newline="\n")
        if not quiet:
            click.echo(f"Wrote section counts {output}: {len(sc.sections)} sections, "
                       f"{len(sc.legend)} lots")
            click.echo(DISCLAIMER)
        return
    if output_format == "json":
        click.echo(sc.to_json(), nl=False)
        return
    if quiet:
        return
    click.echo(f"Section counts for {layout.path} (lot numbers as in the build sheets)")
    if sc.arrangement != "A":
        click.echo(f"Arrangement {sc.arrangement}: sections labelled as hung; kit section in brackets")
    for s in sc.sections:
        sec = s.section
        pairs = " ".join(f"#{k}:{v}" for k, v in s.counts.items())
        kit = f" [{sec.kit_label}]" if sec.kit_label != sec.label else ""
        click.echo(f"{sec.label}{kit}  x {sec.x_range[0]}-{sec.x_range[1]}  y {sec.y_range[0]}-"
                   f"{sec.y_range[1]}  frame {sec.frame}  {pairs}  total {s.total}")
    click.echo()
    click.echo("Legend")
    for e in sc.legend:
        ids = "" if e.verified else " (no cited IDs)"
        click.echo(f"#{e.number}  {PART_LABEL[e.lot.part_type]}  {e.name} ({e.lot.color_key}){ids}"
                   f"  {e.lot.needed:,}")
    click.echo(DISCLAIMER)
