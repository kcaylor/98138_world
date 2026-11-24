"""Read-only `kit` commands: the cited kit 31203 inventory and color table."""

from __future__ import annotations

import json

import click

from ..kit import DISCLAIMER, UnsupportedKitError, load_kit_color_table, load_kit_inventory
from ..kit.colors import KIT_COLORS_PATH
from ..kit.inventory import INVENTORY_PATH, ROLES, check_kit_id


def _table(headers, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    lines = [fmt.format(*headers)]
    lines += [fmt.format(*[str(x) for x in r]) for r in rows]
    return [l.rstrip() for l in lines]


def _check_kit(kit_id: str) -> None:
    try:
        check_kit_id(kit_id)
    except UnsupportedKitError as exc:
        raise click.ClickException(str(exc))


@click.group()
def kit() -> None:
    """Show the cited reference data for LEGO World Map kit 31203 (works offline)."""


@kit.command()
@click.option("--kit", "kit_id", default="31203", show_default=True, help="Kit ID")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
@click.option("--role", type=click.Choice(list(ROLES)), help="Only list elements with this role")
def inventory(kit_id: str, output_format: str, role: str) -> None:
    """List every element on the instructions' parts inventory page."""
    _check_kit(kit_id)
    if output_format == "json":
        click.echo(INVENTORY_PATH.read_text(encoding="utf-8"), nl=False)
        return
    inv = load_kit_inventory(kit_id)
    elements = inv.by_role(role) if role else inv.elements
    rows = [(e.element_id, "/".join(e.part_ids), e.description, e.color, e.quantity, e.role,
             e.source_page) for e in elements]
    for line in _table(["element", "part(s)", "description", "color", "qty", "role", "page"], rows):
        click.echo(line)
    click.echo()
    click.echo(f"Total: {len(elements)} lines, {sum(e.quantity for e in elements):,} pieces")
    click.echo(f"Source: {inv.source.url} (SHA-256 {inv.source.sha256}), "
               f"page{'s' if len(inv.source.pages) > 1 else ''} "
               f"{', '.join(map(str, inv.source.pages))}")
    click.echo(DISCLAIMER)


@kit.command()
@click.option("--kit", "kit_id", default="31203", show_default=True, help="Kit ID")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
def colors(kit_id: str, output_format: str) -> None:
    """List the kit's 10 map colors with LEGO, BrickLink and Rebrickable names and IDs."""
    _check_kit(kit_id)
    if output_format == "json":
        click.echo(KIT_COLORS_PATH.read_text(encoding="utf-8"), nl=False)
        return
    table = load_kit_color_table()
    inv = load_kit_inventory(kit_id)
    qty = {e.element_id: e.quantity for e in inv.elements}
    rows = [(c.key, f"{c.lego.name} ({c.lego.id})", f"{c.bricklink.name} ({c.bricklink.id})",
             f"{c.rebrickable.name} ({c.rebrickable.id})", c.role, c.element_id,
             qty.get(c.element_id, 0)) for c in table.colors]
    for line in _table(["key", "LEGO (id)", "BrickLink (id)", "Rebrickable (id)", "role", "element",
                        "qty"], rows):
        click.echo(line)
    click.echo()
    click.echo("Sources: " + "; ".join(f"{c.title} <{c.url}>" for c in table.source.citations))
    click.echo(DISCLAIMER)


PART_HEADINGS = {"6141": "1x1 round plate, land", "98138": "1x1 round tile, ocean",
                 "3070b": "1x1 square tile, margin"}  # 3070b: feature 016, not in the kit


@kit.command("part-colors")
@click.option("--part", type=click.Choice(["6141", "98138", "3070b"]),
              help="Only this part (6141 plate, 98138 tile, 3070b tile 1x1 square)")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
def part_colors(part: str, output_format: str) -> None:
    """List the colors each map part is made in, with LEGO, BrickLink and Rebrickable IDs (cited)."""
    from ..kit.part_colors import load_part_colors

    table = load_part_colors()
    parts = [part] if part else list(table.parts)
    if output_format == "json":
        rows = []
        for p in parts:
            for c in table.for_part(p):
                rows.append({"part_id": p, "key": c.key, "element_id": c.element_id,
                             "element_ids": list(c.element_ids),
                             "lego": {"name": c.lego.name, "id": c.lego.id},
                             "bricklink": {"name": c.bricklink.name, "id": c.bricklink.id},
                             "rebrickable": {"name": c.rebrickable.name, "id": c.rebrickable.id},
                             "rgb": list(c.rgb), "in_kit": c.in_kit,
                             "citations": {k: v.id for k, v in c.citations.items()}})
        click.echo(json.dumps({"colors": rows, "source": table.source, "disclaimer": DISCLAIMER},
                              indent=2, ensure_ascii=False))
        return
    for p in parts:
        rows = [(c.key, f"{c.lego.name} ({c.lego.id})", f"{c.bricklink.name} ({c.bricklink.id})",
                 f"{c.rebrickable.name} ({c.rebrickable.id})", c.element_id, "yes" if c.in_kit else "no")
                for c in table.for_part(p)]
        click.echo(f"Part {p} ({PART_HEADINGS[p]}):")
        for line in _table(["key", "LEGO (id)", "BrickLink (id)", "Rebrickable (id)", "element", "in kit"], rows):
            click.echo(line)
        click.echo()
    click.echo("Sources: " + "; ".join(f"{c.title} <{c.url}>" for c in table.citations))
    terms = table.source.get("terms") or {}
    if terms:
        click.echo(f"Rebrickable terms: \"{terms['text']}\" <{terms['url']}>")
    click.echo(table.source.get("acknowledgement") or "Catalog data: Rebrickable (rebrickable.com).")
    click.echo(DISCLAIMER)


@kit.command("part-numbers")
@click.option("--kit", "kit_id", default="31203", show_default=True, help="Kit ID")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
def part_numbers(kit_id: str, output_format: str) -> None:
    """Show each marketplace's number for the map parts, with cited sources (feature 005; 3070b: 016)."""
    from ..kit.part_numbers import PART_NUMBERS_PATH, load_part_numbers

    _check_kit(kit_id)
    if output_format == "json":
        click.echo(PART_NUMBERS_PATH.read_text(encoding="utf-8"), nl=False)
        return
    table = load_part_numbers()
    rows = [(p.part_id, p.name, ", ".join(p.lego_design_ids),
             f"{p.bricklink_item_type} {p.bricklink_item_no}", ", ".join(p.bricklink_alternates),
             p.rebrickable_part_num, len(p.bricklink_colors))
            for p in table.parts.values()]
    for line in _table(["part", "name", "LEGO design", "BrickLink", "BrickLink alternates",
                        "Rebrickable", "BrickLink colors"], rows):
        click.echo(line)
    click.echo()
    click.echo("Wanted lists use each marketplace's own number: BrickLink item "
               f"{table.get('6141').bricklink_item_no} for the plate (6141 is an alternate there), "
               f"Rebrickable part {table.get('6141').rebrickable_part_num}; "
               f"the tile is {table.get('98138').bricklink_item_no} on both.")
    if "3070b" in table.parts:  # feature 016: the square tile of template margins (not in the kit)
        sq = table.get("3070b")
        click.echo(f"For template margins, the square tile is BrickLink item {sq.bricklink_item_no} "
                   f"(3070b is an alternate there), Rebrickable part {sq.rebrickable_part_num}; "
                   "it is not in kit 31203.")
    click.echo("Sources:")
    for page in table.pages:
        click.echo(f"  {page.title} <{page.url}> SHA-256 {page.sha256}, accessed {page.accessed}")
    click.echo("Catalog data: Rebrickable (rebrickable.com), BrickLink.")
    click.echo(DISCLAIMER)
