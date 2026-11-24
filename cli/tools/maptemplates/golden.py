"""Kit golden digests (feature 016, research R9, SC-001): every kit 31203 output, digested.

``kit_golden()`` builds the bundled recipes x combinations A, B, C on the kit through the CLI
commands themselves (``click.testing.CliRunner`` on ``lego_image_processor.cli.main.cli``), as a
maker would run them, and digests every output:

- ``map build -o --preview --report``: its text, the layout JSON and the report JSON (with
  ``generated_at`` fixed to ``FIXED_GENERATED_AT`` before anything reads the layout), and the
  preview PNG (bytes and decoded pixels, so an encoder upgrade shows as a byte change only);
- ``map check`` text; ``map cells -o`` (``cells.json``) and its text;
- ``parts list`` (JSON and text, full and ``--kits 1``) and ``parts export`` (BrickLink XML and
  Rebrickable CSV, full and ``--kits 1``, with their text; a file the command does not write is
  recorded as null);
- ``parts estimate`` (JSON and text) on the synthetic fixture snapshot
  ``tests/fixtures/prices/bricklink_price_guide.json`` with ``--as-of AS_OF``;
- ``sheets counts`` (JSON and text); ``sheets build`` as SVG pages (Letter, every combination) and
  as PDF bytes (Letter, combination A only), with their text.

Commands run in a temporary directory with relative paths (``<recipe>/<C>/layout.json``), so no
temporary path reaches an output; any that would is replaced by ``PLACEHOLDER`` in the text
outputs. ``reference_digests()`` adds canonical-JSON digests of the 6141 and 98138 blocks and the
citations they use in ``part_colors.json`` and ``part_numbers.json`` (new parts may be appended).

The harness imports only modules present at commits af3ce57 and 6038d9c (``lego_image_processor.cli.main``,
``.datasets.registry``, ``.kit.source``, ``.maps.recipe``) and only CLI commands present there, so
the same file runs against a checkout of ``main``. The result holds no timestamp, version or path:
the same inputs give the same file. ``--fixtures`` points a temporary registry at the committed
dataset fixtures exactly as the CLI tests do (``fixtures004.registry``).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from lego_image_processor.datasets.registry import DATA_DIR
from lego_image_processor.kit.source import DISCLAIMER

CLI_DIR = Path(__file__).resolve().parents[2]
GOLDEN_PATH = CLI_DIR / "tests" / "fixtures" / "golden" / "kit_outputs.json"
PRICES_FIXTURE = CLI_DIR / "tests" / "fixtures" / "prices" / "bricklink_price_guide.json"
PRICES_NAME = PRICES_FIXTURE.name
FORMAT_VERSION = "1"
GENERATOR = "tools/maptemplates kit-golden"
FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
AS_OF = "2026-12-05"  # 4 days after the fixture snapshot, as in the web tests
COMBINATIONS: Tuple[str, ...] = ("A", "B", "C")
PDF_COMBINATIONS: Tuple[str, ...] = ("A",)
KIT_PARTS: Tuple[str, ...] = ("6141", "98138")
PLACEHOLDER = "<tmp>"
_GENERATED_AT = re.compile(r'"generated_at": "[^"\n]*"')


class GoldenError(RuntimeError):
    """A command failed or an output is not as the harness expects (exit 1)."""


# --- digest rules -----------------------------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: Any) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def blob_digest(data: bytes) -> Dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256_hex(data)}


def png_digest(data: bytes) -> Dict[str, Any]:
    """Bytes digest plus a digest of the decoded pixels (mode, size and raw samples)."""
    from PIL import Image

    with Image.open(io.BytesIO(data)) as im:
        im.load()
        w, h = im.size
        pixels = sha256_hex(f"{im.mode} {w}x{h}\n".encode("ascii") + im.tobytes())
        mode = im.mode
    return {**blob_digest(data), "pixels": pixels, "size": f"{w}x{h}", "mode": mode}


def svg_pages_digest(pages: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """One digest over the SVG pages in order: name, newline, text, NUL for each page."""
    h = hashlib.sha256()
    total = 0
    for name, text in pages:
        b = text.encode("utf-8")
        total += len(b)
        h.update(name.encode("utf-8") + b"\n" + b + b"\0")
    return {"pages": len(pages), "bytes": total, "sha256": h.hexdigest()}


def fix_generated_at(text: str) -> str:
    """Replace the one ``"generated_at": "..."`` of a layout or report JSON by the fixed time."""
    out, n = _GENERATED_AT.subn(f'"generated_at": "{FIXED_GENERATED_AT}"', text)
    if n != 1:
        raise GoldenError(f"expected one generated_at, found {n}")
    return out


def normalise_text(text: str, root: Path) -> str:
    """Replace the temporary directory (as given and resolved) by ``PLACEHOLDER``."""
    for p in sorted({str(root), str(Path(root).resolve())}, key=len, reverse=True):
        text = text.replace(p, PLACEHOLDER)
    return text


# --- reference data ---------------------------------------------------------------------------

def _digest(obj: Any) -> str:
    return sha256_hex(canonical(obj))


def reference_digests(data_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Canonical-JSON digests of the kit parts' blocks (6141, 98138) and the citations they use."""
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


