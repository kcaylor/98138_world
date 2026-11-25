"""Shared fixtures: a small site output built offline by the prebuild itself (FR-016).

`official-31203` needs no dataset; `ocean-sst` is built from the CLI's small derived ERSST
fixture (cli/tests/fixtures/datasets), placed in a temporary cache behind a registry whose entry
points at it, as the CLI's own tests do. Prices come from the CLI's synthetic fixture snapshot
(cli/tests/fixtures/prices, feature 011) with a fixed staleness reference date. No test uses the
network.

Feature 016 (T084): the whole session builds on a confirmed ``winkel-tripel`` template
(``confirmed_template_dir``), with the CLI's shared helper ``cli/tools/maptemplates/testing.py``
(the web suite cannot use the CLI conftest fixtures). Until the owner confirms the package file
(T039 -> T081) it is a ``confirmed_copy`` of it with the test confirmation; so the small site gains
a Winkel variant of ocean-sst, and the living-planet and rainfall sites one each. Kit variants
stay as the web kit golden says (``test_kit_golden.py``).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CLI_FIXTURES = REPO / "cli" / "tests" / "fixtures" / "datasets"
PRICES = REPO / "cli" / "tests" / "fixtures" / "prices" / "bricklink_price_guide.json"
TEMPLATE_FIXTURES = REPO / "cli" / "tests" / "fixtures" / "templates"
TODAY = date(2026, 12, 5)     # 4 days after the fixture snapshot
SMALL_MAPS = ("official-31203", "ocean-sst", "ocean-el-nino")
TEST_CONFIRMATION_DATE = "2026-11-23"

if str(REPO / "cli" / "tools") not in sys.path:   # tools/maptemplates/testing.py (T025)
    sys.path.insert(0, str(REPO / "cli" / "tools"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def confirmed_template_dir(tmp_path_factory):
    """A buildable ``winkel-tripel`` for the whole session, as the CLI's ``confirmed_winkel``:

    - the package file is confirmed: it is used as is (no copy);
    - it exists but is unconfirmed: a ``confirmed_copy`` with the test confirmation, with its ice
      file (the layout digest leaves the confirmation out, so the ice file stays valid);
    - it does not exist: the committed synthetic fixture template and its ice file.

    Yields the template directory in use."""
    import lego_image_processor.templates as templates
    from maptemplates.testing import confirmed_copy, use_template_dir

    package = templates.TEMPLATE_DIR / "winkel-tripel.json"
    if package.exists() and json.loads(package.read_text(encoding="utf-8")).get("confirmation"):
        yield templates.TEMPLATE_DIR
        return
    src = templates.TEMPLATE_DIR if package.exists() else TEMPLATE_FIXTURES
    d = tmp_path_factory.mktemp("templates-confirmed")
    confirmed_copy(src, d, TEST_CONFIRMATION_DATE)
    with use_template_dir(d):
        yield d


@pytest.fixture(scope="session")
def unconfirmed_template_dir(tmp_path_factory):
    """The same template without a confirmation (Principle I: it must give no variants)."""
    import lego_image_processor.templates as templates

    d = tmp_path_factory.mktemp("templates-unconfirmed")
    src = Path(templates.TEMPLATE_DIR)
    doc = json.loads((src / "winkel-tripel.json").read_text(encoding="utf-8"))
    doc["confirmation"] = None
    (d / "winkel-tripel.json").write_text(json.dumps(doc), encoding="utf-8")
    ice = src / "winkel-tripel-ice.json"
    if ice.exists():
        shutil.copyfile(ice, d / ice.name)
    return d


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
        elif row["id"] == "mod17a3-npp-mean-2000-2015":  # feature 012: 1-degree fixture, 2x2 blocks
            f = CLI_FIXTURES / "mod17a3_npp_1deg.tif"
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f),
                       grid={**row.get("grid", {}), "block": 2})
            files[row["id"]] = f
        elif row["id"] == "modis-aqua-chla-2013-2024":  # feature 012: content checksum of the fixture
            from lego_image_processor.datasets.readers import netcdf3_content_sha256

            f = CLI_FIXTURES / "modis_chla_4deg_6mo.nc"
            row.update(filename=f.name, size=f.stat().st_size,
                       content_sha256=netcdf3_content_sha256(f, "chlor_a"))
            files[row["id"]] = f
        elif row["id"] == "gpcp-v23-ltm-1991-2020":  # feature 013: 10-degree netCDF-4 fixture
            f = CLI_FIXTURES / "gpcp_v23_ltm_10deg.nc"
            row.update(filename=f.name, size=f.stat().st_size, sha256=_sha(f))
            files[row["id"]] = f
        elif row["id"] == "nsidc-cdr-v6-seaice-minimum-1991-2020":  # feature 013: 4 of the 60 files
            fs = sorted(CLI_FIXTURES.glob("nsidc_cdr_v6_*_4x.nc"))
            row["files"] = [{"url": f"https://noaadata.apps.nsidc.org/NOAA/G02202_V6/fixture/{f.name}",
                             "size": f.stat().st_size, "sha256": _sha(f)} for f in fs]
            row["size"] = sum(f.stat().st_size for f in fs)
            files[row["id"]] = fs
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
        if isinstance(f, list):  # a multi-file entry: dest is its directory
            dest.mkdir(parents=True, exist_ok=True)
            for x in f:
                shutil.copyfile(x, dest / x.name)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)
    yield cache
    mp.undo()


@pytest.fixture(scope="session")
def site_dir(tmp_path_factory, fixture_datasets, confirmed_template_dir) -> Path:
    from web98138.prebuild import build_site

    out = tmp_path_factory.mktemp("site")
    build_site(out, maps=SMALL_MAPS, cache_dir=fixture_datasets, echo=lambda *a: None,
               prices_path=PRICES, today=TODAY)
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


@pytest.fixture(scope="session")
def living_site(tmp_path_factory, fixture_datasets, confirmed_template_dir) -> Path:
    """Feature 012: the living-planet map alone (three datasets, A, B and C) from the fixtures."""
    from web98138.prebuild import build_site

    out = tmp_path_factory.mktemp("living")
    build_site(out, maps=("living-planet",), cache_dir=fixture_datasets, echo=lambda *a: None,
               prices_path=PRICES, today=TODAY)
    return out


@pytest.fixture(scope="session")
def rainfall_site(tmp_path_factory, fixture_datasets, confirmed_template_dir) -> Path:
    """Feature 013: the rainfall map alone (GPCP netCDF-4 and the multi-file NSIDC entry)."""
    from web98138.prebuild import build_site

    out = tmp_path_factory.mktemp("rainfall")
    build_site(out, maps=("rainfall",), cache_dir=fixture_datasets, echo=lambda *a: None,
               prices_path=PRICES, today=TODAY)
    return out


@pytest.fixture()
def rainfall_client(rainfall_site):
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    with TestClient(create_app(rainfall_site), base_url="https://98138.world") as c:
        yield c


@pytest.fixture()
def living_client(living_site):
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    with TestClient(create_app(living_site), base_url="https://98138.world") as c:
        yield c
