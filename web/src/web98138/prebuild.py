"""Build step: every map x combination and every download, with a manifest (FR-014-FR-016).

Run ``python -m web98138.prebuild --out DIR [--fetch] [--prices FILE | --no-prices]
[--allow-partial-prices] [--templates LIST|none]``. It calls the same library functions as the CLI
commands ``map build``, ``map cells`` (feature 015), ``parts list``, ``parts export``, ``parts
estimate``, ``sheets build`` and ``map stickers`` (feature 017); nothing here computes a map, a
parts list, a price, a sheet or a sticker itself (constitution VI). Each map gets one sticker set,
from the build in the recipe's default combination, under ``maps/<map>/stickers/kit-31203/`` (the
kit template's id). Only ``--fetch`` uses the network,
to download missing pinned datasets (verified by SHA-256); prices come from a committed snapshot
file (feature 011), never from the network.

Template variants (feature 016, contracts/web.md): besides the kit's combinations A, B and C, each
map is built on every confirmed template the site offers (``TEMPLATES``; ``--templates`` narrows
the list, ``none`` builds kit variants only) when the library's ``templates.compatibility`` allows
it, into ``maps/<map>/<template-id>/`` with the same files. An unconfirmed template gives no
variants (constitution Principle I); the build says why. Kit variants are built exactly as before.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from . import COMBINATIONS, DISCLAIMER, MAP_IDS, TEMPLATES, __version__

FORMAT_VERSION = "1"

# kind -> (file name, media type, description). The order is the order shown on the page.
KINDS: Dict[str, tuple] = {
    "preview": ("preview.png", "image/png", "Preview, round studs on black, 10 px per stud"),
    "thumb": ("thumb.png", "image/png", "Thumbnail, square studs, 3 px per stud"),
    "sheets-letter": ("sheets-letter.pdf", "application/pdf",
                      "Build sheets, US Letter: overview, legend and 40 section pages at true scale"),
    "sheets-a4": ("sheets-a4.pdf", "application/pdf",
                  "Build sheets, A4: overview, legend and 40 section pages at true scale"),
    "parts": ("parts.json", "application/json", "Parts list: every piece, with cited IDs"),
    "bricklink": ("bricklink.xml", "application/xml", "BrickLink wanted list: every piece"),
    "rebrickable": ("rebrickable.csv", "text/csv; charset=utf-8",
                    "Rebrickable parts CSV: every piece"),
    "parts-1kit": ("parts-1kit.json", "application/json",
                   "Parts list topped up from one 31203 kit"),
    "bricklink-1kit": ("bricklink-1kit.xml", "application/xml",
                       "BrickLink wanted list: pieces to buy on top of one kit"),
    "rebrickable-1kit": ("rebrickable-1kit.csv", "text/csv; charset=utf-8",
                         "Rebrickable parts CSV: pieces to buy on top of one kit"),
    "layout": ("layout.json", "application/json", "Layout: all 10,240 positions (schema 2.0)"),
    # feature 015: the palette chooser's data (served for the map page, not a download)
    "cells": ("cells.json", "application/json",
              "Per-cell classes, values, shadow and ice regions for the palette chooser"),
}
PREVIEW_SCALE = 10
THUMB_SCALE = 3
# feature 016: descriptions that differ on a template variant (its margin is square tiles)
TEMPLATE_DESCRIPTIONS = {
    "preview": "Preview, round studs on black and square tiles in the margin, 10 px per stud",
}
TEMPLATE_STUD_COUNTS = ("land", "ocean", "margin", "ring")

# feature 017: one sticker set per map (contracts/web.md), under the kit template's id
# (lego_image_processor.templates.KIT_TEMPLATE_ID, feature 016). kind -> (file name, media type,
# description); the SVG descriptions get the sticker's cut size.
STICKER_KINDS: Dict[str, tuple] = {
    "stickers-letter": ("stickers-letter.pdf", "application/pdf",
                        "Sticker print sheet, US Letter: both stickers at true size"),
    "stickers-a4": ("stickers-a4.pdf", "application/pdf",
                    "Sticker print sheet, A4: both stickers at true size"),
    "sticker-small": ("sticker-small.svg", "image/svg+xml", "Small sticker (SVG, {w} x {h} mm)"),
    "sticker-large": ("sticker-large.svg", "image/svg+xml", "Large sticker (SVG, {w} x {h} mm)"),
}


class PrebuildError(RuntimeError):
    """A build that cannot complete (missing dataset, price snapshot, library error)."""


NO_PACKAGED_SNAPSHOT = ("no price snapshot is packaged (lego_image_processor/data/"
                        "bricklink_price_guide.json); run `parts prices fetch` and commit it, or "
                        "build with --no-prices")


def load_prices(prices_path=None, *, allow_partial: bool = False):
    """The price snapshot for the build (feature 011): packaged by default, or ``prices_path``."""
    from lego_image_processor.prices import SnapshotError, SnapshotMissingError, load_snapshot

    try:
        snap = load_snapshot(prices_path)
    except SnapshotMissingError as exc:
        raise PrebuildError(NO_PACKAGED_SNAPSHOT) from exc
    except SnapshotError as exc:
        raise PrebuildError(str(exc)) from exc
    if not snap.complete and not allow_partial:
        raise PrebuildError(f"price snapshot {snap.file_name} is partial ({len(snap.lots)} of "
                            f"{snap.lot_set['count']} lots); run `parts prices fetch --resume` "
                            "to finish it, or build with --allow-partial-prices")
    return snap


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_commit() -> Optional[str]:
    env = os.environ.get("GIT_COMMIT")
    if env:
        return env.strip() or None
    head = Path(__file__).resolve().parents[3] / ".git" / "HEAD"
    try:
        ref = head.read_text().strip()
        if ref.startswith("ref: "):
            return (head.parent / ref[5:]).read_text().strip()
        return ref
    except OSError:
        return None


def _parse_list(value: Optional[str], allowed: Sequence[str], what: str, upper: bool = False) -> List[str]:
    if value is None:
        return list(allowed)
    items = [v.strip() for v in value.split(",") if v.strip()]
    if upper:
        items = [v.upper() for v in items]
    bad = [v for v in items if v not in allowed]
    if bad or not items:
        raise ValueError(f"unknown {what} {', '.join(bad) or '(none)'}; use {', '.join(allowed)}")
    return [v for v in allowed if v in items]


def _arrangements() -> Dict[str, Any]:
    from lego_image_processor.layout.arrangement import load_arrangements

    data = load_arrangements()
    names = {f.number: f.name for f in data.frames}
    rows = []
    for a in data.arrangements:
        order = "·".join(str(n) for n in a.frame_order)
        rows.append({"id": a.id, "name": a.name, "centre": a.centre,
                     "frame_order": list(a.frame_order), "column_shift": a.column_shift,
                     "frames": [names[n] for n in a.frame_order],
                     "description": f"frames {order}, {a.centre} in the centre"})
    src = data.source
    return {"arrangements": rows,
            "frames": [{"number": f.number, "name": f.name} for f in data.frames],
            "arrangement_source": {k: src[k] for k in ("title", "url", "pages", "citation")}}


def _part_labels(rows: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    """Labels of the parts the built variants' lots and leftovers use, in the parts list's part
    order: a kit-only site lists exactly 6141 and 98138; the square tile 3070b appears only when a
    variant has margin tiles (feature 016, data-model.md Manifest.part_labels)."""
    from lego_image_processor.parts.partslist import PART_TYPE
    from lego_image_processor.sheets.legend import PART_LABEL

    used = {r["part_id"] for m in rows for v in _all_variants(m)
            for r in list(v.get("lots") or ()) + list(v.get("leftovers") or ())}
    return {part_id: PART_LABEL[t] for part_id, t in PART_TYPE.items() if part_id in used}


def _all_variants(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """A map row's kit variants, then its template variants (feature 016)."""
    return list(row["variants"].values()) + list(row.get("template_variants", {}).values())


