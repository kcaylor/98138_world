"""FR-002: the instructions PDF is never committed to the repository or shipped in the package."""

import shutil
import subprocess
from pathlib import Path

import pytest

CLI_DIR = Path(__file__).resolve().parents[2]
PACKAGE_DIR = CLI_DIR / "src" / "lego_image_processor"
REPO_ROOT = CLI_DIR.parent


def test_no_pdf_in_package_tree():
    assert sorted(p.relative_to(PACKAGE_DIR) for p in PACKAGE_DIR.rglob("*")
                  if p.suffix.lower() == ".pdf") == []


def test_no_pdf_tracked_by_git():
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True,
                             check=True).stdout.splitlines()
    assert [f for f in tracked if f.lower().endswith(".pdf")] == []


def test_gitignore_ignores_pdfs():
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        pytest.skip("no repository .gitignore (installed package)")
    assert "*.pdf" in gitignore.read_text(encoding="utf-8").splitlines()
