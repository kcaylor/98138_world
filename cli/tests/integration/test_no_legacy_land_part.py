"""SC-006 / US1-5: the old land part (3062b, part type "brick") is gone.

Allowed exceptions: the schema 1.0 rejection fixture and this test (see run-state.md Decisions).
"""

import re
from pathlib import Path

CLI_DIR = Path(__file__).resolve().parents[2]
REPO = CLI_DIR.parent

PATTERN = re.compile(r"3062b|land_brick|\"brick\"|'brick'")
SEARCH = [CLI_DIR / "src", CLI_DIR / "tests", CLI_DIR / "tools", CLI_DIR / "README.md",
          REPO / "README.md", REPO / "docs"]
EXCLUDE = {
    CLI_DIR / "tests" / "fixtures" / "layouts" / "legacy_v1_layout.json",
    Path(__file__).resolve(),
}
TEXT_SUFFIXES = {".py", ".json", ".csv", ".md", ".txt", ".toml", ".cfg", ".yaml", ".yml"}


def _files():
    for root in SEARCH:
        if root.is_file():
            yield root
        elif root.is_dir():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
                    yield p


def test_no_legacy_land_part():
    hits = []
    for path in _files():
        if path.resolve() in EXCLUDE:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if PATTERN.search(line):
                hits.append(f"{path.relative_to(REPO)}:{n}: {line.strip()[:100]}")
                if len(hits) > 20:
                    break
    assert not hits, "legacy land part found:\n" + "\n".join(hits)


def test_legacy_fixture_still_has_old_values():
    text = (CLI_DIR / "tests" / "fixtures" / "layouts" / "legacy_v1_layout.json").read_text()
    assert "3062b" in text and '"schema_version": "1.0"' in text
