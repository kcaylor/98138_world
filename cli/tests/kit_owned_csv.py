"""Owned and missing CSVs on a kit layout, as main reads them (feature 016 T110; SC-001, FR-014).

On main (commit 6038d9c) the parts commands know two map parts, 6141 and 98138, so a Rebrickable
CSV row for the square tile 3070b, or for one of its other catalog numbers (3070, 30039, 35403,
39727, 53836, 112412), is a row "for other parts": ignored and counted. Feature 016 adds 3070b for
template margins; on a kit layout (no square tiles) those rows must still be ignored and counted
exactly as before, and every kit output of ``parts list`` and ``parts export`` must stay byte for
byte the same.

``run_cases()`` writes the official 31203 design as a layout (``generated_at`` fixed) and the CSVs
in ``INPUTS`` into a directory, then runs each command in ``CASES`` there with relative paths
through ``click.testing.CliRunner``, and returns every exit code, stdout, stderr and written file.
It imports only modules present at main 6038d9c, so the same file runs against a checkout of main:
``tests/fixtures/golden/kit_owned_csv.json`` was written that way (see its ``.source.json``) and
``tests/contract/test_kit_owned_csv.py`` compares this feature's results with it. Never
regenerate the fixture from feature 016 code.

Run as a script to write the fixture: ``python tests/kit_owned_csv.py --out FILE``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

FORMAT_VERSION = "1"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
LAYOUT_NAME = "official.json"
FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
_GENERATED_AT = re.compile(r'"generated_at": "[^"\n]*"')

# Rebrickable import CSVs (Part,Color,Quantity or Element,Quantity). Colors: 0 Black, 1 Blue,
# 15 White, 322 Medium Azur. 3070 ... 112412 are 3070b's BrickLink and LEGO numbers
# (part_numbers.json of feature 016); 3001 is another part.
INPUTS: Dict[str, str] = {
    "owned.csv": ("Part,Color,Quantity\n"
                  "6141,15,10\n"
                  "98138,322,25\n"
                  "3070b,0,40\n"
                  "3070b,15,5\n"
                  "3070,0,3\n"
                  "30039,1,2\n"
                  "35403,0,1\n"
                  "39727,0,1\n"
                  "53836,0,1\n"
                  "112412,0,1\n"
                  "3001,15,4\n"),
    "missing.csv": ("Part,Color,Quantity\n"
                    "6141,15,7\n"
                    "98138,322,3\n"
                    "3070b,0,2\n"
                    "3070,0,1\n"),
    "square-only.csv": "Part,Color,Quantity\n3070b,0,12\n",
    # a 3070b element (Black square tile 307026) next to a White plate element
    "elements.csv": "Element,Quantity\n614101,4\n307026,6\n",
    # a BrickLink number of a kit part: the error lists the Rebrickable part numbers
    "bricklink-numbers.csv": "Part,Color,Quantity\n4073,15,1\n",
}

TOPUP = ["--kits", "1", "--owned", "owned.csv", "--missing", "missing.csv"]
EXPORT_FILES = ("wanted.xml", "rebrickable.csv")

# (name, arguments, files the command may write)
CASES: List[Tuple[str, List[str], Tuple[str, ...]]] = [
    ("list-table", ["parts", "list", LAYOUT_NAME] + TOPUP, ()),
    ("list-all-columns", ["parts", "list", LAYOUT_NAME, "--all-columns"] + TOPUP, ()),
    ("list-json", ["parts", "list", LAYOUT_NAME, "--format", "json"] + TOPUP, ()),
    ("list-owned-only", ["parts", "list", LAYOUT_NAME, "--owned", "owned.csv"], ()),
    ("list-missing-only-json", ["parts", "list", LAYOUT_NAME, "--format", "json", "--kits", "2",
                                "--missing", "missing.csv"], ()),
    ("list-square-only", ["parts", "list", LAYOUT_NAME, "--kits", "1", "--owned", "square-only.csv",
                          "--missing", "square-only.csv"], ()),
    ("export", ["parts", "export", LAYOUT_NAME, "--bricklink", "wanted.xml", "--rebrickable",
                "rebrickable.csv"] + TOPUP, EXPORT_FILES),
    ("export-owned-only", ["parts", "export", LAYOUT_NAME, "--bricklink", "wanted.xml",
                           "--rebrickable", "rebrickable.csv", "--owned", "owned.csv"], EXPORT_FILES),
    ("export-missing", ["parts", "export", LAYOUT_NAME, "--bricklink", "wanted.xml", "--rebrickable",
                        "rebrickable.csv", "--kits", "1", "--missing", "missing.csv"], EXPORT_FILES),
    ("list-elements", ["parts", "list", LAYOUT_NAME, "--owned", "elements.csv"], ()),
    ("list-bricklink-numbers", ["parts", "list", LAYOUT_NAME, "--owned", "bricklink-numbers.csv"], ()),
]


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def layout_text() -> str:
    """The official 31203 design as layout JSON, ``generated_at`` fixed so the bytes repeat."""
    from lego_image_processor.kit import load_official_design

    text = load_official_design().to_layout().to_json()
    return _GENERATED_AT.sub(f'"generated_at": "{FIXED_GENERATED_AT}"', text, count=1)


def write_inputs(root: Path) -> None:
    (root / LAYOUT_NAME).write_text(layout_text(), encoding="utf-8")
    for name, text in INPUTS.items():
        (root / name).write_text(text, encoding="utf-8")


def run_cases(root: Optional[Path] = None) -> Dict[str, Any]:
    """Every case's exit code, stdout, stderr and written files (null when not written)."""
    from click.testing import CliRunner

    from lego_image_processor.cli.main import cli

    with contextlib.ExitStack() as stack:
        if root is None:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        write_inputs(root)
        cases: Dict[str, Any] = {}
        runner = CliRunner()
        with _chdir(root):
            for name, args, files in CASES:
                for f in files:
                    Path(f).unlink(missing_ok=True)
                r = runner.invoke(cli, args, catch_exceptions=False)
                cases[name] = {
                    "args": list(args),
                    "exit_code": r.exit_code,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "files": {f: (Path(f).read_text(encoding="utf-8") if Path(f).is_file() else None)
                              for f in files},
                }
    return {"format_version": FORMAT_VERSION, "layout": LAYOUT_NAME,
            "generated_at": FIXED_GENERATED_AT, "inputs": dict(INPUTS), "cases": cases,
            "disclaimer": DISCLAIMER}


def to_text(doc: Dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def compare(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """One line per difference: inputs, a missing or extra case, or a changed field of a case."""
    diffs = []
    for key in ("format_version", "layout", "generated_at", "inputs", "disclaimer"):
        if expected.get(key) != actual.get(key):
            diffs.append(f"{key}: the harness changed; rewrite the fixture from main, not from this code")
    for name in sorted(set(expected["cases"]) | set(actual["cases"])):
        e, a = expected["cases"].get(name), actual["cases"].get(name)
        if e is None or a is None:
            diffs.append(f"{name}: {'missing' if a is None else 'not in the fixture'}")
            continue
        for field in ("args", "exit_code", "stdout", "stderr", "files"):
            if e[field] != a[field]:
                diffs.append(f"{name}.{field}: expected {e[field]!r}, got {a[field]!r}")
    return diffs


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Write the kit owned-CSV outputs (run on main only).")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.write_text(to_text(run_cases()), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(DISCLAIMER)


if __name__ == "__main__":
    main()
