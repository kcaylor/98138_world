"""`map` commands: build a layout from a recipe, check a recipe, list bundled recipes (feature 004).

Only `map build --fetch` uses the network (to download a recipe's missing pinned datasets).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from ..datasets.cache import DatasetError, fetch, is_cached
from ..kit.source import DISCLAIMER
from ..maps.build import build_map, missing_datasets
from ..maps.classify import MapBuildError
from ..maps.margin import MarginError, MarginTreatment, resolve_margin
from ..maps.recipe import Recipe, RecipeError, bundled_recipes, load_recipe
from ..maps.suitability import extra_tiles
from .options import arrangement_option, template_options


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


_SOURCE_TEXT = {"recipe": "from the recipe", "option": "from --arrangement", "default": "default"}
_UNIT_TEXT = {"degc": "°C", "degree_c": "°C", "degrees_c": "°C", "celsius": "°C"}


def arrangement_line(report: Dict[str, Any], arrangement) -> str:
    """``Arrangement: B (...) - from the recipe`` (feature 009, FR-012)."""
    source = _SOURCE_TEXT.get(report.get("arrangement_source", ""), "")
    return f"Arrangement: {arrangement.describe()}" + (f" - {source}" if source else "")


_TEMPLATE_SOURCE_TEXT = {"recipe": "from the recipe", "option": "from --template", "default": "default"}
KIT_MARGIN_NOTE = ("Note: margin settings are not used on the kit template kit-31203 (it has no margin); "
                   "they apply to templates with a margin, such as winkel-tripel.")


def template_lines(result) -> List[str]:
    """``Template: ...`` and ``Margin: ...`` for a non-kit build (feature 016, contracts/cli.md);
    nothing for the kit, whose output stays as it was."""
    t = result.template
    if t is None or t.is_kit:
        return []
    report = result.report
    source = _TEMPLATE_SOURCE_TEXT.get(report.get("template_source", ""), "")
    margin = report["margin"]
    counts = report["template"]["counts"]
    ring = f"ring {counts['ring']:,} {margin['ring']}" if margin["ring"] else "no ring"
    return [f"Template: {t.id} ({t.title})" + (f" - {source}" if source else ""),
            f"Margin: {counts['margin']:,} square tiles (part {margin['part_id']}): {margin['color']}; {ring}"]


def resolve_margin_options(recipe: Recipe, margin_color: Optional[str],
                           ring_color: Optional[str]) -> Optional[MarginTreatment]:
    """The recipe's ``[margin]`` overridden by ``--margin-color``/``--ring-color`` (exit 1 on a bad
    color); None when neither the recipe nor an option sets one (feature 016)."""
    if recipe.margin is None and margin_color is None and ring_color is None:
        return None
    try:
        return resolve_margin(recipe.margin, margin_color, ring_color)
    except MarginError as exc:
        raise CommandError(str(exc), 1)


def echo_template(result, margin: Optional[MarginTreatment], echo=click.echo) -> None:
    lines = template_lines(result)
    for line in lines:
        echo(line)
    if not lines and margin is not None:
        echo(KIT_MARGIN_NOTE)


def layer_units(recipe: Recipe) -> Dict[str, str]:
    """Display units of each data layer's variable, from the recipe's dataset entry."""
    out = {}
    for layer in recipe.layers:
        if layer.dataset is not None and layer.variable:
            u = str((layer.dataset.variables or {}).get(layer.variable, {}).get("units", "") or "")
            out[layer.cls] = _UNIT_TEXT.get(u.lower(), u)
    return out


def _bound(b: float, signed: bool = True) -> str:
    if b == 0:
        return "0"
    text = f"{abs(b):.2f}".rstrip("0").rstrip(".")
    if text == "0":  # small positive bounds (e.g. 0.001 mg m-3) keep their significant digits
        text = f"{abs(b):.3g}"
    if not signed:
        return ("-" if b < 0 else "") + text
    return ("+" if b > 0 else "-") + text


def legend_ranges(bounds) -> List[str]:
    """Range text per class: ``below b1``, ``b(i) to b(i+1)``, ``b(n-1) and above`` (end classes
    open; membership [lower, upper)). Signs are shown only when a bound is negative (012)."""
    n = len(bounds) - 1
    if n < 1:
        return []
    if n == 1:
        return ["all values"]
    signed = any(b < 0 for b in bounds)
    out = [f"below {_bound(bounds[1], signed)}"]
    out += [f"{_bound(bounds[i], signed)} to {_bound(bounds[i + 1], signed)}" for i in range(1, n - 1)]
    out.append(f"{_bound(bounds[n - 1], signed)} and above")
    return out


def secondary_ranges(bounds, legend: Dict[str, Any]) -> List[str]:
    """The legend ranges in a layer's secondary units (feature 013), e.g. ``182.5 to 365 mm/yr``."""
    f, units = float(legend["factor"]), legend["units"]
    return [t.replace(" and above", f" {units} and above") if t.endswith(" and above") else f"{t} {units}"
            for t in legend_ranges([b * f for b in bounds])]