# --- running the commands ---------------------------------------------------------------------

@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


@contextlib.contextmanager
def _datasets(root: Path, fixtures: bool, cache_dir) -> Iterator[Optional[str]]:
    """The ``--cache-dir`` value for the commands; with ``fixtures``, a temporary registry whose
    download entries are the committed fixtures (restored afterwards)."""
    if not fixtures:
        yield None if cache_dir is None else str(Path(cache_dir).resolve())
        return
    from fixtures004.registry import make_fixture_registry
    import lego_image_processor.datasets.registry as reg

    fr = make_fixture_registry(root / "fixture-registry")
    old_path, old_env = reg.REGISTRY_PATH, os.environ.get("LEGO_IMAGE_PROCESSOR_CACHE")
    reg.REGISTRY_PATH = fr.registry_path
    os.environ["LEGO_IMAGE_PROCESSOR_CACHE"] = str(fr.cache_dir)
    try:
        fr.place_all()
        yield str(fr.cache_dir.relative_to(root))
    finally:
        reg.REGISTRY_PATH = old_path
        if old_env is None:
            os.environ.pop("LEGO_IMAGE_PROCESSOR_CACHE", None)
        else:
            os.environ["LEGO_IMAGE_PROCESSOR_CACHE"] = old_env


class _Runner:
    def __init__(self, root: Path):
        from click.testing import CliRunner

        self.root = root
        self.runner = CliRunner()

    def __call__(self, args: Sequence[str], save: Optional[Path] = None) -> bytes:
        """Run one CLI command (exit 0 required); return its normalised stdout, saved to ``save``."""
        from lego_image_processor.cli.main import cli

        r = self.runner.invoke(cli, list(args), catch_exceptions=False)
        if r.exit_code != 0:
            raise GoldenError(f"`lego-image-processor {' '.join(args)}` exited {r.exit_code}:\n{r.output}")
        data = normalise_text(r.stdout, self.root).encode("utf-8")
        if save is not None:
            save.write_bytes(data)
        return data


def _file(path: Path) -> Optional[Dict[str, Any]]:
    return blob_digest(path.read_bytes()) if path.is_file() else None


