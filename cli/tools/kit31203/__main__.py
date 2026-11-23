"""Command line entry point: ``python -m kit31203``.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Callable, NamedTuple

# Make ``cli/tools`` importable when run as ``python -m kit31203`` from anywhere.
_TOOLS_DIR = str(Path(__file__).resolve().parent.parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import click  # noqa: E402

from kit31203 import assemble, classify, inventory, sections, source  # noqa: E402
from lego_image_processor.kit.design import parse_design  # noqa: E402
from lego_image_processor.kit.colors import KIT_COLORS_PATH, load_kit_color_table  # noqa: E402
from lego_image_processor.kit.inventory import parse_inventory  # noqa: E402
from lego_image_processor.kit.source import (  # noqa: E402
    DISCLAIMER, PINNED_SHA256, PINNED_URL, SOURCE_TITLE,
)

DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "src" / "lego_image_processor" / "data"
INVENTORY_FILE = "kit_31203_inventory.json"
GENERATOR = "cli/tools/kit31203 extract"
OVERRIDES_PATH = classify.OVERRIDES_PATH


class StageError(Exception):
    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


STAGE_ERRORS = (source.SourceError, inventory.PairingError, StageError, sections.SectionsError,
                sections.PlacementError, classify.ClassificationError, assemble.SupplyError)


def _source_block(pages, generated_on, citations):
    return {
        "title": SOURCE_TITLE, "url": PINNED_URL, "sha256": PINNED_SHA256, "pages": list(pages),
        "generator": GENERATOR, "generated_on": generated_on, "citations": citations,
        "disclaimer": DISCLAIMER,
    }


def build_inventory_document(words, generated_on: str, catalog=None, colors_table=None) -> dict:
    """Inventory stage (pure apart from reading the curated files): words -> inventory JSON."""
    catalog = catalog or inventory.load_part_catalog()
    colors_table = colors_table or load_kit_color_table(KIT_COLORS_PATH)
    pairs = inventory.pair_words(words)
    color_keys = {(c.role, c.lego.name): c.key for c in colors_table.colors}
    elements = inventory.join_catalog(pairs, catalog, color_keys)
    doc = {
        "format_version": "1",
        "kit_id": "31203",
        "source": _source_block([inventory.SOURCE_PAGE], generated_on, catalog["citations"]),
        "totals": {"lines": len(elements), "pieces": sum(e["quantity"] for e in elements)},
        "elements": elements,
    }
    try:
        parse_inventory(doc, INVENTORY_FILE)  # library rules + agreement with kit_colors.json
    except ValueError as exc:
        raise StageError(f"inventory failed validation: {exc}", 9) from exc
    return doc


class PdfInputs(NamedTuple):
    words: list                 # page-159 words (x, y, text)
    placements: dict            # page -> image placements
    load_image: Callable        # placement -> RGB PIL image


def read_pdf_inputs(pdf, cache_dir) -> PdfInputs:
    """Resolve and verify the PDF, then read everything the stages need from it."""
    from kit31203 import pdf_adapter  # needs pypdf (maintainer group)

    pdf_path = source.resolve_pdf(pdf=pdf, cache_dir=cache_dir)
    doc = pdf_adapter.open_pdf(pdf_path)
    n_pages = len(doc.pages)
    placements = {p: pdf_adapter.image_placements(doc, p) for p in sections.SECTION_PAGES
                  if p <= n_pages}
    return PdfInputs(words=pdf_adapter.page_words(doc, inventory.SOURCE_PAGE),
                     placements=placements,
                     load_image=lambda placement: pdf_adapter.load_image(doc, placement))


def classify_sections(inputs: PdfInputs):
    """Stages 3-4a: sections, cell samples and automatic classification (no overrides)."""
    records = sections.map_sections(inputs.placements)
    found = sections.find_section_images(inputs.placements)
    images, cells = {}, {}
    for rec in records:
        img = inputs.load_image(found[rec["page"]])
        if [img.width, img.height] != rec["image_size"]:
            raise StageError(f"page {rec['page']}: decoded image is {img.width}x{img.height}, "
                             f"placement says {rec['image_size']}", 5)
        slot = (rec["col"], rec["row"])
        images[slot] = img
        cells[slot] = classify.sample_cells(img)
    keys, refs = classify.load_reference_colors()
    palette = [c.key for c in load_kit_color_table(KIT_COLORS_PATH).colors]
    if list(keys) != palette:
        raise StageError("reference_colors.json must list the kit colours in kit_colors.json order", 7)
    result = classify.classify(assemble.place_sections(cells), keys, refs)
    return records, images, result


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def build_outputs(inputs: PdfInputs, generated_on: str, out_dir: Path) -> dict:
    """All stages after the PDF is read; returns {filename: document}. Nothing is written."""
    inv = build_inventory_document(inputs.words, generated_on)
    records, _, result = classify_sections(inputs)
    grid, applied = classify.apply_overrides(result, classify.load_overrides(OVERRIDES_PATH))
    palette = list(result.keys)
    supplied = {k: sum(e["quantity"] for e in inv["elements"] if e["color_key"] == k) for k in palette}
    counts = assemble.color_counts(grid, palette, supplied)
    assemble.check_supply(counts)

    src = _source_block(sections.SECTION_PAGES, generated_on, [])
    flagged = int(result.flagged.sum())
    resolved = sum(1 for o in applied if result.flagged[o["y"], o["x"]])
    classification = {
        "method": classify.METHOD,
        "ambiguity_ratio_threshold": result.ratio_threshold,
        "max_delta_e00": result.max_delta_e,
        "flagged": flagged, "resolved": resolved,
    }
    design = assemble.build_design(src, palette, grid, records, classification, applied, counts)
    try:
        parse_design(json.loads(assemble.dump_json(design)), assemble.DESIGN_FILE)
    except ValueError as exc:
        raise StageError(f"design failed validation: {exc}", 7) from exc

    mask = assemble.build_mask(grid, palette, src)
    out_dir = Path(out_dir)
    prev_path = out_dir / assemble.MASK_FILE
    if not prev_path.is_file():
        prev_path = DEFAULT_OUT_DIR / assemble.MASK_FILE
    previous = _read_json(prev_path) or {"land_coordinates": []}
    prev_sha = source.sha256_file(prev_path) if prev_path.is_file() else "0" * 64
    prev_record = _read_json(out_dir / assemble.CHANGES_FILE)
    changes = assemble.build_change_record(previous, prev_sha, mask, src, prev_record)
    return {INVENTORY_FILE: inv, assemble.DESIGN_FILE: design, assemble.MASK_FILE: mask,
            assemble.CHANGES_FILE: changes}


def run_extract(pdf, cache_dir, out_dir: Path, generated_on: str) -> dict:
    """All stages; returns {filename: document}. Nothing is written here."""
    return build_outputs(read_pdf_inputs(pdf, cache_dir), generated_on, out_dir)


def _summary(outputs: dict) -> list:
    inv = outputs[INVENTORY_FILE]
    lines = [f"Inventory: {inv['totals']['lines']} lines, {inv['totals']['pieces']:,} pieces "
             f"(page {inventory.SOURCE_PAGE})"]
    for role in ("land", "ocean", "section_base", "frame_other"):
        rows = [e for e in inv["elements"] if e["role"] == role]
        lines.append(f"  {role}: {len(rows)} lines, {sum(e['quantity'] for e in rows):,} pieces")
    design = outputs.get(assemble.DESIGN_FILE)
    if design:
        secs = design["sections"]
        lines.append(f"Sections: {len(secs)} (order check passed for "
                     f"{sum(1 for s in secs if s['order_check'])})")
        cl = design["classification"]
        lines.append(f"Classification: flagged {cl['flagged']}, resolved {cl['resolved']}; "
                     f"{len(design['overrides'])} overrides applied")
        lines.append(f"  {'color':32s} {'used':>5s} {'supplied':>8s} {'spare':>5s}")
        for c in design["counts"]:
            lines.append(f"  {c['key']:32s} {c['used']:5d} {c['supplied']:8d} {c['spare']:5d}")
        mask = outputs[assemble.MASK_FILE]
        rec = outputs[assemble.CHANGES_FILE]
        lines.append(f"Mask: {mask['land_positions']} land, {mask['ocean_positions']} ocean; "
                     f"{rec['count']} changes vs previous mask")
    return lines


@click.group()
def main() -> None:
    """Extract kit 31203 reference data from the pinned instructions PDF."""


@main.command()
@click.option("--pdf", type=click.Path(path_type=Path), help="Local copy of the pinned PDF (still checksum-verified).")
@click.option("--cache-dir", type=click.Path(path_type=Path), help="Cache root (default: per-user cache).")
@click.option("--out-dir", type=click.Path(path_type=Path), default=DEFAULT_OUT_DIR, show_default=True)
@click.option("--date", "generated_on", default=None, help="generated_on date, YYYY-MM-DD (default: today).")
@click.option("--check", is_flag=True, help="Regenerate to a temp dir and diff with --out-dir (ignores generated_on).")
@click.option("--report", type=click.Path(path_type=Path), help="Also write the summary to this file.")
def extract(pdf, cache_dir, out_dir, generated_on, check, report) -> None:
    """Extract reference data; writes outputs only if every step passes."""
    generated_on = generated_on or _dt.date.today().isoformat()
    try:
        _dt.date.fromisoformat(generated_on)
    except ValueError:
        raise click.UsageError("--date must be YYYY-MM-DD")
    try:
        outputs = run_extract(pdf, cache_dir, out_dir, generated_on)
    except STAGE_ERRORS as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(exc.exit_code)

    summary = _summary(outputs)
    if check:
        diffs = []
        for name, doc in outputs.items():
            path = Path(out_dir) / name
            if not path.exists():
                diffs.append(f"{name}: missing in {out_dir}")
                continue
            committed = json.loads(path.read_text(encoding="utf-8"))
            for d in assemble.json_differences(committed, json.loads(assemble.dump_json(doc)))[:20]:
                diffs.append(f"{name}: {d}")
        if diffs:
            click.echo("Differences found:", err=True)
            for d in diffs:
                click.echo(f"  {d}", err=True)
            sys.exit(1)
        summary.append("Check: no differences")
    else:
        with assemble.AtomicWriter(out_dir) as w:
            for name, doc in outputs.items():
                w.write_json(name, doc)
        summary += [f"Wrote {p}" for p in w.written]
    summary.append(DISCLAIMER)
    for line in summary:
        click.echo(line)
    if report:
        Path(report).write_text("\n".join(summary) + "\n", encoding="utf-8")


@main.command()
@click.option("--pdf", type=click.Path(path_type=Path), help="Local copy of the pinned PDF (still checksum-verified).")
@click.option("--cache-dir", type=click.Path(path_type=Path), help="Cache root (default: per-user cache).")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="Review sheet PNG (default: <cache>/review/kit31203-review.png, outside the repository).")
def review(pdf, cache_dir, out) -> None:
    """Write a review sheet of ambiguous positions and an overrides.json stub.

    The sheet contains LEGO artwork: never commit it.
    """
    from kit31203 import review as review_sheet

    try:
        inputs = read_pdf_inputs(pdf, cache_dir)
        records, images, result = classify_sections(inputs)
    except STAGE_ERRORS as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(exc.exit_code)
    out = Path(out) if out else (Path(cache_dir) if cache_dir else source.cache_root()) / "review" / "kit31203-review.png"
    existing = {(o["x"], o["y"]): o for o in classify.load_overrides(OVERRIDES_PATH)}
    sheet, stub = review_sheet.write_review(result, images, out, existing)
    flagged = result.flagged_positions()
    click.echo(f"Ambiguous positions: {len(flagged)} "
               f"({sum(1 for p in flagged if p in existing)} already in overrides.json)")
    click.echo(f"Review sheet: {sheet} (contains LEGO artwork; do not commit)")
    click.echo(f"Overrides stub: {stub}")
    click.echo(DISCLAIMER)


@main.command("fit-projection")
@click.option("--dataset", "dataset_path", type=click.Path(path_type=Path, dir_okay=False),
              help="ETOPO 2022 10-arc-minute DODS file (default: the verified cached copy)")
@click.option("--cache-dir", type=click.Path(path_type=Path), help="Cache root (default: per-user cache).")
@click.option("--check", is_flag=True, help="Compare the fit with the committed projection; write nothing.")
@click.option("--date", "generated_on", default=None, help="generated_on date, YYYY-MM-DD (default: today).")
def fit_projection(dataset_path, cache_dir, check, generated_on) -> None:
    """Fit the kit grid's projection to the kit mask and write kit_31203_projection.json."""
    import numpy as np

    from kit31203 import projection_fit
    from lego_image_processor.datasets import get_entry, read_dataset, resolve, verify
    from lego_image_processor.datasets.cache import DatasetError
    from lego_image_processor.maps.build import land_mask_array
    from lego_image_processor.maps.projection import PROJECTION_PATH

    entry = get_entry("etopo2022-surface-10m")
    try:
        if dataset_path:
            verify(entry, dataset_path)
            path = dataset_path
        else:
            path = resolve(entry, cache_dir)
    except DatasetError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(getattr(exc, "exit_code", 1))
    g = read_dataset(entry, path, "z")
    result = projection_fit.fit(g.values, g.lat, g.lon, land_mask_array())
    committed = json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))
    for m, f in result["fits"].items():
        click.echo(f"{m:16s} equator row {f['equator_row']:5.1f}  scale {f['scale']:5.1f}  agreement {f['agreement']:.3f}")
    click.echo(f"left edge {result['left_edge_lon']} (column correlation {result['column_correlation']})")
    keys = ("model", "left_edge_lon", "deg_per_col", "equator_row", "rows_per_radian", "agreement")
    if check:
        diffs = [k for k in keys if committed.get(k) != result[k]]
        if diffs:
            for k in diffs:
                click.echo(f"difference: {k}: committed {committed.get(k)} fitted {result[k]}", err=True)
            sys.exit(1)
        click.echo("no differences")
        click.echo(DISCLAIMER)
        return
    out = dict(committed)
    out.update({k: result[k] for k in keys})
    out["source"] = dict(committed.get("source", {}))
    out["source"]["generated_on"] = generated_on or _dt.date.today().isoformat()
    out["source"]["dataset"] = {"id": entry.id, "sha256": entry.sha256}
    PROJECTION_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    click.echo(f"Wrote {PROJECTION_PATH}")
    click.echo(DISCLAIMER)