def _echo_legend(layer: Dict[str, Any], units: str, echo) -> None:
    bounds = layer.get("class_bounds") or []
    counts = layer.get("class_counts") or []
    if layer.get("classification") != "bins" or len(bounds) != len(counts) + 1:
        return
    legend = layer.get("legend")
    if legend:
        head = f"{units}; {legend['units']}" if units else legend["units"]
        echo(f"  Legend ({head}):")
    else:
        echo(f"  Legend ({units}):" if units else "  Legend:")
    ranges = legend_ranges(bounds)
    if legend:
        ranges = [f"{a} ({b})" for a, b in zip(ranges, secondary_ranges(bounds, legend))]
    kw = max(len(c["key"]) for c in counts)
    rw = max(len(t) for t in ranges)
    cw = max(len(f"{c['cells']:,}") for c in counts)
    for c, text in zip(counts, ranges):
        echo(f"    {c['key']:<{kw}}  {text:<{rw}}  {c['cells']:>{cw},}")


def echo_report(report: Dict[str, Any], echo=click.echo, units: Optional[Dict[str, str]] = None) -> None:
    units = units or {}
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
        nd = layer.get("no_data")
        if nd:
            params = ", ".join(f"{k} {nd[k]:g}" for k in ("min_lat", "min_share", "sparse_lat", "min_steps",
                                                          "value") if nd.get(k) is not None)
            echo(f"  No data ({nd['rule']}): {nd['cells']:,} cells of {nd['color']} ({params}), assigned "
                 "before classification and counted in the table below")
        for o in layer.get("overrides") or []:  # feature 013
            echo(f"  Override {o['name']} ({o['kind']}): {o['cells']:,} cells of {o['color']}, assigned "
                 "before classification and counted in the table below")
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
        _echo_legend(layer, units.get(layer["class"], ""), echo)
        echo(f"  Tiles beyond one kit: {extra_tiles(layer['supply']):,}")
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
    """Build maps from recipes: a land layer and an ocean layer on the kit 31203 template or a
    confirmed map template (`template list`)."""


@map_group.command()
@click.argument("recipe")
@click.option("--output", "-o", required=True, type=click.Path(dir_okay=False), help="Layout JSON to write")
@click.option("--preview", type=click.Path(dir_okay=False), help="Also write a PNG preview (8x8 px per stud)")
@click.option("--preview-style", type=click.Choice(["round", "square"]), default="round", show_default=True,
              help="Preview studs: round pieces on black, as built, or square cells")
@click.option("--report", "report_path", type=click.Path(dir_okay=False), help="Write the suitability report (JSON)")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
@click.option("--fetch", "do_fetch", is_flag=True,
              help="Download the recipe's missing pinned datasets (verified) before building")
@click.option("--compare-official", is_flag=True, default=None,
              help="Print cell agreement with the official design (always on for official-31203*)")
@arrangement_option(default=None)
@template_options
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def build(recipe, output, preview, preview_style, report_path, cache_dir, do_fetch, compare_official, arrangement,
          template_id, margin_color, ring_color, quiet):
    """Build RECIPE (a recipe file or a bundled recipe id) into a schema 2.0 layout.

    \b
    Examples:
        lego-image-processor map build official-31203 -o official.json --preview official.png
        lego-image-processor map build ocean-sst -o sst.json --fetch
        lego-image-processor map build land-elevation --arrangement B -o elev-B.json
        lego-image-processor map build ocean-el-nino -o el-nino.json   # hung as B (recipe)
        lego-image-processor map build ocean-sst --template winkel-tripel -o w.json --preview w.png
    """
    echo = (lambda *a, **k: None) if quiet else click.echo
    r = _load(recipe)
    margin = resolve_margin_options(r, margin_color, ring_color)
    if do_fetch:
        for entry in missing_datasets(r, cache_dir):
            echo(f"Fetching {entry.id} ({entry.size:,} bytes) from {entry.url}")
            try:
                path, _ = fetch(entry, cache_dir=cache_dir)
            except DatasetError as exc:
                raise _dataset_failure(exc)
            what = "content SHA-256" if entry.content_sha256 and not entry.sha256 else "SHA-256"
            echo(f"Fetched {entry.id}: {path} ({what} verified)")
    try:
        result = build_map(r, cache_dir=cache_dir, compare_official=compare_official or None,
                           arrangement=arrangement, template=template_id, margin=margin)
    except DatasetError as exc:
        raise _dataset_failure(exc)
    except MapBuildError as exc:
        raise CommandError(f"Cannot build {r.id}: {exc}", 1)
    echo(f"Recipe: {r.id} - {r.title} (format {r.format}, SHA-256 {r.sha256})")
    echo(arrangement_line(result.report, result.arrangement))
    echo_template(result, margin, echo)
    echo_report(result.report, echo, layer_units(r))
    if result.agreement:
        echo_agreement(result.agreement, echo)
    try:
        Path(output).write_text(result.layout.to_json(), encoding="utf-8")
        if preview:
            from ..maps.preview import write_preview
            write_preview(result.layout, preview, style=preview_style)
        if report_path:
            _write_json(report_path, result.report)
    except OSError as exc:
        raise CommandError(f"Cannot write output: {exc}", 1)
    margin_tiles = (f", {result.layout.margin_positions:,} margin tiles"
                    if result.layout.template is not None else "")  # feature 016: non-kit layouts only
    echo(f"Layout: {output} ({result.layout.total_positions:,} positions, "
         f"{result.layout.land_positions:,} land plates, {result.layout.ocean_positions:,} ocean tiles"
         f"{margin_tiles})")
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
@arrangement_option(default=None)
@template_options
def check(recipe, report_path, cache_dir, arrangement, template_id, margin_color, ring_color):
    """Run the suitability check on RECIPE without writing a layout (exit 0 even with warnings)."""
    r = _load(recipe)
    margin = resolve_margin_options(r, margin_color, ring_color)
    try:
        result = build_map(r, cache_dir=cache_dir, compare_official=False, arrangement=arrangement,
                           template=template_id, margin=margin)
    except DatasetError as exc:
        raise _dataset_failure(exc)
    except MapBuildError as exc:
        raise CommandError(f"Cannot build {r.id}: {exc}", 1)
    click.echo(f"Suitability check: {r.id} - {r.title}")
    click.echo(arrangement_line(result.report, result.arrangement))
    echo_template(result, margin)
    echo_report(result.report, units=layer_units(r))
    if report_path:
        _write_json(report_path, result.report)
        click.echo(f"Report: {report_path}")
    echo_citations(result.report["citations"])
    click.echo(DISCLAIMER)


