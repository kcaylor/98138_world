"""Guard helpers for feature 017 (map stickers): research R13 G1-G4, FR-017, SC-006.

Feature 017 adds an optional ``[sticker]`` table to recipes and a sticker command. Nothing else
may change: every kit output of the eight bundled recipes stays byte for byte the same, except
the recorded recipe checksum when a bundled recipe gains its table. These helpers measure that.

- ``prefix_bytes(path)``: a recipe file's bytes before the line that starts
  ``# Map stickers (feature 017):`` (research R5), or the whole file when it has none.
- ``kit_outputs(recipe_bytes, recipe_path, cache_dir, prices)``: G2's output set for one recipe
  built in A, with the recipe SHA-256 and the layout file's SHA-256 replaced by placeholders, so
  the outputs of two recipe texts that differ only in their sticker table compare equal.
- ``guard_digests(cache_dir)``: G3's digests of every kit output of the eight bundled recipes in
  A, B and C, each built from ``prefix_bytes`` so the digests keep the af3ce57 recipe checksums;
  plus the sheets PDF (Letter) bytes and each sheets SVG page of ``ocean-sst`` and
  ``land-elevation`` in A. ``compare`` names the recipe, combination and output that differ.
- ``map_part_blocks()``: G4's canonical-JSON digests of the 6141 and 98138 blocks of
  ``part_colors.json`` and ``part_numbers.json`` and of the citation entries those blocks use
  (feature 016's method, so rows appended for other parts do not touch them).

Outputs are made with the library functions the CLI commands call (``map build``, ``map
cells``, ``parts list``, ``parts export``, ``parts estimate``, ``sheets counts``, ``sheets
build``), written the way those commands write them. Only functions present at commits af3ce57
and 6038d9c are used, so this module also runs against an export of either. The layout path
recorded in parts lists, estimates, counts and sheets is ``<recipe>/<combination>/layout.json``
(feature 016's kit golden uses the same relative path), so no temporary path reaches an output.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

CLI_DIR = Path(__file__).resolve().parents[2]
GOLDEN_PATH = CLI_DIR / "tests" / "fixtures" / "golden" / "stickers_017_guard.json"
PRICES_FIXTURE = CLI_DIR / "tests" / "fixtures" / "prices" / "bricklink_price_guide.json"
STICKER_MARKER = b"# Map stickers (feature 017):"
FORMAT_VERSION = "1"
GENERATOR = ("cli/tests/integration/test_stickers_outputs_unchanged.py::test_guard_golden "
             "with STICKERS_017_GUARD_WRITE=1")
FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
AS_OF = date(2026, 12, 5)  # 4 days after the synthetic snapshot, as in the price tests
COMBINATIONS: Tuple[str, ...] = ("A", "B", "C")
SHEET_RECIPES: Tuple[str, ...] = ("land-elevation", "ocean-sst")
SHEET_COMBINATION = "A"
KIT_PARTS: Tuple[str, ...] = ("6141", "98138")
RECIPE_PLACEHOLDER = "<recipe-sha256>"
LAYOUT_PLACEHOLDER = "<layout-sha256>"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
_GENERATED_AT = re.compile(r'"generated_at": "[^"\n]*"')


# --- digests ----------------------------------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: Any) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blob_digest(data: Optional[bytes]) -> Optional[Dict[str, Any]]:
    """Size and SHA-256 of ``data``; None (an output the command does not write) stays None."""
    return None if data is None else {"bytes": len(data), "sha256": sha256_hex(data)}


def png_pixels(png: bytes) -> bytes:
    """The decoded pixels of a PNG: mode, size and raw samples."""
    from PIL import Image

    with Image.open(io.BytesIO(png)) as im:
        im.load()
        w, h = im.size
        return f"{im.mode} {w}x{h}\n".encode("ascii") + im.tobytes()


def svg_pages_digest(pages: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """One digest over the SVG pages in order: name, newline, text, NUL for each page."""
    h = hashlib.sha256()
    total = 0
    for name, text in pages:
        b = text.encode("utf-8")
        total += len(b)
        h.update(name.encode("utf-8") + b"\n" + b + b"\0")
    return {"pages": len(pages), "bytes": total, "sha256": h.hexdigest()}


# --- recipes ----------------------------------------------------------------------------------

def bundled_recipe_paths() -> Dict[str, Path]:
    """The bundled recipe ids and files, sorted by id."""
    from lego_image_processor.maps.recipe import bundled_recipes

    found = bundled_recipes()
    return {rid: Path(found[rid]) for rid in sorted(found)}


def prefix_bytes(path: Union[str, Path]) -> bytes:
    """The recipe file's bytes before the line that starts ``# Map stickers (feature 017):``, or
    the whole file when there is none (research R5)."""
    raw = Path(path).read_bytes()
    out: List[bytes] = []
    for line in raw.splitlines(keepends=True):
        if line.startswith(STICKER_MARKER):
            return b"".join(out)
        out.append(line)
    return raw


# --- building the outputs ---------------------------------------------------------------------

def _snapshot(prices):
    """The price snapshot, loaded by its file name from its own directory, so the estimate
    records ``"path": "<file name>"`` (as ``parts estimate --prices <file name>`` run there
    does) and no checkout path reaches an output."""
    from lego_image_processor.prices.snapshot import PriceSnapshot, load_snapshot

    if isinstance(prices, PriceSnapshot):
        return prices
    p = Path(prices).resolve()
    with contextlib.chdir(p.parent):
        return load_snapshot(p.name)


def _json_file(data: Any) -> bytes:
    """A report as ``map build --report`` writes it."""
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def variant_outputs(recipe, combination: str, cache_dir, snapshot, *, sheets_svg: bool = False,
                    sheets_pdf: bool = False) -> Dict[str, Optional[bytes]]:
    """Every kit output of ``recipe`` hung as ``combination``, as the CLI commands write them.

    ``generated_at`` is fixed in the layout and the report before anything reads the layout. A
    file the command does not write (an export with nothing to buy) is None. With
    ``sheets_svg``, ``sheets-letter.svg/<page>`` holds each SVG page; with ``sheets_pdf``,
    ``sheets-letter.pdf`` holds the PDF bytes."""
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.cells import map_cells
    from lego_image_processor.maps.preview import write_preview
    from lego_image_processor.parts import (OwnedInputs, build_parts_list, read_layout,
                                            to_bricklink_xml, to_rebrickable_csv)
    from lego_image_processor.prices.estimate import estimate_layout
    from lego_image_processor.sheets import build_sheet_set, render_pdf, render_svg, section_counts

    result = build_map(recipe, cache_dir=cache_dir, compare_official=None,
                       arrangement=parse_arrangement(combination))
    out: Dict[str, Optional[bytes]] = {}
    layout_text, n = _GENERATED_AT.subn(f'"generated_at": "{FIXED_GENERATED_AT}"',
                                        result.layout.to_json())
    if n != 1:
        raise AssertionError(f"{recipe.id} {combination}: expected one generated_at in the layout, found {n}")
    out["layout.json"] = layout_text.encode("utf-8")
    out["report.json"] = _json_file({**result.report, "generated_at": FIXED_GENERATED_AT})
    with tempfile.TemporaryDirectory(prefix="stickers-guard-") as tmp:
        png = write_preview(result.layout, Path(tmp) / "preview.png")
        out["preview.png"] = png.read_bytes()
        path = Path(tmp) / "layout.json"
        path.write_bytes(out["layout.json"])
        layout = dataclasses.replace(read_layout(path), path=f"{recipe.id}/{combination}/layout.json")
    cells = map_cells(result)
    out["cells.json"] = (json.dumps(cells, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    for suffix, kits in (("", 0), ("-1kit", 1)):
        pl = build_parts_list(layout, owned=OwnedInputs(kits=kits))
        out[f"parts{suffix}.json"] = pl.to_json().encode("utf-8")
        xml = to_bricklink_xml(pl)
        csv_text = to_rebrickable_csv(pl)
        out[f"bricklink{suffix}.xml"] = None if xml is None else xml.encode("utf-8")
        out[f"rebrickable{suffix}.csv"] = None if csv_text is None else csv_text.encode("utf-8")
    out["estimate.json"] = estimate_layout(layout, snapshot, as_of=AS_OF).to_json().encode("utf-8")
    out["counts.json"] = section_counts(layout).to_json().encode("utf-8")
    if sheets_svg or sheets_pdf:
        sheet_set = build_sheet_set(layout, paper="letter")
        if sheets_svg:
            for name, text in render_svg(sheet_set):
                out[f"sheets-letter.svg/{name}"] = text.encode("utf-8")
        if sheets_pdf:
            out["sheets-letter.pdf"] = render_pdf(sheet_set)
    return out


def kit_outputs(recipe_bytes: bytes, recipe_path: Union[str, Path], cache_dir,
                prices=PRICES_FIXTURE) -> Dict[str, Optional[bytes]]:
    """G2's output set of one recipe text built in A: layout, report, preview pixels, parts lists
    (full and one kit), BrickLink XML, Rebrickable CSV, estimate, section counts, cells.json and
    the sheets SVG pages, each with the recipe SHA-256 and the layout file's SHA-256 replaced by
    placeholders (the preview pixels carry neither)."""
    from lego_image_processor.maps.recipe import parse_recipe

    recipe = parse_recipe(bytes(recipe_bytes), path=Path(recipe_path))
    raw = variant_outputs(recipe, "A", cache_dir, _snapshot(prices), sheets_svg=True)
    layout_sha = sha256_hex(raw["layout.json"])
    swaps = ((recipe.sha256.encode("ascii"), RECIPE_PLACEHOLDER.encode("ascii")),
             (layout_sha.encode("ascii"), LAYOUT_PLACEHOLDER.encode("ascii")))
    out: Dict[str, Optional[bytes]] = {}
    for name, data in raw.items():
        if name == "preview.png":
            out["preview.pixels"] = png_pixels(data)
            continue
        if data is not None:
            for old, new in swaps:
                data = data.replace(old, new)
        out[name] = data
    return out


def first_difference(a: Optional[bytes], b: Optional[bytes]) -> str:
    """A short description of where two outputs first differ."""
    if a is None or b is None:
        return f"{'absent' if a is None else len(a)} vs {'absent' if b is None else len(b)} bytes"
    if a == b:
        return "equal"
    i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    lo = max(0, i - 60)
    return (f"{len(a)} vs {len(b)} bytes, first difference at byte {i}: "
            f"{a[lo:i + 60]!r} vs {b[lo:i + 60]!r}")


# --- G3: the guard golden ---------------------------------------------------------------------

def _variant_digests(raw: Mapping[str, Optional[bytes]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, data in raw.items():
        if name.startswith("sheets-letter.svg/"):
            continue
        if name == "preview.png":
            out[name] = {**blob_digest(data), "pixels": sha256_hex(png_pixels(data))}
        else:
            out[name] = blob_digest(data)
    pages = [(name.split("/", 1)[1], data.decode("utf-8")) for name, data in raw.items()
             if name.startswith("sheets-letter.svg/")]
    if pages:
        out["sheets-letter.svg"] = svg_pages_digest(pages)
        for name, text in pages:
            out[f"sheets-letter.svg/{name}"] = blob_digest(text.encode("utf-8"))
    return out


def _dataset_rows(recipes: Iterable[Any]) -> List[Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for r in recipes:
        for e in r.datasets():
            row = {"id": e.id, "version": e.version, "kind": e.kind}
            for k in ("sha256", "content_sha256", "files_sha256"):
                if getattr(e, k, None):
                    row[k] = getattr(e, k)
            rows[e.id] = row
    return [rows[k] for k in sorted(rows)]


def guard_digests(cache_dir, prices=PRICES_FIXTURE,
                  recipes: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """G3: digests of every kit output of the bundled recipes (default all eight) in A, B and C,
    each built from ``prefix_bytes`` of its file, plus the sheets PDF (Letter) bytes and SVG
    pages of ``SHEET_RECIPES`` in A."""
    from lego_image_processor.maps.recipe import parse_recipe

    snapshot = _snapshot(prices)
    paths = bundled_recipe_paths()
    ids = sorted(paths) if recipes is None else sorted(recipes)
    parsed, recipe_rows, variants = [], {}, []
    for rid in ids:
        recipe = parse_recipe(prefix_bytes(paths[rid]), path=paths[rid])
        parsed.append(recipe)
        recipe_rows[rid] = recipe.sha256
        for c in COMBINATIONS:
            sheets = rid in SHEET_RECIPES and c == SHEET_COMBINATION
            raw = variant_outputs(recipe, c, cache_dir, snapshot, sheets_svg=sheets, sheets_pdf=sheets)
            variants.append({"recipe": rid, "combination": c, "outputs": _variant_digests(raw)})
    prices_path = Path(prices) if isinstance(prices, (str, Path)) else None
    return {
        "format_version": FORMAT_VERSION,
        "title": "Digests of every kit 31203 output before feature 017 (research R13 G3, FR-017, SC-006)",
        "generator": GENERATOR,
        "inputs": {
            "datasets": "fixtures (tests/fixtures/datasets, via the fixture_registry fixture)",
            "generated_at": FIXED_GENERATED_AT,
            "as_of": AS_OF.isoformat(),
            "prices": None if prices_path is None else {"file": prices_path.name,
                                                        "sha256": sha256_hex(prices_path.read_bytes())},
            "recipes": recipe_rows,
            "combinations": list(COMBINATIONS),
            "sheets": {"recipes": [r for r in ids if r in SHEET_RECIPES],
                       "combination": SHEET_COMBINATION, "paper": "letter"},
            "layout_path": "<recipe>/<combination>/layout.json",
        },
        "datasets": _dataset_rows(parsed),
        "variants": variants,
        "disclaimer": DISCLAIMER,
    }


def compare(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> List[str]:
    """Differences between two guard documents, naming the recipe, combination and output."""
    diffs: List[str] = []
    for key in ("format_version", "inputs", "datasets"):
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key} differs: expected {expected.get(key)!r}, got {actual.get(key)!r}")
    ev = {(v["recipe"], v["combination"]): v["outputs"] for v in expected.get("variants", [])}
    av = {(v["recipe"], v["combination"]): v["outputs"] for v in actual.get("variants", [])}
    for key in sorted(set(ev) | set(av)):
        where = f"{key[0]} {key[1]}"
        if key not in av or key not in ev:
            diffs.append(f"{where}: variant {'missing' if key not in av else 'unexpected'}")
            continue
        e, a = ev[key], av[key]
        for out in sorted(set(e) | set(a)):
            if out not in a:
                diffs.append(f"{where}: {out} missing")
            elif out not in e:
                diffs.append(f"{where}: {out} unexpected")
            elif e[out] != a[out]:
                diffs.append(f"{where}: {out} differs (expected {e[out]}, got {a[out]})")
    return diffs


_LEAF = re.compile(r'\{\n(?:[ ]+"[^"\n]*": (?:"[^"\n]*"|-?\d+|true|false|null),?\n)+[ ]*\}')


def to_text(doc: Mapping[str, Any]) -> str:
    """Indented JSON with each innermost object (a digest entry) on one line."""
    text = json.dumps(doc, indent=2, ensure_ascii=False)
    return _LEAF.sub(lambda m: "{" + ", ".join(x.strip().rstrip(",") for x in
                                               m.group(0)[1:-1].strip().split("\n")) + "}", text) + "\n"


# --- G4: the map parts' blocks of the part data -----------------------------------------------

def _digest(obj: Any) -> str:
    return sha256_hex(canonical(obj))


def map_part_blocks(data_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Canonical-JSON digests of the 6141 and 98138 blocks of ``part_colors.json`` and
    ``part_numbers.json``, of the citation entries those blocks use, and of the excluded rows
    for those parts (feature 016's method)."""
    from lego_image_processor.datasets.registry import DATA_DIR

    d = Path(data_dir) if data_dir is not None else Path(DATA_DIR)
    pc = json.loads((d / "part_colors.json").read_text(encoding="utf-8"))
    pn = json.loads((d / "part_numbers.json").read_text(encoding="utf-8"))
    colors: Dict[str, str] = {f"parts.{p}": _digest(pc["parts"][p]) for p in KIT_PARTS}
    used = {v for p in KIT_PARTS for row in pc["parts"][p] for v in row["citations"].values()}
    colors["citations"] = _digest(sorted((c for c in pc["source"]["citations"] if c["id"] in used),
                                         key=lambda c: c["id"]))
    colors["excluded"] = _digest([e for e in pc["source"].get("excluded", []) if e["part"] in KIT_PARTS])
    numbers: Dict[str, str] = {f"parts.{p}": _digest(pn["parts"][p]) for p in KIT_PARTS}
    pages = {pn["parts"][p][site]["citation"] for p in KIT_PARTS for site in ("bricklink", "rebrickable")}
    numbers["citations"] = _digest(sorted((x for x in pn["source"]["pages"] if x["id"] in pages),
                                          key=lambda x: x["id"]))
    return {"part_colors.json": colors, "part_numbers.json": numbers}
