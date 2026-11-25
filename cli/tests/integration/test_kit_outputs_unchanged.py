"""Kit outputs byte-for-byte unchanged (feature 016, T007; SC-001, research R9).

Rebuilds every bundled recipe x A, B, C on the kit from the dataset fixtures through the same
harness that wrote tests/fixtures/golden/kit_outputs.json (``maptemplates kit-golden --fixtures``)
from an unmodified checkout of main (commit 6038d9c; re-based once from af3ce57 when main changed
the previews), and compares every digest. A difference is a bug in the new code: the golden file is
never regenerated from feature 016 code. Feature 017 (map stickers) regenerated it once, on the
merge of 016 into 017 (017 task T054): its approved sticker tables change the bundled recipes'
checksums, and only after the harness on the recipes' af3ce57 bytes reproduced the file exactly
(kit_outputs.source.json ``regenerated``). On failure the rebuilt outputs stay in the
test's temporary directory (named in the message) for diffing against a ``main`` checkout.
"""

from __future__ import annotations

import json
from pathlib import Path

from maptemplates import golden

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "kit_outputs.json"


def test_golden_file_is_the_fixture_digest_set():
    doc = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert doc["inputs"]["datasets"] == "fixtures"
    assert doc["inputs"]["combinations"] == ["A", "B", "C"]
    assert len(doc["variants"]) == 24
    assert doc["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
    meta = json.loads(GOLDEN.with_name("kit_outputs.source.json").read_text(encoding="utf-8"))
    assert meta["code"]["commit"] == "6038d9c"   # re-based from af3ce57 on 2026-11-23 (previews only)
    assert meta["disclaimer"] == doc["disclaimer"]


def test_kit_outputs_unchanged(tmp_path):
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    actual = golden.kit_golden(fixtures=True, keep=tmp_path / "kit")
    diffs = golden.compare(expected, actual)
    assert not diffs, (f"{len(diffs)} kit output digest(s) differ from {GOLDEN.name} (outputs kept in "
                       f"{tmp_path / 'kit'}):\n" + "\n".join(diffs))
