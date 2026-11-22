"""Shared fixtures: a small site output built offline by the prebuild itself (FR-016).

`official-31203` needs no dataset; `ocean-sst` is built from the CLI's small derived ERSST
fixture (cli/tests/fixtures/datasets), placed in a temporary cache behind a registry whose entry
points at it, as the CLI's own tests do. No test uses the network.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

CLI_FIXTURES = Path(__file__).resolve().parents[2] / "cli" / "tests" / "fixtures" / "datasets"
SMALL_MAPS = ("official-31203", "ocean-sst", "ocean-el-nino")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="session")
def fixture_datasets(tmp_path_factory):
    """Point the dataset registry at the CLI's fixtures; return the cache directory."""
    from lego_image_processor.datasets import cached_path, get_entry
    from lego_image_processor.datasets import registry as reg

    root = tmp_path_factory.mktemp("datasets")
    data = json.loads(reg.REGISTRY_PATH.read_text(encoding="utf-8"))
    files = {}
    for row in data["datasets"]:
        if row["id"] == "ersst-v5-ltm-1991-2020":
            f = CLI_FIXTURES / "ersst_v5_annual_2deg.nc"
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f),
                       variables={"sst": {"units": "degC"}})
            files[row["id"]] = f
        elif row["id"] == "ersst-v5-1997-12":  # feature 009: the per-month fixture (int16 ssta)
            f = CLI_FIXTURES / "ersst_v5_199712_ssta.nc"
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f))
            files[row["id"]] = f
        elif row["id"] == "etopo2022-surface-10m":
            f = CLI_FIXTURES / "etopo2022_1deg.npy"
            row.update(format="npy", filename=f.name, size=f.stat().st_size, sha256=_sha(f),
                       grid={"lat": [-90, 90], "lon": [-180, 180]})
            files[row["id"]] = f
    registry = root / "datasets.json"
    registry.write_text(json.dumps(data), encoding="utf-8")
    mp = pytest.MonkeyPatch()
    mp.setattr(reg, "REGISTRY_PATH", registry)
    cache = root / "cache"
    for did, f in files.items():
        dest = cached_path(get_entry(did), cache)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)
    yield cache
    mp.undo()


@pytest.fixture(scope="session")
def site_dir(tmp_path_factory, fixture_datasets) -> Path:
    from web98138.prebuild import build_site

    out = tmp_path_factory.mktemp("site")
    build_site(out, maps=SMALL_MAPS, cache_dir=fixture_datasets, echo=lambda *a: None)
    return out


@pytest.fixture(scope="session")
def manifest(site_dir) -> dict:
    return json.loads((site_dir / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture()
def client(site_dir):
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    with TestClient(create_app(site_dir), base_url="https://98138.world") as c:
        yield c