@map_group.command()
@click.argument("recipe")
@click.option("--output", "-o", required=True, type=click.Path(dir_okay=False), help="JSON file to write")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
@arrangement_option(default=None)
@template_options
def cells(recipe, output, cache_dir, arrangement, template_id, margin_color, ring_color):
    """Write RECIPE's per-cell classes, values, shadow and ice regions for recoloring (JSON).

    The file feeds the web site's palette chooser (feature 015): each layer's built class and
    data value per cell, default class bounds, the land shadow, the ice-covered cells and the
    cited colors of both parts with CIE L*. On a map template with a margin (`--template`) it
    also marks the margin cells (M) and gives the margin and ring colors and the square tile's
    colors. It is a preview aid only: layouts, parts lists, prices and build sheets do not use
    it. Never downloads (build first with `map build --fetch`).

    \b
    Examples:
        lego-image-processor map cells land-elevation -o cells.json --arrangement B
        lego-image-processor map cells ocean-sst --template winkel-tripel -o cells.json
    """
    from ..maps.cells import map_cells
    from ..maps.ice import TemplateIceError, template_ice_path

    r = _load(recipe)
    margin = resolve_margin_options(r, margin_color, ring_color)
    try:
        result = build_map(r, cache_dir=cache_dir, compare_official=False, arrangement=arrangement,
                           template=template_id, margin=margin)
    except DatasetError as exc:
        raise _dataset_failure(exc)
    except MapBuildError as exc:
        raise CommandError(f"Cannot build {r.id}: {exc}", 1)
    try:
        data = map_cells(result)
    except TemplateIceError as exc:
        raise CommandError(f"Cannot write the cells of {r.id}: {exc}", 1)
    click.echo(f"Recipe: {r.id} - {r.title} (format {r.format}, SHA-256 {r.sha256})")
    click.echo(arrangement_line(result.report, result.arrangement))
    echo_template(result, margin)
    for cls in ("land", "ocean"):
        layer = data["layers"][cls]
        head = f"{cls.capitalize()} layer: {layer['role']}"
        if layer["role"] == "data":
            head += f", {layer['method']}"
        head += f", {layer['cells']:,} cells, {len(layer['colors'])} colors"
        if layer.get("bounds"):
            head += f", bounds {layer['bounds_source']} ({layer.get('units', '')})"
        click.echo(head)
        if layer["role"] == "data" and "no_value" in layer:
            click.echo(f"  {len(layer['no_value']):,} cells have no source value and take the nearest "
                       f"value ({layer['no_value_ice']:,} of them in ice regions)")
    sh = data["shadow"]
    if sh["enabled"]:
        click.echo(f"Land shadow: {sh['cells']:,} cells of {sh['color']}")
    ice_file = ("kit_31203_ice.json, as hung" if "template" not in data   # feature 016: a template's own file
                else template_ice_path(result.template).name)
    click.echo(f"Ice regions: {len(data['ice']['land']):,} land-ice cells, "
               f"{len(data['ice']['sea']):,} sea-ice cells ({ice_file})")
    try:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        Path(output).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise CommandError(f"Cannot write output: {exc}", 1)
    click.echo(f"Cells: {output} ({len(text.encode('utf-8')):,} bytes)")
    click.echo(data["note"])
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
        arr = r.arrangement.id if r.arrangement is not None else "A"
        rows.append((rid, r.title, arr, layers, names, cached))
    for line in _table(["id", "title", "arrangement", "layers", "datasets", "cached"], rows):
        click.echo(line)
    click.echo()
    click.echo("Build one with: lego-image-processor map build <id> -o layout.json [--fetch]")
    click.echo(DISCLAIMER)