def template_reason(recipe, template) -> Optional[str]:
    """None when the site builds ``recipe`` on ``template``, else why not: the library's
    ``templates.compatibility`` decides (feature 016, research R19); arrangement A, the only one a
    curved map has, unless the recipe names another."""
    from lego_image_processor.templates import compatibility

    return compatibility(recipe, template)


def select_templates(names: Optional[Iterable[str]] = None):
    """The templates to build variants on, and notes on those left out (feature 016).

    ``names`` None means every template in ``TEMPLATES``; an empty list means none. A template that
    is not confirmed by the project owner gives no variants (Principle I) and a note says so; a
    template file that fails its checks is a ``PrebuildError``."""
    from lego_image_processor.templates import TemplateError, UnknownTemplateError, confirmed_text, load_template

    chosen, notes = [], []
    for tid in (list(TEMPLATES) if names is None else list(names)):
        try:
            tpl = load_template(tid)
        except UnknownTemplateError:
            notes.append(f"{tid}: no template file, so no template variants are built")
            continue
        except TemplateError as exc:
            raise PrebuildError(f"template {tid}: {exc}") from exc
        if not tpl.buildable:
            notes.append(f"{tid}: not confirmed by the project owner, so no template variants are built "
                         f"(confirmed templates: {confirmed_text()})")
            continue
        chosen.append(tpl)
    return chosen, notes


