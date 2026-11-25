"""``python -m maptemplates`` (maintainer only; run from ``cli/`` with ``PYTHONPATH=tools``).

Commands (specs/016-map-templates/contracts/template-file.md):

- ``generate ID [--dataset FILE] [--cache-dir DIR] [--out DIR]``: the candidate template JSON
  (no corrections, unconfirmed), its review sheet PNG and flags JSON, in ``--out`` (default
  ``<cache>/templates/``, outside the repository); exit 0, 4 when the pinned dataset is missing or
  its checksum differs.
- ``review ID [--out DIR]``: the review sheet and water flags of the committed package file with
  its corrections (no pyproj, no dataset; land-share flags come from ``generate``); exit 0.
- ``write ID [--corrections FILE] [--confirmed-on DATE] [--dataset FILE] [--cache-dir DIR]``:
  regenerates, applies the corrections (FILE, else the committed file's) and writes the package
  file ``data/templates/<id>.json``. The confirmation is set only with ``--confirmed-on``; it is
  kept while classes and locations are unchanged and cleared otherwise; exit 0, 1, 4.
- ``build ID --check [--dataset FILE] [--cache-dir DIR]``: regenerates with the committed
  corrections and compares every field but ``source.generated_on`` with the committed file;
  exit 0 "no differences", 1 with the differences listed, 4 dataset.
- ``ice-mask ID [--check] [--dataset FILE] [--cache-dir DIR]``: the template's ice regions
  ``data/templates/<id>-ice.json`` (feature 016, FR-020b; the kit's rules at the template's stud
  locations from the pinned ERSST v5 1991-2020 file, ``maptemplates/ice.py``), or with ``--check``
  a comparison with the committed file (every field but ``source.generated_on``); no pyproj.
  Exit 0 ("no differences" with ``--check``), 1 with the differences listed or a template that
  does not load, 4 dataset.
- ``kit-golden --out FILE [--cache-dir DIR | --fixtures]``: digests of every kit 31203 output
  (research R9); exit 0, or 1 when a command fails.

``generate``, ``write`` and ``build`` need pyproj (``poetry install --with maintainer``). Commands
import their modules when they run, so ``kit-golden`` needs only library modules present at commit
af3ce57 and 6038d9c and can run against a checkout of ``main``. Every command prints the disclaimer last.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from lego_image_processor.kit.source import DISCLAIMER


@click.group()
def main() -> None:
    """Map templates: generate, review, write and check templates; kit golden digests."""


@main.command("kit-golden")
@click.option("--out", "out", required=True, type=click.Path(dir_okay=False, path_type=Path),
              help="Digest file to write (JSON)")
@click.option("--cache-dir", type=click.Path(file_okay=False, path_type=Path),
              help="Dataset cache with the pinned datasets (default: the per-user cache)")
@click.option("--fixtures", is_flag=True,
              help="Build from the committed dataset fixtures (tests/fixtures/datasets)")
def kit_golden_cmd(out: Path, cache_dir, fixtures: bool) -> None:
    """Build every bundled recipe on the kit as A, B and C and digest every output."""
    if fixtures and cache_dir is not None:
        raise click.UsageError("--cache-dir and --fixtures cannot be used together")
    from maptemplates import golden

    if not out.parent.is_dir():
        raise click.UsageError(f"output directory {out.parent} does not exist")
    try:
        doc = golden.kit_golden(cache_dir=cache_dir, fixtures=fixtures)
    except golden.GoldenError as exc:
        click.echo(f"Error: {exc}", err=True)
        click.echo(DISCLAIMER, err=True)
        sys.exit(1)
    out.write_text(golden.to_text(doc), encoding="utf-8")
    n = sum(len(v["outputs"]) for v in doc["variants"])
    click.echo(f"wrote {out}: {len(doc['variants'])} variants, {n} outputs "
               f"({doc['inputs'].get('datasets', '')} datasets)")
    click.echo(DISCLAIMER)



# --- template commands ------------------------------------------------------------------------

def _fail(message: str, code: int) -> None:
    click.echo(f"Error: {message}", err=True)
    click.echo(DISCLAIMER, err=True)
    sys.exit(code)


def _spec(template_id: str):
    from maptemplates import generate

    try:
        return generate.get_spec(template_id)
    except KeyError as exc:
        raise click.BadParameter(str(exc.args[0]), param_hint="ID") from None


def _regenerate(spec, dataset_path, cache_dir):
    from maptemplates import generate

    try:
        return generate.regenerate(spec, dataset_path=dataset_path, cache_dir=cache_dir)
    except generate.ToolError as exc:
        _fail(str(exc), exc.exit_code)


def _package_path(template_id: str) -> Path:
    import lego_image_processor.templates as templates

    return Path(templates.TEMPLATE_DIR) / f"{template_id}.json"


def _out_dir(out, cache_dir) -> Path:
    if out:
        return Path(out)
    from lego_image_processor.datasets.cache import cache_root

    return cache_root(override=cache_dir) / "templates"


def _counts_line(counts) -> str:
    m = counts["modules"]
    corners = ", ".join(f"{k} {v['width']} x {v['height']}" for k, v in counts["corners"].items())
    return (f"{counts['land']:,} land, {counts['ocean']:,} ocean, {counts['margin']:,} margin; ring "
            f"{counts['ring']:,}; modules {m['full']} full, {m['partial']} partial, {m['empty']} empty; "
            f"corners {corners}")


def _flags_line(fc, land_share: bool = True) -> str:
    from maptemplates.generate import FLAG_LAND_SHARE, FLAG_WATER

    water = (f"{fc[FLAG_WATER]} {FLAG_WATER} ({fc['water groups']} groups, largest "
             f"{fc['largest water group']})")
    if not land_share:
        return water + f"; {FLAG_LAND_SHARE}: see generate (needs the dataset)"
    return f"{fc[FLAG_LAND_SHARE]} {FLAG_LAND_SHARE}; " + water


def _sheet_header(doc, flags, of: str):
    from maptemplates.review import flag_counts

    p, ds = doc["projection"], doc["source"]["dataset"]
    status = "confirmed" if doc.get("confirmation") else "unconfirmed"
    return [f"Map template review sheet: {doc['id']} ({of}, {status})",
            f"{doc['title']}: {p['proj']}; board {doc['board']['modules'][0]} x {doc['board']['modules'][1]} "
            f"modules ({doc['board']['width']} x {doc['board']['height']} studs)",
            f"Generated {doc['source']['generated_on']} from {ds['id']} {ds['version']} (SHA-256 {ds['sha256'][:12]}...)"
            f" with pyproj {doc['source']['software']['pyproj']} / PROJ {doc['source']['software']['proj']}",
            _counts_line(doc["counts"]),
            "Flags: " + _flags_line(flag_counts(flags), of == "candidate")
            + f"; corrections in the file: {len(doc['corrections'])}",
            "Rows 0-79 from the top, columns 0-127 from the left; sections A1-H5 as hung (combination A). "
            "Give corrections as row, column, new class, reason."]


_dataset_options = [
    click.option("--dataset", "dataset_path", type=click.Path(path_type=Path, dir_okay=False),
                 help="ETOPO 2022 10-arc-minute file (default: the verified cached copy; still checksum-verified)"),
    click.option("--cache-dir", type=click.Path(path_type=Path, file_okay=False),
                 help="Cache root (default: the per-user cache)"),
]


def dataset_options(f):
    for opt in reversed(_dataset_options):
        f = opt(f)
    return f


@main.command("generate")
@click.argument("template_id", metavar="ID")
@dataset_options
@click.option("--out", type=click.Path(path_type=Path, file_okay=False),
              help="Output folder (default: <cache>/templates, outside the repository)")
def generate_cmd(template_id: str, dataset_path, cache_dir, out) -> None:
    """Generate a candidate template, its review sheet and flags (outside the repository)."""
    from maptemplates import document, generate, review

    spec = _spec(template_id)
    regen = _regenerate(spec, dataset_path, cache_dir)
    cand = regen.candidate
    doc = document.normalise(generate.build_document(spec, cand, dataset=regen.dataset, software=regen.software))
    flags = generate.review_flags(cand.classes, cand.land_share)
    d = _out_dir(out, cache_dir)
    d.mkdir(parents=True, exist_ok=True)
    cand_path = d / f"{spec.id}.json"
    flags_path = d / f"{spec.id}.flags.json"
    sheet_path = d / f"{spec.id}.review.png"
    cand_path.write_text(document.to_text(doc), encoding="utf-8")
    flags_path.write_text(review.flags_text(review.flags_document(
        spec.id, flags, classes=cand.classes, lat=cand.lat, lon=cand.lon, of="candidate",
        generated_on=doc["source"]["generated_on"])), encoding="utf-8")
    review.render_sheet(sheet_path, cand.classes, flags=flags, header=_sheet_header(doc, flags, "candidate"))
    click.echo(f"candidate: {cand_path}")
    click.echo(f"review sheet: {sheet_path}")
    click.echo(f"flags: {flags_path}")
    click.echo(_counts_line(doc["counts"]))
    click.echo("flags: " + _flags_line(review.flag_counts(flags)))
    click.echo(DISCLAIMER)


@main.command("review")
@click.argument("template_id", metavar="ID")
@click.option("--out", type=click.Path(path_type=Path, file_okay=False),
              help="Output folder (default: <cache>/templates, outside the repository)")
def review_cmd(template_id: str, out) -> None:
    """Review sheet of the committed template file with its corrections (no pyproj needed)."""
    import numpy as np

    from maptemplates import document, generate, review

    spec = _spec(template_id)
    path = _package_path(spec.id)
    if not path.is_file():
        _fail(f"{path} does not exist (write it with: maptemplates write {spec.id})", 1)
    doc = document.read_document(path)
    classes = np.array([list(r) for r in doc["classes"]], dtype="U1")
    lat = np.array([[np.nan if v is None else v for v in row] for row in doc["locations"]["lat"]], dtype=float)
    lon = np.array([[np.nan if v is None else v for v in row] for row in doc["locations"]["lon"]], dtype=float)
    flags = generate.review_flags(classes)
    corrected = [(c["row"], c["col"]) for c in doc.get("corrections", [])]
    d = _out_dir(out, None)
    d.mkdir(parents=True, exist_ok=True)
    sheet_path = d / f"{spec.id}.committed-review.png"
    flags_path = d / f"{spec.id}.committed-flags.json"
    flags_path.write_text(review.flags_text(review.flags_document(
        spec.id, flags, classes=classes, lat=lat, lon=lon, of="committed file",
        generated_on=doc["source"]["generated_on"], extra={"corrections": len(corrected)})), encoding="utf-8")
    review.render_sheet(sheet_path, classes, flags=flags, corrected=corrected,
                        header=_sheet_header(doc, flags, "committed file"))
    click.echo(f"review sheet: {sheet_path}")
    click.echo(f"flags: {flags_path}")
    click.echo(_counts_line(doc["counts"]))
    click.echo(f"corrections: {len(corrected)}; flags: " + _flags_line(review.flag_counts(flags), False))
    click.echo(DISCLAIMER)


def _confirmed_on(ctx, param, value: Optional[str]):
    if value is None:
        return None
    from maptemplates import document

    try:
        document.confirmation(value)
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from None
    return value


@main.command("write")
@click.argument("template_id", metavar="ID")
@click.option("--corrections", "corrections_path", type=click.Path(path_type=Path, dir_okay=False, exists=True),
              help="Corrections JSON: a list of {row, col, class, reason} (default: the committed file's)")
@click.option("--confirmed-on", callback=_confirmed_on, metavar="YYYY-MM-DD",
              help="Record the owner's confirmation (role \"project owner\" and this date)")
@dataset_options
def write_cmd(template_id: str, corrections_path, confirmed_on, dataset_path, cache_dir) -> None:
    """Regenerate, apply corrections and write the package template file."""
    from lego_image_processor.templates import TemplateError, parse_template
    from maptemplates import document, generate

    spec = _spec(template_id)
    path = _package_path(spec.id)
    committed = document.read_document(path) if path.is_file() else None
    try:
        corrections = (document.read_corrections(corrections_path) if corrections_path
                       else list((committed or {}).get("corrections", [])))
    except document.CorrectionError as exc:
        _fail(str(exc), 1)
    regen = _regenerate(spec, dataset_path, cache_dir)
    try:
        doc = document.normalise(generate.build_document(spec, regen.candidate, dataset=regen.dataset,
                                                         software=regen.software, corrections=corrections))
    except document.CorrectionError as exc:
        _fail(str(exc), 1)
    doc["confirmation"] = document.resolve_confirmation(doc, committed, confirmed_on)
    if committed is not None and committed.get("source", {}).get("generated_on") and \
            not document.differences(committed, doc):
        doc["source"]["generated_on"] = committed["source"]["generated_on"]   # nothing changed
    try:
        t = parse_template(doc, path.name)
    except TemplateError as exc:
        _fail(f"the written file would not load: {exc}", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document.to_text(doc), encoding="utf-8")
    click.echo(f"wrote {path}")
    click.echo(_counts_line(doc["counts"]))
    click.echo(f"corrections: {len(doc['corrections'])}; layout SHA-256 {t.layout_sha256}")
    if doc["confirmation"]:
        click.echo(f"confirmation: {doc['confirmation']['role']}, {doc['confirmation']['date']}")
    elif committed and committed.get("confirmation"):
        click.echo("confirmation cleared: classes or locations changed (confirm again with --confirmed-on)")
    else:
        click.echo("unconfirmed: maps cannot be built on it until the owner confirms (--confirmed-on)")
    ice = path.with_name(f"{spec.id}-ice.json")
    if ice.is_file():
        import json

        recorded = json.loads(ice.read_text(encoding="utf-8")).get("source", {}).get("template_layout_sha256")
        if recorded != t.layout_sha256:
            click.echo(f"note: {ice.name} records another layout; regenerate it with: maptemplates ice-mask {spec.id}")
    click.echo(DISCLAIMER)


@main.command("build")
@click.argument("template_id", metavar="ID")
@click.option("--check", is_flag=True, help="Regenerate and compare with the committed file; write nothing")
@dataset_options
def build_cmd(template_id: str, check: bool, dataset_path, cache_dir) -> None:
    """Check that the committed template file is reproducible (build ID --check)."""
    from maptemplates import document, generate

    if not check:
        raise click.UsageError("build only checks (build ID --check); use write to write the file")
    spec = _spec(template_id)
    path = _package_path(spec.id)
    if not path.is_file():
        _fail(f"difference: {path} does not exist", 1)
    committed = document.read_document(path)
    regen = _regenerate(spec, dataset_path, cache_dir)
    try:
        doc = document.normalise(generate.build_document(
            spec, regen.candidate, dataset=regen.dataset, software=regen.software,
            generated_on=committed.get("source", {}).get("generated_on"),
            corrections=list(committed.get("corrections") or [])))
        doc["confirmation"] = document.resolve_confirmation(doc, committed, None)
    except (document.CorrectionError, ValueError) as exc:
        _fail(f"difference: {exc}", 1)
    diffs = document.differences(committed, doc)
    if diffs:
        limit = 50
        for line in diffs[:limit]:
            click.echo(f"difference: {line}", err=True)
        if len(diffs) > limit:
            click.echo(f"... and {len(diffs) - limit} more differences", err=True)
        click.echo(f"{len(diffs)} difference{'' if len(diffs) == 1 else 's'}", err=True)
        click.echo(DISCLAIMER, err=True)
        sys.exit(1)
    click.echo("no differences")
    click.echo(DISCLAIMER)


def _ice_template(template_id: str):
    """The template ``ice-mask`` works on: any template file but the kit's (usage error otherwise)."""
    from lego_image_processor.templates import KIT_TEMPLATE_ID, TemplateError, load_template, template_ids

    if template_id == KIT_TEMPLATE_ID:
        raise click.BadParameter("the kit's ice regions are kit_31203_ice.json; make them with: "
                                 "PYTHONPATH=tools python -m kit31203 ice-mask", param_hint="ID")
    known = [i for i in template_ids() if i != KIT_TEMPLATE_ID]
    if template_id not in known:
        raise click.BadParameter(f"unknown template {template_id!r}; templates: {', '.join(known) or 'none'}",
                                 param_hint="ID")
    try:
        return load_template(template_id)
    except TemplateError as exc:
        _fail(f"template {template_id}: {exc}", 1)


