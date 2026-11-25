"""`template` commands (feature 016; contracts/cli.md): list, show and locate map templates.

Read-only and offline. The kit template ``kit-31203`` is the reference; other templates are the
package files in ``data/templates/`` and can be built on only once the project owner confirms them.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
from typing import Optional, Tuple

import click

from ..kit.source import DISCLAIMER
from ..templates import Template, TemplateError, list_templates, load_template
from .map import CommandError, _table

_STATUS_TEXT = {"reference": "reference (the kit 31203 grid; always buildable)",
                "confirmed": "confirmed: maps can be built on it",
                "unconfirmed": "unconfirmed: not confirmed by the project owner; maps cannot be built on it"}


def _load(template_id: str) -> Template:
    try:
        return load_template(template_id)
    except TemplateError as exc:
        raise CommandError(str(exc), 1)


def _all() -> Tuple[Template, ...]:
    try:
        return list_templates()
    except TemplateError as exc:
        raise CommandError(str(exc), 1)


def _json(doc) -> None:
    click.echo(json.dumps(dict(doc, disclaimer=DISCLAIMER), indent=2, ensure_ascii=False))


@click.group("template")
def template_group() -> None:
    """Map templates: the kit grid and the curved maps on the kit board (works offline)."""


@template_group.command("list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
def list_cmd(output_format: str) -> None:
    """List every template with its status, stud counts and arrangements."""
    templates = _all()
    if output_format == "json":
        _json({"templates": [{"id": t.id, "title": t.title, "status": t.status, "counts": t.counts,
                              "arrangements": list(t.arrangements)} for t in templates]})
        return
    rows = []
    for t in templates:
        c = t.counts
        rows.append((t.id, t.title, t.status, f"{c['land']:,}", f"{c['ocean']:,}", f"{c['margin']:,}",
                     " ".join(t.arrangements)))
    for line in _table(["id", "title", "status", "land", "ocean", "margin", "arrangements"], rows):
        click.echo(line)
    click.echo()
    click.echo("Maps can be built on the reference template and on confirmed templates.")
    click.echo(DISCLAIMER)


def _projection_lines(t: Template):
    p = t.projection
    fit = p["fit"]
    if t.is_kit:
        yield (f"Projection: {p['name']}, fitted to the kit's land/sea mask: left edge {fit['left_edge_lon']:g}°, "
               f"{fit['deg_per_col']:g}° per column, equator at row {fit['equator_row']:g}, "
               f"{fit['rows_per_radian']:g} rows per radian")
    else:
        lon0 = p["lon_0"]
        meridian = f"{abs(lon0):g}° {'E' if lon0 >= 0 else 'W'}"
        yield (f"Projection: {p['name']}, {p['proj']} (standard parallel {p['lat_1']:g}°, central meridian "
               f"{meridian})")
        x0, x1, y0, y1 = fit["extent"]
        yield (f"Fit: {fit['mode']}, {fit['scale']:.4f} studs per projected unit, extent x {x0:.4f}..{x1:.4f}, "
               f"y {y0:.4f}..{y1:.4f}")
    yield f"Citation: {p['citation']}"


@template_group.command("show")
@click.argument("template_id", metavar="ID")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
def show_cmd(template_id: str, output_format: str) -> None:
    """Show a template: projection, board, parts, counts, source and confirmation."""
    t = _load(template_id)
    if output_format == "json":
        _json(t.summary())
        return
    b, c = t.board, t.counts
    m = c["modules"]
    click.echo(f"Template: {t.id} - {t.title}")
    click.echo(f"Status: {_STATUS_TEXT[t.status]}")
    click.echo(f"Description: {t.description}")
    for line in _projection_lines(t):
        click.echo(line)
    click.echo(f"Board: {b['modules'][0]} x {b['modules'][1]} modules of {b['module']} x {b['module']} studs "
               f"({b['width']} x {b['height']}), pitch {b['pitch_mm']:.1f} mm")
    click.echo("Parts: " + ", ".join(f"{k} {v}" for k, v in t.parts.items()))
    click.echo(f"Frame: kit {t.frame['kit']}, arrangements {', '.join(t.arrangements)}")
    click.echo(f"Studs: {c['land']:,} land, {c['ocean']:,} ocean, {c['margin']:,} margin "
               f"(outline ring {c['ring']:,})")
    click.echo(f"Modules: {m['full']} full, {m['partial']} partial, {m['empty']} empty")
    if c["margin"]:
        click.echo("Corners (largest block inside the ring): " + "; ".join(
            f"{name} {k['width']} x {k['height']} at row {k['row']}, column {k['col']}"
            for name, k in c["corners"].items()))
    else:
        click.echo("Corners: none (no margin)")
    if t.dataset is None:
        click.echo("Source: built in code from " + ", ".join(t.source.get("files", [])))
    else:
        d = t.dataset
        click.echo(f"Source dataset: {d.id} (version {d.version}), {d.title}; {d.license}; {d.citation}")
        click.echo(f"Source file: {t.path.name} (SHA-256 {t.file_sha256})")
    click.echo(f"Layout SHA-256: {t.layout_sha256}")
    click.echo(f"Corrections: {len(t.corrections)}")
    if t.is_kit:
        click.echo("Confirmation: not needed (the kit is the reference)")
    elif t.confirmation is None:
        click.echo("Confirmation: none (not confirmed by the project owner)")
    else:
        click.echo(f"Confirmation: {t.confirmation.role}, {t.confirmation.date}")
    click.echo(DISCLAIMER)


def _stud_text(t: Template, row: int, col: int) -> str:
    cls = t.class_at(row, col)
    return f"row {row}, column {col}, section {t.section_label(row, col)}, {cls} (part {t.part_at(row, col)})"


@template_group.command("locate", context_settings={"ignore_unknown_options": True})
@click.argument("template_id", metavar="ID")
@click.argument("coords", nargs=-1, type=float, metavar="[LAT LON]")
@click.option("--stud", nargs=2, type=int, metavar="ROW COL",
              help="Give the location of this stud instead (row 0-79 from the top, column 0-127 from the left).")
def locate_cmd(template_id: str, coords: Tuple[float, ...], stud: Optional[Tuple[int, int]]) -> None:
    """The stud that contains a location (LAT LON, degrees; negative south and west), or the
    location of a stud (--stud ROW COL)."""
    if stud is not None and coords:
        raise click.UsageError("give LAT LON or --stud ROW COL, not both")
    if stud is None and len(coords) != 2:
        raise click.UsageError("give LAT LON (two numbers) or --stud ROW COL")
    if stud is None:
        lat, lon = coords
        if not -90 <= lat <= 90:
            raise click.UsageError(f"latitude {lat:g} is outside -90..90")
        if not -180 <= lon <= 180:
            raise click.UsageError(f"longitude {lon:g} is outside -180..180")
    t = _load(template_id)
    click.echo(f"Template: {t.id} - {t.title}")
    if stud is None:
        click.echo(f"Location: lat {lat:.4f}, lon {lon:.4f}")
        hit = t.stud_at(lat, lon)
        if hit is not None:
            click.echo(f"Stud: {_stud_text(t, *hit)}")
        elif t.is_kit:
            click.echo("Stud: outside the kit grid (its rows end short of the South Pole)")
        else:
            click.echo("Stud: off the globe (margin)")
    else:
        row, col = stud
        if not (0 <= row < t.height and 0 <= col < t.width):
            raise click.UsageError(f"stud ({row}, {col}) is outside the board: rows 0-{t.height - 1}, "
                                   f"columns 0-{t.width - 1}")
        click.echo(f"Stud: {_stud_text(t, row, col)}")
        loc = t.location(row, col)
        if loc is None:
            click.echo("Location: none, off the globe (margin)")
        else:
            click.echo(f"Location: lat {loc[0]:.4f}, lon {loc[1]:.4f}")
    click.echo(DISCLAIMER)
