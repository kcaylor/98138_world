"""`map` commands: build a layout from a recipe, check a recipe, list bundled recipes (feature 004).

Only `map build --fetch` uses the network (to download a recipe's missing pinned datasets).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import click

from ..datasets.cache import DatasetError, fetch, is_cached
from ..kit.source import DISCLAIMER
from ..maps.build import build_map, missing_datasets
from ..maps.classify import MapBuildError
from ..maps.recipe import RecipeError, bundled_recipes, load_recipe
from .options import arrangement_option


class CommandError(click.ClickException):
    """A failure with a contract exit code; the message is followed by the disclaimer."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code

    def show(self, file=None) -> None:  # noqa: D401 - click API
        click.echo(f"Error: {self.format_message()}", err=True)
        click.echo(DISCLAIMER, err=True)


def recipe_error(exc: RecipeError) -> CommandError:
    where = f" in {exc.file}" if exc.file else ""
    return CommandError(f"Recipe error{where}: {exc}", 1)


def _load(ref: str):
    try:
        return load_recipe(ref)
    except RecipeError as exc:
        raise recipe_error(exc)


def _table(headers, rows) -> List[str]:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    return [fmt.format(*headers).rstrip()] + [fmt.format(*[str(x) for x in r]).rstrip() for r in rows]


def _pct(share) -> str:
    return "n/a" if share is None else f"{share * 100:.1f}%"


def echo_report(report: Dict[str, Any], echo=click.echo) -> None:
    for layer in report["layers"]:
        head = f"{layer['class'].capitalize()} layer ({layer['role']}, part {layer['part_id']}, {layer['cells']:,} cells)"
        if layer.get("dataset"):
            d = layer["dataset"]
            head += f": {d['id']} {d['version']}, {layer.get('classification')}"
        echo(head)
        sh = report.get("shadow") or {}
        if layer["class"] == "ocean" and sh.get("cells"):
            echo(f"  Land shadow (cast {sh['direction']}): {sh['cells']:,} cells of {sh['color']}, assigned "
                 "first and counted in the table below")
        if layer["role"] == "data":
            vl = layer.get("variance_lost")
            echo(f"  Variance lost below grid scale: {_pct(vl)}; filled from neighbours: "
                 f"{layer.get('filled_cells', 0):,} cells ({_pct(layer.get('filled_share'))})")
            de = layer.get("min_neighbour_delta_e00")
            if de:
                echo(f"  Closest neighbouring colors: {de['pair'][0]} / {de['pair'][1]} (ΔE00 {de['delta_e00']:.1f})")
            ob = layer.get("outside_bounds")
            if ob:
                echo(f"  Outside the class bounds: {ob['below']} below, {ob['above']} above (clamped)")
        rows = [(r["key"], f"{r['used']:,}", f"{r['supplied']:,}" if r["in_kit"] else "not in kit",
                 "yes" if r["within"] else "no") for r in layer["supply"]]
        for line in _table(["  color", "cells", "one kit", "within"], [("  " + a, b, c, d) for a, b, c, d in rows]):
            echo(line)
    warnings = report["warnings"]
    if warnings:
        echo(f"Warnings ({len(warnings)}):")
        for w in warnings:
            echo(f"  - {w['message']}")
    else:
        echo("No warnings.")
    t = report["thresholds"]
    echo(f"  (thresholds: variance lost {t['variance_lost'] * 100:.0f}%, filled {t['filled_share'] * 100:.0f}%, "
         f"ΔE00 {t['min_delta_e00']:.0f})")


def echo_agreement(agreement: Dict[str, Any], echo=click.echo) -> None:
    a = agreement
    echo("Agreement with the official 31203 design (cells with the same color):")
    for part in ("land", "ocean"):
        echo(f"  {part}: {a[part]['agree']:,} / {a[part]['cells']:,} ({_pct(a[part]['share'])})")
    echo(f"  total: {a['total']['agree']:,} / {a['total']['cells']:,}")


def echo_citations(citations, echo=click.echo) -> None:
    if not citations:
        return
    echo("Data citations and licenses:")
    for c in citations:
        line = f"  - {c['id']} ({c['version']}): {c['citation']}"
        if c.get("doi"):
            line += f" https://doi.org/{c['doi']}"
        echo(line)
        echo(f"    License: {c['license']}")
        if c.get("acknowledgement"):
            echo(f"    Acknowledgement: {c['acknowledgement']}")