def _template_record(tpl) -> Dict[str, Any]:
    """The manifest's ``templates`` entry for a template the site built on (contracts/web.md)."""
    board = tpl.board
    return {"id": tpl.id, "title": tpl.title, "projection": TEMPLATES.get(tpl.id, tpl.title),
            "board": {"modules": list(board["modules"]), "width": tpl.width, "height": tpl.height},
            "counts": {k: int(tpl.counts[k]) for k in TEMPLATE_STUD_COUNTS},
            "rehang": len(tpl.arrangements) > 1, "description": tpl.description,
            "source": {"sha256": tpl.file_sha256,
                       "confirmation": None if tpl.confirmation is None else tpl.confirmation.to_dict()}}


def _citations(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    keep = ("id", "version", "title", "publisher", "citation", "license", "doi", "acknowledgement",
            "url")
    return [{k: c[k] for k in keep if c.get(k)} for c in report["citations"]]


def _layers(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for layer in report["layers"]:
        ds = layer.get("dataset")
        out.append({"class": layer["class"], "role": layer["role"], "part_id": layer["part_id"],
                    "cells": layer["cells"], "classification": layer.get("classification"),
                    "dataset": ds["id"] if ds else None})
    return out


def build_variant(recipe, combination: str, out: Path, rel: str, *, cache_dir=None,
                  prices=None, today: Optional[date] = None, template=None) -> Dict[str, Any]:
    """Write one variant's files with the library; return its manifest entry.

    With ``prices`` (a loaded snapshot), the entry has ``estimates`` from the same two parts
    lists as the downloads, and ``_prices`` (the manifest's top-level block). ``_report`` and
    ``_result`` (the ``MapResult``, feature 017) are for the caller, not the manifest.

    With ``template`` (a confirmed non-kit ``Template``; feature 016), ``combination`` is the
    template's id: the map is built on it (arrangement A) instead of hung as a combination, and the
    entry adds ``template``, ``margin``, and the ``layers`` and ``citations`` of its own report
    (which cites the template's dataset).
    """
    from lego_image_processor.datasets.cache import DatasetError
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.cells import map_cells
    from lego_image_processor.maps.classify import MapBuildError
    from lego_image_processor.maps.preview import write_preview
    from lego_image_processor.parts import (OwnedInputs, build_parts_list, to_bricklink_xml,
                                            to_rebrickable_csv)
    from lego_image_processor.sheets import build_sheet_set, render_pdf

    try:
        if template is None:
            result = build_map(recipe, cache_dir=cache_dir, compare_official=False,
                               arrangement=parse_arrangement(combination))
        else:
            result = build_map(recipe, cache_dir=cache_dir, compare_official=False, template=template)
    except DatasetError as exc:
        raise PrebuildError(f"{recipe.id} {combination}: {exc}") from exc
    except MapBuildError as exc:
        raise PrebuildError(f"cannot build {recipe.id} {combination}: {exc}") from exc
    layout = result.layout
    d = out / rel
    d.mkdir(parents=True, exist_ok=True)
    files: Dict[str, bytes] = {}

    layout_text = layout.to_json()
    files["layout"] = layout_text.encode("utf-8")
    (d / KINDS["layout"][0]).write_bytes(files["layout"])
    write_preview(layout, d / KINDS["preview"][0], scale=PREVIEW_SCALE)
    write_preview(layout, d / KINDS["thumb"][0], scale=THUMB_SCALE, style="square")

    layout_path = d / KINDS["layout"][0]
    sha = _sha256(files["layout"])
    full = build_parts_list(layout, layout_path=KINDS["layout"][0], layout_sha256=sha)
    topup = build_parts_list(layout, layout_path=KINDS["layout"][0], layout_sha256=sha,
                             owned=OwnedInputs(kits=1))
    files["parts"] = full.to_json().encode("utf-8")
    files["parts-1kit"] = topup.to_json().encode("utf-8")
    # allow_partial=False: an unverified lot is a build error, as for `parts export`.
    for kind, pl in (("bricklink", full), ("bricklink-1kit", topup)):
        xml = to_bricklink_xml(pl, None, False)
        if xml is not None:
            files[kind] = xml.encode("utf-8")
    for kind, pl in (("rebrickable", full), ("rebrickable-1kit", topup)):
        csv_text = to_rebrickable_csv(pl, False)
        if csv_text is not None:
            files[kind] = csv_text.encode("utf-8")
    files["cells"] = (json.dumps(map_cells(result), ensure_ascii=False, separators=(",", ":"))
                      + "\n").encode("utf-8")
    for paper in ("letter", "a4"):
        sheet_set = build_sheet_set(layout, layout_path=KINDS["layout"][0], paper=paper,
                                    layout_sha256=sha)
        files[f"sheets-{paper}"] = render_pdf(sheet_set)
    for kind, data in files.items():
        if kind != "layout":
            (d / KINDS[kind][0]).write_bytes(data)
    for kind in ("preview", "thumb"):
        files[kind] = (d / KINDS[kind][0]).read_bytes()

    entries = {}
    for kind, (name, media, desc) in KINDS.items():
        if kind not in files:
            continue
        if template is not None:
            desc = TEMPLATE_DESCRIPTIONS.get(kind, desc)
        data = files[kind]
        ext = name.rsplit(".", 1)[1]
        stem = name.rsplit(".", 1)[0]
        entries[kind] = {"path": f"{rel}/{name}", "bytes": len(data), "sha256": _sha256(data),
                         "media_type": media, "description": desc,
                         "filename": f"98138-world_{recipe.id}_{combination}_{stem}.{ext}"}
    t = topup.totals()
    ft = full.totals()
    entry = {
        "warnings": [w["message"] for w in result.report["warnings"]],
        "shadow_cells": (result.report.get("shadow") or {}).get("cells", 0),
        "summary": {"lots": ft["lots"], "pieces": ft["needed"],
                    "one_kit_covers": t["needed"] - t["to_buy"], "to_buy_with_kit": t["to_buy"],
                    "lots_to_buy_with_kit": t["lots_to_buy"],
                    "unverified_lots": ft["unverified_lots"], "left_over_with_kit": t["leftover"]},
        "nothing_to_buy_with_kit": t["to_buy"] == 0,
        "lots": [lot.to_dict() for lot in topup.lots],
        "leftovers": [row.to_dict() for row in topup.leftovers],
        "files": entries,
        "_report": result.report,
        "_result": result,
    }
    if prices is not None:
        from lego_image_processor.prices import estimate_parts_lists

        report = estimate_parts_lists(full, topup, prices, as_of=today)
        entry["estimates"] = {k: report.manifest_entry(k) for k in ("full", "one_kit")}
        entry["_prices"] = report.prices_block()
    if template is not None:
        entry["template"] = template.id
        entry["margin"] = result.report.get("margin")
        entry["layers"] = _layers(result.report)
        entry["citations"] = _citations(result.report)
    return entry


def _default_combination(recipe) -> str:
    return recipe.arrangement.id if recipe.arrangement else "A"


def build_map_stickers(recipe, result, out: Path, *, cache_dir=None) -> Optional[Dict[str, Any]]:
    """Feature 017: the map's sticker set, written with the library; return the manifest's
    ``maps[].stickers`` block (``{"kit-31203": {...}}``, keyed by ``templates.KIT_TEMPLATE_ID``;
    contracts/web.md).

    ``result`` is the ``MapResult`` of the recipe's default combination when that combination is
    being built, else None, and the map is built once more in it. The set's legend values come
    from that build; the stickers are the same in A, B and C (SC-003). Files go to
    ``maps/<map>/stickers/kit-31203/``: the print sheet on Letter and A4 and both SVGs.
    """
    from lego_image_processor.datasets.cache import DatasetError
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.classify import MapBuildError
    from lego_image_processor.stickers import (StickerError, render_sticker_pdf,
                                               render_sticker_svgs, sticker_set)
    from lego_image_processor.stickers.credits import credit_lines
    from lego_image_processor.templates import KIT_TEMPLATE_ID

    combination = _default_combination(recipe)
    if result is None:
        try:
            result = build_map(recipe, cache_dir=cache_dir, compare_official=False,
                               arrangement=parse_arrangement(combination))
        except DatasetError as exc:
            raise PrebuildError(f"{recipe.id} {combination}: {exc}") from exc
        except MapBuildError as exc:
            raise PrebuildError(f"cannot build {recipe.id} {combination}: {exc}") from exc
    try:
        s = sticker_set(result)
        files: Dict[str, bytes] = {"stickers-letter": render_sticker_pdf(s, "letter"),
                                   "stickers-a4": render_sticker_pdf(s, "a4")}
        svgs = dict(render_sticker_svgs(s))
    except StickerError as exc:
        raise PrebuildError(f"{recipe.id} stickers: {exc}") from exc
    for kind in ("sticker-small", "sticker-large"):
        files[kind] = svgs[STICKER_KINDS[kind][0]].encode("utf-8")
    rel = f"maps/{recipe.id}/stickers/{KIT_TEMPLATE_ID}"
    d = Path(out) / rel
    d.mkdir(parents=True, exist_ok=True)
    cut = {"sticker-small": s.small.geometry.cut_mm, "sticker-large": s.large.geometry.cut_mm}
    entries = {}
    for kind, (name, media, desc) in STICKER_KINDS.items():
        data = files[kind]
        (d / name).write_bytes(data)
        if kind in cut:
            desc = desc.format(w=f"{cut[kind][0]:.1f}", h=f"{cut[kind][1]:.1f}")
        stem, ext = name.rsplit(".", 1)
        entries[kind] = {"path": f"{rel}/{name}", "bytes": len(data), "sha256": _sha256(data),
                         "media_type": media, "description": desc,
                         "filename": f"98138-world_{recipe.id}_{stem}.{ext}"}
    title, line = s.text.title, s.text.line
    plaques = {p["size"]: p for p in s.to_dict()["plaques"]}
    block = {
        "files": entries,
        "title": title,
        "line": line,
        "alt": {"small": f"Small sticker: {title}. {line}", "large": f"Large sticker: {title}. {line}"},
        "legend": [{"label": sw.label, "color": sw.lego_name, "part": sw.part_id} for sw in s.legend],
        "credit": list(credit_lines(recipe, s.credits)),
        "plaques": [plaques["large"], plaques["small"]],   # as the print sheet lists them
        "notes": s.notes.to_dict(),
    }
    return {KIT_TEMPLATE_ID: block}


def build_site(out, maps: Optional[Iterable[str]] = None,
               combinations: Optional[Iterable[str]] = None, *, cache_dir=None,
               fetch: bool = False, echo: Callable[..., None] = print, prices_path=None,
               with_prices: bool = True, allow_partial_prices: bool = False,
               today: Optional[date] = None, templates: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Build the site output into ``out`` and write ``out/manifest.json``; return the manifest.

    Prices (feature 011): by default the packaged snapshot, or ``prices_path``; a missing,
    invalid or (unless ``allow_partial_prices``) partial snapshot is a ``PrebuildError`` before
    anything is built. ``with_prices=False`` builds without estimates. ``today`` is the staleness
    reference date (default: UTC today).

    Templates (feature 016): ``templates`` None builds on every confirmed template in
    ``TEMPLATES``, an empty list on none (see ``select_templates``). The manifest gains
    ``templates`` and ``maps[].template_variants`` only when a template variant was built.
    """
    import lego_image_processor
    from lego_image_processor.datasets.cache import DatasetError, fetch as fetch_dataset
    from lego_image_processor.maps.build import missing_datasets
    from lego_image_processor.maps.recipe import load_recipe
    from lego_image_processor.parts import ACKNOWLEDGEMENT, BRICKLINK_UPLOAD_NOTE, PRICE_NOTE

    started = time.monotonic()
    prices = load_prices(prices_path, allow_partial=allow_partial_prices) if with_prices else None
    if today is None:
        today = datetime.now(timezone.utc).date()
    prices_block = None
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    maps = list(maps) if maps is not None else list(MAP_IDS)
    combinations = list(combinations) if combinations is not None else list(COMBINATIONS)
    chosen_templates, notes = select_templates(templates)
    for note in notes:
        echo(f"Template {note}")
    used_templates = set()
    rows = []
    for map_id in maps:
        recipe = load_recipe(map_id)
        missing = missing_datasets(recipe, cache_dir)
        if missing and not fetch:
            raise PrebuildError(f"{map_id}: dataset(s) not cached: "
                                f"{', '.join(e.id for e in missing)}; run with --fetch")
        for entry in missing:
            echo(f"Fetching {entry.id} ({entry.size:,} bytes) from {entry.url}")
            try:
                fetch_dataset(entry, cache_dir=cache_dir)
            except DatasetError as exc:
                raise PrebuildError(str(exc)) from exc
        variants = {}
        report = None
        default_result = None
        for c in combinations:
            t0 = time.monotonic()
            v = build_variant(recipe, c, out, f"maps/{map_id}/{c}", cache_dir=cache_dir,
                              prices=prices, today=today)
            report = v.pop("_report")
            result = v.pop("_result")
            if c == _default_combination(recipe):
                default_result = result
            block = v.pop("_prices", None)
            if block is not None:
                prices_block = block
            variants[c] = v
            size = sum(f["bytes"] for f in v["files"].values())
            echo(f"{map_id} {c}: {len(v['files'])} files, {size / 1e6:.1f} MB, "
                 f"{time.monotonic() - t0:.1f} s")
        t0 = time.monotonic()
        stickers = build_map_stickers(recipe, default_result, out, cache_dir=cache_dir)
        default_result = None
        if stickers:
            for template_id, st in stickers.items():
                size = sum(f["bytes"] for f in st["files"].values())
                echo(f"{map_id} stickers: {len(st['files'])} files ({template_id}), "
                     f"{size / 1e3:.0f} kB, {time.monotonic() - t0:.1f} s")
        template_variants = {}
        for tpl in chosen_templates:   # feature 016: after the kit variants; kit files unchanged
            reason = template_reason(recipe, tpl)
            if reason is not None:
                echo(f"{map_id} {tpl.id}: skipped ({reason})")
                continue
            t0 = time.monotonic()
            v = build_variant(recipe, tpl.id, out, f"maps/{map_id}/{tpl.id}", cache_dir=cache_dir,
                              prices=prices, today=today, template=tpl)
            v.pop("_report")
            v.pop("_result")   # feature 017: the MapResult is for the caller, not the manifest
            block = v.pop("_prices", None)
            if block is not None and prices_block is None:
                prices_block = block
            template_variants[tpl.id] = v
            used_templates.add(tpl.id)
            size = sum(f["bytes"] for f in v["files"].values())
            echo(f"{map_id} {tpl.id}: {len(v['files'])} files, {size / 1e6:.1f} MB, "
                 f"{time.monotonic() - t0:.1f} s")
        datasets = [{"id": e.id, "version": e.version, "sha256": e.sha256, "url": e.url, "size": e.size,
                     **({"content_sha256": e.content_sha256} if e.content_sha256 else {}),
                     **({"files": len(e.files), "files_sha256": e.files_sha256} if e.files else {})}
                    for e in recipe.datasets() if e.kind == "download"]
        rows.append({"id": recipe.id, "title": recipe.title, "description": recipe.description,
                     "recipe": {"format": recipe.format, "sha256": recipe.sha256},
                     "default_combination": recipe.arrangement.id if recipe.arrangement else "A",
                     "layers": _layers(report), "datasets": datasets,
                     "citations": _citations(report), "variants": variants,
                     **({"template_variants": template_variants} if template_variants else {}),
                     **({"stickers": stickers} if stickers else {})})
    manifest = {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools": {"lego_image_processor": lego_image_processor.__version__, "web98138": __version__,
                  "python": platform.python_version(), "git_commit": _git_commit()},
        "disclaimer": DISCLAIMER,
        "acknowledgement": ACKNOWLEDGEMENT,
        "price_note": PRICE_NOTE,
        "bricklink_note": BRICKLINK_UPLOAD_NOTE,
        "part_labels": _part_labels(rows),
        **_arrangements(),
        **({"templates": [_template_record(t) for t in chosen_templates if t.id in used_templates]}
           if used_templates else {}),
        "maps": rows,
    }
    if prices_block is not None:
        manifest["prices"] = prices_block
    manifest["build_seconds"] = round(time.monotonic() - started, 1)
    total = sum(f["bytes"] for m in rows for v in _all_variants(m) for f in v["files"].values())
    total += sum(f["bytes"] for m in rows for st in m.get("stickers", {}).values()
                 for f in st["files"].values())       # feature 017: the site's size, stickers too
    manifest["total_bytes"] = total
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    echo(f"Built {sum(len(_all_variants(m)) for m in rows)} variants, {total / 1e6:.1f} MB, in "
         f"{manifest['build_seconds']} s: {out / 'manifest.json'}")
    echo(DISCLAIMER)
    return manifest


def _parse_templates(value: Optional[str]) -> Optional[List[str]]:
    """``--templates``: None (every confirmed template), ``none`` ([]), or ids from ``TEMPLATES``."""
    if value is None:
        return None
    if value.strip().lower() == "none":
        return []
    allowed = list(TEMPLATES)
    items = [v.strip() for v in value.split(",") if v.strip()]
    bad = [v for v in items if v not in allowed]
    if bad or not items:
        raise ValueError(f"unknown template {', '.join(bad) or '(none)'}; use {', '.join(allowed)} or none "
                         "(the kit's combinations A, B and C are always built)")
    return [v for v in allowed if v in items]


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m web98138.prebuild",
                                description="Build every 98138.world map variant and download.",
                                epilog=DISCLAIMER)
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--maps", help=f"comma-separated map ids (default: {','.join(MAP_IDS)})")
    p.add_argument("--combinations", help="comma-separated combinations (default: A,B,C)")
    p.add_argument("--cache-dir", help="dataset cache root (default: the per-user cache)")
    p.add_argument("--fetch", action="store_true",
                   help="download missing pinned datasets (verified) before building")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--prices", metavar="FILE",
                   help="price snapshot (default: the packaged bricklink_price_guide.json)")
    g.add_argument("--no-prices", action="store_true",
                   help="build without price estimates (no prices block, no price panel)")
    p.add_argument("--allow-partial-prices", action="store_true",
                   help="accept a partial price snapshot (pages say it is partial)")
    p.add_argument("--templates", metavar="LIST",
                   help=f"comma-separated templates to build beside the kit ({', '.join(TEMPLATES)}), "
                        "or none (default: every one the project owner confirmed)")
    p.add_argument("--quiet", "-q", action="store_true")
    args = p.parse_args(argv)
    try:
        maps = _parse_list(args.maps, MAP_IDS, "map")
        combos = _parse_list(args.combinations, COMBINATIONS, "combination", upper=True)
        templates = _parse_templates(args.templates)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(DISCLAIMER, file=sys.stderr)
        return 2
    echo = (lambda *a: None) if args.quiet else print
    try:
        build_site(args.out, maps, combos, cache_dir=args.cache_dir, fetch=args.fetch, echo=echo,
                   prices_path=args.prices, with_prices=not args.no_prices,
                   allow_partial_prices=args.allow_partial_prices, templates=templates)
    except PrebuildError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(DISCLAIMER, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
