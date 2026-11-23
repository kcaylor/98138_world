"""`dataset` commands: list, fetch and inspect the canonical datasets (feature 004).

`dataset fetch` is the only command here that uses the network.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json

import click

from ..datasets.cache import DatasetError, cached_path, fetch, is_cached
from ..datasets.registry import load_registry
from ..kit.source import DISCLAIMER
from .map import CommandError, _load, _table


def _size(e) -> str:
    return f"{e.size:,}" if e.size else "-"


def _status(e, cache_dir) -> str:
    if e.kind == "packaged":
        return "packaged"
    return "yes" if is_cached(e, cache_dir) else "no"


@click.group()
def dataset() -> None:
    """Canonical datasets: pinned (URL, size, SHA-256), cached per user, cited."""


@dataset.command("list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", show_default=True)
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
def list_cmd(output_format, cache_dir):
    """List the registry with size, license and whether each dataset is cached."""
    reg = load_registry()
    if output_format == "json":
        rows = []
        for e in reg.entries:
            d = e.provenance()
            d.update(kind=e.kind, size=e.size, format=e.format,
                     cached=e.kind == "packaged" or is_cached(e, cache_dir))
            rows.append(d)
        click.echo(json.dumps({"datasets": rows, "disclaimer": DISCLAIMER}, indent=2, ensure_ascii=False))
        return
    rows = [(e.id, e.version, _size(e), e.license.split(";")[0].split(" (")[0], _status(e, cache_dir), e.title)
            for e in reg.entries]
    for line in _table(["id", "version", "size", "license", "cached", "title"], rows):
        click.echo(line)
    click.echo()
    click.echo("Fetch with: lego-image-processor dataset fetch <id>; details: dataset info <id>")
    click.echo(DISCLAIMER)


@dataset.command("fetch")
@click.argument("ids", nargs=-1)
@click.option("--recipe", help="Fetch the datasets this recipe (file or bundled id) needs")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
def fetch_cmd(ids, recipe, cache_dir):
    """Download datasets by id (or those a recipe needs), verify size and SHA-256, cache them."""
    reg = load_registry()
    entries = []
    if recipe:
        entries.extend(_load(recipe).datasets())
    for i in ids:
        try:
            entries.append(reg.get(i))
        except KeyError:
            raise CommandError(f"Unknown dataset {i!r} (registry: {', '.join(e.id for e in reg.entries)})", 1)
    if not entries:
        raise click.UsageError("Name at least one dataset id or use --recipe.")
    for e in entries:
        if e.kind != "download":
            click.echo(f"{e.id}: {e.kind} dataset, nothing to fetch")
            continue
        try:
            path, downloaded = fetch(e, cache_dir=cache_dir)
        except DatasetError as exc:
            raise CommandError(str(exc), exc.exit_code)
        if downloaded:
            what = "content SHA-256" if e.content_sha256 and not e.sha256 else "SHA-256"
            n = f"{len(e.files)} files, " if e.files else ""
            click.echo(f"Fetched {e.id} ({n}{e.size:,} bytes, {what} verified): {path}")
        else:
            click.echo(f"{e.id}: already cached and verified: {path}")
        click.echo(f"  Citation: {e.citation}" + (f" https://doi.org/{e.doi}" if e.doi else ""))
        click.echo(f"  License: {e.license}")
        if e.acknowledgement:
            click.echo(f"  Acknowledgement: {e.acknowledgement}")
    click.echo(DISCLAIMER)


@dataset.command("info")
@click.argument("dataset_id")
@click.option("--cache-dir", type=click.Path(file_okay=False), help="Dataset cache root (default: per-user cache)")
def info(dataset_id, cache_dir):
    """Show a dataset's full registry entry and cache status."""
    reg = load_registry()
    try:
        e = reg.get(dataset_id)
    except KeyError:
        raise CommandError(f"Unknown dataset {dataset_id!r} (registry: {', '.join(x.id for x in reg.entries)})", 1)
    fields = [("id", e.id), ("title", e.title), ("publisher", e.publisher), ("version", e.version),
              ("kind", e.kind), ("url", e.url), ("size", _size(e) + " bytes" if e.size else ""),
              ("sha256", e.sha256), ("content sha256", e.content_sha256),
              ("files", f"{len(e.files)} (each pinned by size and SHA-256; manifest SHA-256 "
                        f"{e.files_sha256})" if e.files else ""),
              ("http only", e.http_only), ("format", e.format),
              ("variables", "; ".join(f"{k} [{v.get('units', '')}] {v.get('description', '')}".strip()
                                      for k, v in e.variables.items())),
              ("grid", json.dumps(e.grid) if e.grid else ""), ("land/ocean rule", json.dumps(e.class_rule)),
              ("license", e.license), ("citation", e.citation),
              ("doi", f"https://doi.org/{e.doi}" if e.doi else ""), ("acknowledgement", e.acknowledgement),
              ("notes", e.notes)]
    for k, v in fields:
        if v:
            click.echo(f"{k + ':':<17}{v}")
    if e.kind == "download":
        p = cached_path(e, cache_dir)
        click.echo(f"{'cache:':<17}{p} ({'cached' if is_cached(e, cache_dir) else 'not cached'})")
    click.echo(DISCLAIMER)
