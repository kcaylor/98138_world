"""`parts` commands: parts list and marketplace files for a layout (feature 005). Works offline.

Exit codes: 0 ok; 1 input error (layout, owned/missing file, output directory); 2 usage;
6 unverified lots in an export without --allow-partial.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import click

from ..kit.inventory import UnsupportedKitError, check_kit_id
from ..kit.source import DISCLAIMER
from ..parts import (ACKNOWLEDGEMENT, BRICKLINK_UPLOAD_NOTE, PRICE_NOTE, LayoutInputError,
                     OwnedFileError, OwnedInputs, PartsList, UnverifiedLotsError, blocking_lots,
                     build_parts_list, owned_parts, parse_owned_csv, parse_percent, read_layout,
                     to_bricklink_xml, to_rebrickable_csv)
from ..parts.owned import percent_text
from ..parts.partslist import (PART_TYPE_TEXT, PLAQUE_PART_TYPE, plaque_lot_text, positions_text,
                               template_text)
from .map import CommandError, _table

NOTHING_TO_BUY = "Nothing to buy: the owned parts cover this layout."


def _spares(ctx, param, value):
    if value is None:
        return parse_percent(0)
    try:
        return parse_percent(value)
    except ValueError as exc:
        raise click.BadParameter(str(exc))


def topup_options(f):
    """Options shared by both `parts` commands (contracts/cli.md)."""
    options = [
        click.option("--kit", "kit_id", default="31203", show_default=True,
                     help="Template kit (only 31203)"),
        click.option("--kits", type=click.IntRange(min=0), default=0, show_default=True,
                     help="Whole 31203 kits owned; their map pieces count as owned"),
        click.option("--owned", "owned_files", multiple=True,
                     type=click.Path(dir_okay=False, path_type=Path),
                     help="Loose parts owned, Rebrickable import CSV (Part,Color,Quantity or "
                          "Element,Quantity); repeatable, quantities add"),
        click.option("--missing", "missing_files", multiple=True,
                     type=click.Path(dir_okay=False, path_type=Path),
                     help="Pieces missing from the owned kits, same format; repeatable; "
                          "subtracted from kit supply (never below 0)"),
        click.option("--spares", default=None, callback=_spares, metavar="PCT",
                     help="Extra pieces per lot with a shortfall: ceil(shortfall x PCT/100), "
                          "0-100 (default 0; no LEGO spare rate is assumed)"),
    ]
    for option in reversed(options):
        f = option(f)
    return f


def _load(layout_path: Path, kit_id: str, kits: int, owned_files: Sequence[Path],
          missing_files: Sequence[Path], spares) -> PartsList:
    try:
        check_kit_id(kit_id)
        layout = read_layout(layout_path)
        # the layout's map parts: a kit layout's CSVs ignore square-tile rows, as before 016 (T110)
        parts = owned_parts(layout.grid)
        owned = OwnedInputs(kits=kits,
                            owned_files=tuple(parse_owned_csv(p, parts=parts) for p in owned_files),
                            missing_files=tuple(parse_owned_csv(p, parts=parts) for p in missing_files),
                            spares_percent=spares)
        return build_parts_list(layout, owned=owned, kit_id=kit_id)
    except (LayoutInputError, OwnedFileError, UnsupportedKitError) as exc:
        raise CommandError(str(exc), 1)


def _describe_inputs(pl: PartsList, echo) -> None:
    lay = pl.layout
    src = lay["map"]["recipe"]["id"] if lay.get("map") else None
    echo(f"Parts list for {lay['path']} ({f'recipe {src}' if src else lay['source_image']}; "
         f"{positions_text(lay, pl.lots)}; map pieces only)")
    o = pl.owned
    parts = [f"{o.kits} kit(s) of {pl.kit_id}"]
    if o.owned_files:
        parts.append("loose parts from " + ", ".join(f.path for f in o.owned_files))
    if o.missing_files:
        parts.append("missing parts from " + ", ".join(f.path for f in o.missing_files))
    if o.ignored_rows:
        parts.append(f"{o.ignored_rows} row(s) for other parts ignored")
    parts.append(f"spares {percent_text(o.spares_percent)}%")
    echo("Owned: " + "; ".join(parts))
    arr = lay.get("arrangement") or {}
    if arr.get("id", "A") != "A":
        echo(f"Arrangement: {arr['id']} ({arr['name']}). {arr['note']}")
    echo_template(lay, echo, pl.lots)


def echo_template(layout_block, echo, lots=()) -> None:
    """The template line of a non-kit layout (feature 016), naming the in-margin plaque's tile when
    ``lots`` hold it (feature 017); nothing for the kit template."""
    t = layout_block.get("template")
    if t:
        echo(template_text(t, lots))


def _lot_rows(pl: PartsList, all_columns: bool) -> List[List[str]]:
    rows = []
    for l in pl.lots:
        if l.verified:
            r = l.ids
            bl = f"{r.bricklink_item_no} / {r.bricklink_color_name} ({r.bricklink_color_id})"
            rb = f"{r.rebrickable_part_num} / {r.rebrickable_color_name} ({r.rebrickable_color_id})"
            lego = f"{r.lego_name} ({r.lego_id})"
            element = r.element_id
        else:
            bl = rb = "unverified"
            lego = f"{l.layout_color_name} ({l.layout_color_code})"
            element = "-"
        row = [PART_TYPE_TEXT[l.part_type], lego, bl, f"{l.needed:,}", f"{l.owned:,}", f"{l.to_buy:,}"]
        if all_columns:
            row += [element, rb, f"{l.kit_supply:,}", f"{l.loose:,}", f"{l.spares:,}", f"{l.surplus:,}"]
        rows.append(row)
    return rows


def echo_parts_list(pl: PartsList, all_columns: bool = False, echo=click.echo) -> None:
    _describe_inputs(pl, echo)
    echo()
    headers = ["part", "color (LEGO id)", "BrickLink item / color (id)", "needed", "owned", "to buy"]
    if all_columns:
        headers += ["element", "Rebrickable part / color (id)", "kit", "loose", "spares", "surplus"]
    for line in _table(headers, _lot_rows(pl, all_columns)):
        echo(line)
    t = pl.totals()
    echo()
    echo(f"Totals: {t['lots']} lots, {t['needed']:,} pieces needed, {t['owned']:,} owned; "
         f"to buy {t['to_buy']:,} pieces in {t['lots_to_buy']} lots"
         + (f" (incl. {t['spares']:,} spares)" if t["spares"] else "")
         + (f"; surplus {t['surplus']:,}" if t["surplus"] else ""))
    if pl.owned.kits:
        echo()
        kits = pl.owned.kits
        echo(f"Left over in the box ({kits} kit{'s' if kits != 1 else ''} of {pl.kit_id}):")
        rows = [[l.part_type, f"{l.lego_name} ({l.lego_id})", f"{l.kit_supply:,}", f"{l.used:,}",
                 f"{l.leftover:,}"] for l in pl.leftovers]
        for line in _table(["part", "color (LEGO id)", "kit", "used", "left over"], rows):
            echo(line)
        echo(f"Left over in the box: {t['leftover']:,} pieces")
    if pl.unverified_lots:
        echo(f"Warning: {len(pl.unverified_lots)} unverified lot(s) have no cited marketplace IDs "
             "and cannot be exported without --allow-partial:")
        for l in pl.unverified_lots:
            echo(f"  {PART_TYPE_TEXT[l.part_type]} {l.part_id} {l.layout_color_name} (code {l.layout_color_code}, "
                 f"key {l.color_key}): {l.reason}; {l.needed:,} needed")
    echo(PRICE_NOTE)
    echo("Sources:")
    for c in pl.citations:
        echo(f"  {c.get('title') or c['id']} <{c['url']}>")
    echo(ACKNOWLEDGEMENT)
    echo(DISCLAIMER)


@click.group("parts")
def parts() -> None:
    """Parts lists with cited LEGO, BrickLink and Rebrickable IDs, kit top-up and marketplace
    files (works offline)."""


@parts.command("list")
@click.argument("layout_path", metavar="LAYOUT", type=click.Path(path_type=Path))
@topup_options
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path),
              help="Write the parts list as JSON (implies --format json)")
@click.option("--all-columns", is_flag=True, help="Also show element, Rebrickable IDs and the arithmetic")
@click.option("-q", "--quiet", is_flag=True, help="No human output (errors still go to stderr)")
def list_cmd(layout_path, kit_id, kits, owned_files, missing_files, spares, output_format, output,
             all_columns, quiet):
    """List the parts a layout needs, what you own and what to buy (map pieces only)."""
    pl = _load(layout_path, kit_id, kits, owned_files, missing_files, spares)
    if output is not None:
        if not output.parent.is_dir():
            raise CommandError(f"output directory {output.parent} does not exist", 1)
        output.write_text(pl.to_json(), encoding="utf-8")
        if not quiet:
            t = pl.totals()
            click.echo(f"Wrote parts list {output}: {t['lots']} lots, {t['to_buy']:,} pieces to buy "
                       f"in {t['lots_to_buy']} lots, {t['unverified_lots']} unverified")
            click.echo(DISCLAIMER)
        return
    if output_format == "json":
        click.echo(pl.to_json(), nl=False)
        return
    if not quiet:
        echo_parts_list(pl, all_columns)


@parts.command("export")
@click.argument("layout_path", metavar="LAYOUT", type=click.Path(path_type=Path))
@click.option("--bricklink", "bricklink_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Write a BrickLink wanted list (XML)")
@click.option("--rebrickable", "rebrickable_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Write a Rebrickable parts CSV (Part,Color,Quantity)")
@click.option("--condition", type=click.Choice(["new", "used"]),
              help="BrickLink CONDITION for every item (omitted by default: any condition)")
@click.option("--allow-partial", is_flag=True,
              help="Write the verified lots even when some lots have no cited IDs")
@topup_options
@click.option("-q", "--quiet", is_flag=True, help="No human output (errors still go to stderr)")
def export_cmd(layout_path, bricklink_path, rebrickable_path, condition, allow_partial, kit_id, kits,
               owned_files, missing_files, spares, quiet):
    """Write marketplace files for the pieces to buy (verified lots only)."""
    if bricklink_path is None and rebrickable_path is None:
        raise click.UsageError("give at least one of --bricklink PATH, --rebrickable PATH")
    for p in (bricklink_path, rebrickable_path):
        if p is not None and not p.parent.is_dir():
            raise CommandError(f"output directory {p.parent} does not exist", 1)
    pl = _load(layout_path, kit_id, kits, owned_files, missing_files, spares)
    try:
        xml = to_bricklink_xml(pl, condition, allow_partial) if bricklink_path else None
        csv_text = to_rebrickable_csv(pl, allow_partial) if rebrickable_path else None
    except UnverifiedLotsError as exc:
        lines = [f"{exc}.", "Nothing was written. Use --allow-partial to write the verified lots "
                            "only, or rebuild the layout with cited colors (kit part-colors)."]
        raise CommandError("\n".join(lines), exc.exit_code)
    omitted = blocking_lots(pl) if allow_partial else ()
    echo = (lambda *a, **k: None) if quiet else click.echo
    if xml is None and csv_text is None:
        echo(NOTHING_TO_BUY if not omitted else
             "Nothing verified to buy; no file written.")
    else:
        lots = [l for l in pl.lots if l.verified and l.to_buy > 0]
        pieces = sum(l.to_buy for l in lots)
        if xml is not None:
            bricklink_path.write_text(xml, encoding="utf-8")
            echo(f"Wrote BrickLink wanted list {bricklink_path}: {len(lots)} items, {pieces:,} pieces"
                 + (f", condition {condition}" if condition else ""))
        if csv_text is not None:
            rebrickable_path.write_text(csv_text, encoding="utf-8")
            echo(f"Wrote Rebrickable parts CSV {rebrickable_path}: {len(lots)} rows, {pieces:,} pieces")
        for l in lots:  # feature 017: the in-margin plaque's tile, named with its marketplace IDs
            if l.part_type == PLAQUE_PART_TYPE:
                r = l.ids
                echo(f"Plaque tile in the files: {plaque_lot_text(l, l.to_buy)}; BrickLink {r.bricklink_item_no} / "
                     f"{r.bricklink_color_name} ({r.bricklink_color_id}); Rebrickable {r.rebrickable_part_num} / "
                     f"{r.rebrickable_color_name} ({r.rebrickable_color_id})")
        if xml is not None:
            echo(BRICKLINK_UPLOAD_NOTE)
    if omitted:
        echo(f"Omitted {len(omitted)} unverified lot(s) (no cited marketplace IDs):")
        for l in omitted:
            echo(f"  {PART_TYPE_TEXT[l.part_type]} {l.layout_color_name} ({l.color_key}): {l.reason}; "
                 f"{l.to_buy:,} to buy")
    echo(PRICE_NOTE)
    echo(ACKNOWLEDGEMENT)
    echo(DISCLAIMER)
