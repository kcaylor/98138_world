"""``python -m partnumbers build [--source-dir DIR] [--check] [--output PATH]`` (maintainer only).

Downloads a pinned page into the source cache only when it is missing. Exit codes: 0 ok / no
differences; 1 differences found by --check; 4 page missing or checksum mismatch; 5 pages
inconsistent. Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

import click

from lego_image_processor.datasets.cache import cache_root
from lego_image_processor.kit.inventory import INVENTORY_PATH
from lego_image_processor.kit.part_numbers import PART_NUMBERS_PATH, parse_part_numbers
from lego_image_processor.kit.source import DISCLAIMER

from .build import BuildError, SourceError, build, differences, fetch_missing, read_pages, to_text


def default_source_dir() -> Path:
    return cache_root() / "sources" / "partnumbers"


@click.group()
def main() -> None:
    """Build the cited marketplace part-number file from pinned archived pages."""


@main.command("build")
@click.option("--source-dir", type=click.Path(file_okay=False, path_type=Path),
              help="Directory holding the pinned pages (default <cache>/sources/partnumbers)")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=PART_NUMBERS_PATH,
              show_default=True)
@click.option("--check", is_flag=True, help="Compare with the committed file; write nothing")
@click.option("--no-download", is_flag=True, help="Fail instead of downloading a missing page")
def build_cmd(source_dir, output, check, no_download):
    source_dir = source_dir or default_source_dir()
    try:
        if not no_download:
            for pid in fetch_missing(source_dir):
                click.echo(f"downloaded {pid}")
        texts = read_pages(source_dir)
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        old = json.loads(Path(output).read_text(encoding="utf-8")) if Path(output).is_file() else {}
        generated_on = (old.get("source", {}).get("generated_on") if check else None) \
            or _dt.date.today().isoformat()
        data = build(texts, inventory, generated_on)
        parse_part_numbers(data)  # the package's own rules must accept it
    except (SourceError, BuildError) as exc:
        click.echo(f"Error: {exc}", err=True)
        click.echo(DISCLAIMER, err=True)
        sys.exit(exc.exit_code)
    for pid, p in data["parts"].items():
        click.echo(f"part {pid}: BrickLink {p['bricklink']['item_type']} {p['bricklink']['item_no']} "
                   f"(alternates {', '.join(p['bricklink']['alternates'])}; "
                   f"{len(p['bricklink']['colors'])} colors), Rebrickable {p['rebrickable']['part_num']}, "
                   f"LEGO {', '.join(p['lego_design_ids'])}")
    if check:
        diff = differences(data, old)
        for d in diff:
            click.echo(f"difference: {d}")
        click.echo("no differences" if not diff else f"{len(diff)} difference(s)")
        click.echo(DISCLAIMER)
        sys.exit(1 if diff else 0)
    Path(output).write_text(to_text(data), encoding="utf-8")
    click.echo(f"wrote {output}")
    click.echo(DISCLAIMER)


if __name__ == "__main__":
    main()