def variant_digests(run: _Runner, recipe_id: str, combination: str,
                    cache_arg: Optional[str]) -> Dict[str, Any]:
    """Digests of every output of ``recipe_id`` hung as ``combination`` (files kept in
    ``<root>/<recipe>/<combination>/``, text outputs saved there as ``*.txt``)."""
    rel = f"{recipe_id}/{combination}"
    d = run.root / rel
    d.mkdir(parents=True, exist_ok=True)
    layout = f"{rel}/layout.json"
    common = ["--arrangement", combination] + ([] if cache_arg is None else ["--cache-dir", cache_arg])
    out: Dict[str, Any] = {}

    def text(name: str, args: Sequence[str]) -> None:
        out[name] = blob_digest(run(args, d / name))

    text("map-build.txt", ["map", "build", recipe_id, "-o", layout, "--preview", f"{rel}/preview.png",
                           "--report", f"{rel}/report.json", *common])
    for name in ("layout.json", "report.json"):  # fixed time before anything reads the layout
        p = d / name
        p.write_bytes(fix_generated_at(p.read_bytes().decode("utf-8")).encode("utf-8"))
        out[name] = _file(p)
    out["preview.png"] = png_digest((d / "preview.png").read_bytes())
    text("map-check.txt", ["map", "check", recipe_id, *common])
    text("map-cells.txt", ["map", "cells", recipe_id, "-o", f"{rel}/cells.json", *common])
    out["cells.json"] = _file(d / "cells.json")

    run(["parts", "list", layout, "-o", f"{rel}/parts.json"])
    run(["parts", "list", layout, "--kits", "1", "-o", f"{rel}/parts-1kit.json"])
    out["parts.json"] = _file(d / "parts.json")
    out["parts-1kit.json"] = _file(d / "parts-1kit.json")
    text("parts-list.txt", ["parts", "list", layout])
    text("parts-list-1kit.txt", ["parts", "list", layout, "--kits", "1"])
    for suffix, kits in (("", []), ("-1kit", ["--kits", "1"])):
        text(f"parts-export{suffix}.txt", ["parts", "export", layout, *kits,
                                           "--bricklink", f"{rel}/bricklink{suffix}.xml",
                                           "--rebrickable", f"{rel}/rebrickable{suffix}.csv"])
        out[f"bricklink{suffix}.xml"] = _file(d / f"bricklink{suffix}.xml")
        out[f"rebrickable{suffix}.csv"] = _file(d / f"rebrickable{suffix}.csv")

    prices = ["--prices", PRICES_NAME, "--as-of", AS_OF]
    run(["parts", "estimate", layout, *prices, "-o", f"{rel}/estimate.json"])
    out["estimate.json"] = _file(d / "estimate.json")
    text("estimate.txt", ["parts", "estimate", layout, *prices])

    run(["sheets", "counts", layout, "-o", f"{rel}/counts.json"])
    out["counts.json"] = _file(d / "counts.json")
    text("counts.txt", ["sheets", "counts", layout])

    text("sheets-letter-svg.txt", ["sheets", "build", layout, "--format", "svg", "-o", f"{rel}/sheets-letter"])
    pages = sorted((d / "sheets-letter").glob("page-*.svg"))
    out["sheets-letter.svg"] = svg_pages_digest([(p.name, p.read_bytes().decode("utf-8")) for p in pages])
    if combination in PDF_COMBINATIONS:
        text("sheets-letter-pdf.txt", ["sheets", "build", layout, "-o", f"{rel}/sheets-letter.pdf"])
        out["sheets-letter.pdf"] = _file(d / "sheets-letter.pdf")
    return out


def _dataset_rows(recipe_ids: Iterable[str]) -> List[Dict[str, Any]]:
    from lego_image_processor.maps.recipe import load_recipe

    rows: Dict[str, Dict[str, Any]] = {}
    for rid in recipe_ids:
        for e in load_recipe(rid).datasets():
            row = {"id": e.id, "version": e.version, "kind": e.kind}
            for k in ("sha256", "content_sha256", "files_sha256"):
                if getattr(e, k, None):
                    row[k] = getattr(e, k)
            rows[e.id] = row
    return [rows[k] for k in sorted(rows)]


