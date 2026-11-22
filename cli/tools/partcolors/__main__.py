"""``python -m partcolors build [--snapshot-dir DIR] [--check] [--output PATH]`` (maintainer only).

Exit codes: 0 ok / no differences; 1 differences found by --check; 4 snapshot missing or checksum
mismatch. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

import click

from lego_image_processor.datasets.cache import cache_root
from lego_image_processor.kit.colors import KIT_COLORS_PATH
from lego_image_processor.kit.part_colors import PART_COLORS_PATH, parse_part_colors
from lego_image_processor.kit.source import DISCLAIMER

from .build import SNAPSHOTS, SnapshotError, build, differences, read_snapshots, to_text


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


if __name__ == "__main__":
    main()