def _write_json(path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _dataset_failure(exc: DatasetError) -> CommandError:
    return CommandError(str(exc), getattr(exc, "exit_code", 1))


@click.group(name="map")
def map_group() -> None:
    """Build maps from recipes: a land layer and an ocean layer on the kit 31203 template."""


@map_group.command()
@click.argument("recipe")
@click.option("--output", "-o", required=True, type=click.Path(dir_okay=False), help="Layout JSON to write")
@click.option("--preview", type=click.Path(dir_okay=False), help="Also write a PNG preview (8x8 px per stud)")
@click.option("--report", "report_path", type=click.Path(dir_okay=False), help="Write the suitability report (JSON)")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
@click.option("--fetch", "do_fetch", is_flag=True,
              help="Download the recipe's missing pinned datasets (verified) before building")
@click.option("--compare-official", is_flag=True, default=None,
              help="Print cell agreement with the official design (always on for official-31203*)")
@arrangement_option()
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def build(recipe, output, preview, report_path, cache_dir, do_fetch, compare_official, arrangement, quiet):
    """Build RECIPE (a recipe file or a bundled recipe id) into a schema 2.0 layout.

    \b
    Examples:
        lego-image-processor map build official-31203 -o official.json --preview official.png
        lego-image-processor map build ocean-sst -o sst.json --fetch
        lego-image-processor map build land-elevation --arrangement B -o elev-B.json
    """
    echo = (lambda *a, **k: None) if quiet else click.echo
    r = _load(recipe)
    if do_fetch:
        for entry in missing_datasets(r, cache_dir):
            echo(f"Fetching {entry.id} ({entry.size:,} bytes) from {entry.url}")
            try:
                path, _ = fetch(entry, cache_dir=cache_dir)
            except DatasetError as exc:
                raise _dataset_failure(exc)
            echo(f"Fetched {entry.id}: {path} (SHA-256 verified)")
    try:
        result = build_map(r, cache_dir=cache_dir, compare_official=compare_official or None,
                           arrangement=arrangement)
    except DatasetError as exc:
        raise _dataset_failure(exc)
    except MapBuildError as exc:
        raise CommandError(f"Cannot build {r.id}: {exc}", 1)
    echo(f"Recipe: {r.id} - {r.title} (format {r.format}, SHA-256 {r.sha256})")
    echo(f"Arrangement: {arrangement.describe()}")
    echo_report(result.report, echo)
    if result.agreement:
        echo_agreement(result.agreement, echo)
    try:
        Path(output).write_text(result.layout.to_json(), encoding="utf-8")
        if preview:
            from ..maps.preview import write_preview
            write_preview(result.layout, preview)
        if report_path:
            _write_json(report_path, result.report)
    except OSError as exc:
        raise CommandError(f"Cannot write output: {exc}", 1)
    echo(f"Layout: {output} ({result.layout.total_positions:,} positions, "
         f"{result.layout.land_positions:,} land plates, {result.layout.ocean_positions:,} ocean tiles)")
    if preview:
        echo(f"Preview: {preview}")
    if report_path:
        echo(f"Report: {report_path}")
    echo_citations(result.report["citations"], echo)
    echo(DISCLAIMER)


@map_group.command()
@click.argument("recipe")
@click.option("--report", "report_path", type=click.Path(dir_okay=False), help="Write the report (JSON)")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
@arrangement_option()
def check(recipe, report_path, cache_dir, arrangement):
    """Run the suitability check on RECIPE without writing a layout (exit 0 even with warnings)."""
    r = _load(recipe)
    try:
        result = build_map(r, cache_dir=cache_dir, compare_official=False, arrangement=arrangement)
    except DatasetError as exc:
        raise _dataset_failure(exc)
    except MapBuildError as exc:
        raise CommandError(f"Cannot build {r.id}: {exc}", 1)
    click.echo(f"Suitability check: {r.id} - {r.title}")
    click.echo(f"Arrangement: {arrangement.describe()}")
    echo_report(result.report)
    if report_path:
        _write_json(report_path, result.report)
        click.echo(f"Report: {report_path}")
    echo_citations(result.report["citations"])
    click.echo(DISCLAIMER)


@map_group.command()
@click.option("--copy", "copy_args", nargs=2, metavar="ID DEST", help="Copy a bundled recipe to DEST to start a new one")
@click.option("--force", is_flag=True, help="With --copy: overwrite DEST")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (for the cached column)")
def recipes(copy_args, force, cache_dir):
    """List the bundled recipes, or copy one with --copy ID DEST."""
    try:
        bundled = bundled_recipes()
    except RecipeError as exc:
        raise recipe_error(exc)
    if copy_args:
        rid, dest = copy_args
        if rid not in bundled:
            raise CommandError(f"No bundled recipe {rid!r} (bundled: {', '.join(bundled)})", 1)
        dest = Path(dest)
        if dest.exists() and not force:
            raise CommandError(f"{dest} exists; use --force to overwrite", 1)
        shutil.copyfile(bundled[rid], dest)
        click.echo(f"Copied {rid} to {dest}")
        click.echo(DISCLAIMER)
        return
    rows = []
    for rid, path in bundled.items():
        try:
            r = load_recipe(path)
        except RecipeError as exc:
            raise recipe_error(exc)
        layers = ", ".join(f"{l.cls} {l.role}" for l in r.layers)
        ds = [e for e in r.datasets()]
        names = ", ".join(e.id for e in ds) or "-"
        cached = "yes" if all(is_cached(e, cache_dir) for e in ds) else "no"
        rows.append((rid, r.title, layers, names, cached))
    for line in _table(["id", "title", "layers", "datasets", "cached"], rows):
        click.echo(line)
    click.echo()
    click.echo("Build one with: lego-image-processor map build <id> -o layout.json [--fetch]")
    click.echo(DISCLAIMER)