def kit_golden(*, cache_dir=None, fixtures: bool = False, recipes: Optional[Iterable[str]] = None,
               combinations: Sequence[str] = COMBINATIONS, keep: Optional[Path] = None) -> Dict[str, Any]:
    """Digests of every kit output for ``recipes`` (default: every bundled recipe) x
    ``combinations``, from the dataset fixtures (``fixtures``) or a dataset cache (``cache_dir``,
    default the per-user cache). With ``keep``, the outputs stay in that directory."""
    if fixtures and cache_dir is not None:
        raise ValueError("give cache_dir or fixtures, not both")
    root = Path(tempfile.mkdtemp(prefix="kit-golden-")) if keep is None else Path(keep)
    root.mkdir(parents=True, exist_ok=True)
    try:
        with _chdir(root), _datasets(root, fixtures, cache_dir) as cache_arg:
            from lego_image_processor.maps.recipe import bundled_recipes

            ids = sorted(bundled_recipes()) if recipes is None else sorted(recipes)
            shutil.copyfile(PRICES_FIXTURE, root / PRICES_NAME)
            run = _Runner(root)
            variants = [{"recipe": rid, "combination": c,
                         "outputs": variant_digests(run, rid, c, cache_arg)}
                        for rid in ids for c in sorted(combinations)]
            datasets = _dataset_rows(ids)
    finally:
        if keep is None:
            shutil.rmtree(root, ignore_errors=True)
    return {
        "format_version": FORMAT_VERSION,
        "title": "Digests of every kit 31203 output (feature 016, SC-001)",
        "generator": GENERATOR + (" --fixtures" if fixtures else " --cache-dir"),
        "inputs": {
            "datasets": "fixtures" if fixtures else "cache",
            "generated_at": FIXED_GENERATED_AT,
            "as_of": AS_OF,
            "prices": {"file": PRICES_NAME, "sha256": sha256_hex(PRICES_FIXTURE.read_bytes())},
            "recipes": ids,
            "combinations": sorted(combinations),
            "pdf_combinations": [c for c in sorted(combinations) if c in PDF_COMBINATIONS],
        },
        "datasets": datasets,
        "reference_data": reference_digests(),
        "variants": variants,
        "disclaimer": DISCLAIMER,
    }


# --- comparing and writing --------------------------------------------------------------------

def compare(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """Differences between two digest documents, naming the recipe, combination and output."""
    diffs: List[str] = []
    for key in ("format_version", "inputs", "datasets"):
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key} differs: expected {expected.get(key)!r}, got {actual.get(key)!r}")
    eref, aref = expected.get("reference_data", {}), actual.get("reference_data", {})
    for f in sorted(set(eref) | set(aref)):
        e, a = eref.get(f, {}), aref.get(f, {})
        for k in sorted(set(e) | set(a)):
            if e.get(k) != a.get(k):
                diffs.append(f"{f} {k} differs")
    ev = {(v["recipe"], v["combination"]): v["outputs"] for v in expected.get("variants", [])}
    av = {(v["recipe"], v["combination"]): v["outputs"] for v in actual.get("variants", [])}
    for key in sorted(set(ev) | set(av)):
        name = f"{key[0]} {key[1]}"
        if key not in av:
            diffs.append(f"{name}: variant missing")
            continue
        if key not in ev:
            diffs.append(f"{name}: unexpected variant")
            continue
        e, a = ev[key], av[key]
        for out in sorted(set(e) | set(a)):
            if out not in a:
                diffs.append(f"{name}: {out} missing")
            elif out not in e:
                diffs.append(f"{name}: {out} unexpected")
            elif e[out] != a[out]:
                diffs.append(f"{name}: {out} differs (expected {e[out]}, got {a[out]})")
    return diffs


_LEAF = re.compile(r'\{\n(?:[ ]+"[^"\n]*": (?:"[^"\n]*"|-?\d+|true|false|null),?\n)+[ ]*\}')


def to_text(doc: Dict[str, Any]) -> str:
    """Indented JSON with each innermost object (a digest entry) on one line."""
    text = json.dumps(doc, indent=2, ensure_ascii=False)

    def one_line(m: re.Match) -> str:
        items = [x.strip().rstrip(",") for x in m.group(0)[1:-1].strip().split("\n")]
        return "{" + ", ".join(items) + "}"

    return _LEAF.sub(one_line, text) + "\n"