@main.command("ice-mask")
@click.argument("template_id", metavar="ID")
@click.option("--check", is_flag=True, help="Compare with the committed <ID>-ice.json; write nothing")
@click.option("--dataset", "dataset_path", type=click.Path(path_type=Path, dir_okay=False),
              help="ERSST v5 1991-2020 long-term monthly means (default: the verified cached copy; "
                   "still checksum-verified)")
@click.option("--cache-dir", type=click.Path(path_type=Path, file_okay=False),
              help="Cache root (default: the per-user cache)")
def ice_mask_cmd(template_id: str, check: bool, dataset_path, cache_dir) -> None:
    """Derive the template's land-ice and sea-ice studs and write data/templates/<ID>-ice.json."""
    import datetime as _dt
    import json

    from lego_image_processor.datasets import get_entry
    from lego_image_processor.maps.ice import SEA_ICE_RULE
    from maptemplates import document, generate, ice

    t = _ice_template(template_id)
    entry = get_entry(SEA_ICE_RULE["dataset"])
    try:
        warmest = ice.read_warmest(entry, dataset_path, cache_dir)
    except generate.ToolError as exc:
        _fail(str(exc), exc.exit_code)
    regions = ice.derive(t, warmest)
    path = ice.ice_path(t)
    committed = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    today = _dt.date.today().isoformat()
    doc = ice.ice_document(t, regions, ice.source_block(t, entry, today))
    doc["source"]["generated_on"] = ice.generated_on(committed, doc, today)
    click.echo(f"land ice: {int(regions.land.sum()):,} studs; sea ice: {int(regions.sea.sum()):,} studs "
               f"(template {t.id}, {t.status}, layout SHA-256 {t.layout_sha256})")
    if check:
        if committed is None:
            _fail(f"difference: {path} does not exist (write it with: maptemplates ice-mask {t.id})", 1)
        diffs = ice.differences(committed, doc)
        if diffs:
            for line in diffs:
                click.echo(f"difference: {line}", err=True)
            click.echo(f"{len(diffs)} difference{'' if len(diffs) == 1 else 's'}", err=True)
            click.echo(DISCLAIMER, err=True)
            sys.exit(1)
        click.echo("no differences")
        click.echo(DISCLAIMER)
        return
    path.write_text(document.ice_to_text(doc), encoding="utf-8")
    click.echo(f"wrote {path}")
    click.echo(DISCLAIMER)


if __name__ == "__main__":
    main()
