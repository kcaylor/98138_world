"""FR-025: no downloaded dataset is committed; fixtures are small and documented."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2]
REPO = CLI_DIR.parent
FIXTURES = CLI_DIR / "tests" / "fixtures" / "datasets"
DATA_SUFFIXES = {".nc", ".dods", ".npy", ".csv", ".gz", ".grib", ".tif", ".h5", ".zip"}


def _tracked():
    if shutil.which("git") is None or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "cli"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
    return [REPO / f for f in out if (REPO / f).is_file()]


def test_no_large_data_files():
    big = [p for p in _tracked() if p.suffix.lower() in DATA_SUFFIXES and p.stat().st_size > 1_000_000]
    assert big == []


def test_fixtures_small_and_documented():
    files = [p for p in FIXTURES.iterdir() if p.suffix != ".json"]
    assert files
    # Budget raised from 300 kB to 450 kB for the two feature 012 fixtures (research R6), and to
    # 540 kB for the five feature 013 netCDF-4 fixtures (specs/013-rainfall research R7).
    assert sum(p.stat().st_size for p in files) < 540_000
    for p in files:
        meta = json.loads((FIXTURES / f"{p.stem}.source.json").read_text(encoding="utf-8"))
        # a source pinned by content checksum (012) records that instead of a file SHA-256
        source = meta["source_sha256"] or meta.get("source_content_sha256", "")
        assert meta["dataset"] and meta["license"] and len(source) == 64
        assert meta["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."
