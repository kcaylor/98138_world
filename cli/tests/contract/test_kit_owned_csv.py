"""Kit `parts list` and `parts export` with --owned and --missing CSVs are byte-for-byte main's
(feature 016 T110; SC-001, FR-014).

``tests/kit_owned_csv.py`` runs the same commands on the official 31203 design layout with CSVs
that list the square tile 3070b, its other catalog numbers (3070, 30039, ...), a 3070b element and
a BrickLink number of a kit part. The expected exit codes, stdout, stderr and files were written by
that harness from an unmodified checkout of main 6038d9c (``tests/fixtures/golden/kit_owned_csv.json``
and its ``.source.json``), where 3070b rows are ignored and counted as rows for other parts. The
fixture is never regenerated from feature 016 code.
Not affiliated with or endorsed by The LEGO Group.
"""

import hashlib
import json
from pathlib import Path

from ..kit_owned_csv import CASES, DISCLAIMER, INPUTS, compare, run_cases

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "kit_owned_csv.json"
HARNESS = Path(__file__).resolve().parents[1] / "kit_owned_csv.py"


def test_fixture_is_mains_output_of_this_harness():
    meta = json.loads(GOLDEN.with_name("kit_owned_csv.source.json").read_text(encoding="utf-8"))
    assert meta["code"]["commit"] == "6038d9c" and meta["disclaimer"] == DISCLAIMER
    assert meta["sha256"] == hashlib.sha256(GOLDEN.read_bytes()).hexdigest()
    assert meta["harness"]["sha256"] == hashlib.sha256(HARNESS.read_bytes()).hexdigest()
    doc = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert doc["inputs"] == INPUTS and [c[0] for c in CASES] == list(doc["cases"])
    assert doc["disclaimer"] == DISCLAIMER


def test_main_ignored_the_square_tile_rows():
    """What main did, read from the fixture: 9 + 2 rows ignored, no error for 3070 and the like."""
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    owned = json.loads(cases["list-json"]["stdout"])["owned"]
    assert owned["ignored_rows"] == 11
    assert "11 row(s) for other parts ignored" in cases["list-table"]["stdout"]
    assert cases["export-owned-only"]["exit_code"] == 0
    assert cases["list-elements"]["exit_code"] == 1 and "element '307026'" in cases["list-elements"]["stderr"]


def test_kit_owned_csv_outputs_match_main(tmp_path):
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    diffs = compare(expected, run_cases(tmp_path / "run"))
    assert not diffs, (f"{len(diffs)} difference(s) from {GOLDEN.name} (inputs and outputs kept in "
                       f"{tmp_path / 'run'}):\n" + "\n".join(diffs))