@main.command("ice-mask")
@click.option("--dataset", "dataset_path", type=click.Path(path_type=Path, dir_okay=False),
              help="ERSST v5 1991-2020 long-term monthly means (default: the verified cached copy)")
@click.option("--cache-dir", type=click.Path(path_type=Path), help="Cache root (default: per-user cache).")
@click.option("--check", is_flag=True, help="Compare with the committed kit_31203_ice.json; write nothing.")
@click.option("--date", "generated_on", default=None, help="generated_on date, YYYY-MM-DD (default: today).")
def ice_mask(dataset_path, cache_dir, check, generated_on) -> None:
    """Derive the land-ice and sea-ice cells (feature 012) and write kit_31203_ice.json."""
    from lego_image_processor.datasets import get_entry, resolve, verify
    from lego_image_processor.datasets.cache import DatasetError
    from lego_image_processor.datasets.readers import read_netcdf3
    from lego_image_processor.maps.ice import (ICE_PATH, LAND_ICE_REGIONS, SEA_ICE_RULE,
                                               derive_ice_regions, ice_document)

    entry = get_entry(SEA_ICE_RULE["dataset"])
    try:
        if dataset_path:
            verify(entry, dataset_path)
            path = dataset_path
        else:
            path = resolve(entry, cache_dir)
    except DatasetError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(getattr(exc, "exit_code", 1))
    grid = read_netcdf3(path, SEA_ICE_RULE["variable"], reduce=SEA_ICE_RULE["reduce"])
    ice = derive_ice_regions(grid)
    click.echo(f"land ice: {int(ice.land.sum())} cells; sea ice: {int(ice.sea.sum())} cells")
    committed = json.loads(ICE_PATH.read_text(encoding="utf-8")) if ICE_PATH.exists() else None
    source = {
        "title": "Ice-covered cells of the kit 31203 grid (palette chooser, feature 012)",
        "generator": "cli/tools/kit31203 ice-mask",
        "generated_on": generated_on or (committed or {}).get("source", {}).get("generated_on")
        or _dt.date.today().isoformat(),
        "land_ice": {"rule": "land cells whose centre lies in a region (strict bounds, minus "
                             "excluded boxes); the regions of the 013-rainfall design",
                     "regions": [dict(r) for r in LAND_ICE_REGIONS],
                     "mask": "lego_world_map_land_sea_mask.json",
                     "projection": "kit_31203_projection.json"},
        "sea_ice": {"rule": "ocean cells whose 1991-2020 warmest-month mean SST (cell mean of the "
                            "ERSST v5 values, as maps reproject) is at or below max_value, or "
                            "with no ERSST value and a centre poleward of unobserved_lat",
                    **{k: SEA_ICE_RULE[k] for k in ("variable", "reduce", "max_value", "unobserved_lat")},
                    "dataset": {"id": entry.id, "version": entry.version, "url": entry.url,
                                "sha256": entry.sha256, "citation": entry.citation,
                                "license": entry.license}},
        "disclaimer": DISCLAIMER,
    }
    doc = ice_document(ice, source)
    if check:
        if committed is None:
            click.echo(f"difference: {ICE_PATH} does not exist", err=True)
            sys.exit(1)
        diffs = [k for k in ("land_ice", "sea_ice") if committed.get(k) != doc[k]]
        diffs += [f"source.{k}" for k in ("land_ice", "sea_ice")
                  if committed.get("source", {}).get(k) != source[k]]
        if diffs:
            for k in diffs:
                click.echo(f"difference: {k}", err=True)
            sys.exit(1)
        click.echo("no differences")
        click.echo(DISCLAIMER)
        return
    ICE_PATH.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    click.echo(f"Wrote {ICE_PATH}")
    click.echo(DISCLAIMER)


if __name__ == "__main__":
    main()
