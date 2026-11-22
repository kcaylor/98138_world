"""Read-only `kit` commands: the cited kit 31203 inventory and color table."""

from __future__ import annotations

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
