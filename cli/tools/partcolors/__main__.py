"""``python -m partcolors build [--snapshot-dir DIR] [--check] [--output PATH]`` and
``python -m partcolors plaque-parts [--snapshots DIR] [--check]`` (feature 017; maintainer only).

Exit codes: 0 ok / no differences; 1 differences found by --check; 4 snapshot missing or checksum
mismatch; 5 (plaque-parts) a rule fails. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

import click

from lego_image_processor.datasets.cache import cache_root
from lego_image_processor.kit.colors import KIT_COLORS_PATH
from lego_image_processor.kit.inventory import INVENTORY_PATH
from lego_image_processor.kit.part_colors import PART_COLORS_PATH, parse_part_colors
from lego_image_processor.kit.plaque_parts import PLAQUE_PARTS_PATH
from lego_image_processor.kit.source import DISCLAIMER
from partnumbers.build import BuildError

from . import plaque
from .build import SNAPSHOTS, SnapshotError, build, differences, read_snapshots, to_text


def default_snapshot_dir() -> Path:
    return cache_root() / "sources" / "partcolors"


@click.group()
def main() -> None:
    """Build the cited part-color table from pinned catalog snapshots."""


@main.command("build")
@click.option("--snapshot-dir", type=click.Path(file_okay=False, path_type=Path),
              help="Directory holding the pinned snapshot files (default <cache>/sources/partcolors)")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=PART_COLORS_PATH,
              show_default=True)
@click.option("--check", is_flag=True, help="Compare with the committed file; write nothing")
def build_cmd(snapshot_dir, output, check):
    snapshot_dir = snapshot_dir or cache_root() / "sources" / "partcolors"
    try:
        snap = read_snapshots(snapshot_dir)
    except SnapshotError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(exc.exit_code)
    kit = json.loads(KIT_COLORS_PATH.read_text(encoding="utf-8"))
    old = json.loads(Path(output).read_text(encoding="utf-8")) if Path(output).is_file() else {}
    generated_on = old.get("source", {}).get("generated_on") if check else _dt.date.today().isoformat()
    result = build(snap, kit, generated_on or _dt.date.today().isoformat())
    parse_part_colors(result.data)  # the package's own rules must accept it
    for n in result.kit_notes:
        click.echo(f"note: {n}")
    for e in result.excluded:
        click.echo(f"excluded: part {e['part']} Rebrickable {e['rebrickable_id']} ({e['name']}): {e['reason']}")
    if check:
        diff = differences(result.data, old)
        if diff:
            for d in diff:
                click.echo(f"difference: {d}")
            click.echo(DISCLAIMER)
            sys.exit(1)
        click.echo("no differences")
        click.echo(DISCLAIMER)
        return
    Path(output).write_text(to_text(result.data), encoding="utf-8")
    n = {p: len(r) for p, r in result.data["parts"].items()}
    click.echo(f"wrote {output}: " + ", ".join(f"{p}: {k} colors" for p, k in n.items()))
    click.echo(DISCLAIMER)


@main.command("plaque-parts")
@click.option("--snapshots", "snapshot_dir", type=click.Path(file_okay=False, path_type=Path),
              help="Directory holding the pinned snapshot files (default <cache>/sources/partcolors; "
                   "the BrickLink pages are read from its sibling partnumbers/)")
@click.option("--check", is_flag=True, help="Compare with the committed file; write nothing")
def plaque_parts_cmd(snapshot_dir, check):
    """Build data/plaque_parts.json: the Black tiles and plates of the sticker plaques (017)."""
    output = Path(PLAQUE_PARTS_PATH)
    snapshot_dir = snapshot_dir or default_snapshot_dir()
    try:
        snap, pages = plaque.read_sources(snapshot_dir)
        inventory = json.loads(Path(INVENTORY_PATH).read_text(encoding="utf-8"))
        black = plaque.black_row(json.loads(Path(PART_COLORS_PATH).read_text(encoding="utf-8")))
        old = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {}
        generated_on = (old.get("source", {}).get("generated_on") if check else None) \
            or _dt.date.today().isoformat()
        data = plaque.build(snap, pages, inventory, black, generated_on)
    except (SnapshotError, BuildError) as exc:
        click.echo(f"Error: {exc}", err=True)
        click.echo(DISCLAIMER, err=True)
        sys.exit(exc.exit_code)
    for line in plaque.summary(data):
        click.echo(line)
    if check:
        diff = plaque.differences(data, old)
        for d in diff:
            click.echo(f"difference: {d}")
        click.echo("no differences" if not diff else f"{len(diff)} difference(s)")
        click.echo(DISCLAIMER)
        sys.exit(1 if diff else 0)
    output.write_text(plaque.to_text(data), encoding="utf-8")
    click.echo(f"wrote {output}")
    click.echo(DISCLAIMER)


if __name__ == "__main__":
    main()
