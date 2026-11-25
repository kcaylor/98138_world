"""The packaged Winkel tripel template, data/templates/winkel-tripel.json (feature 016, T037/T038;
contracts/template-file.md, research R2-R5).

Written by ``PYTHONPATH=tools python -m maptemplates write winkel-tripel`` and reproducible with
``build winkel-tripel --check`` (the end-to-end check is in tests/unit/tools/test_maptemplates.py,
run when pyproj and the cached ETOPO 2022 file are present). The owner confirmed it as is, with no
corrections, on 2026-11-24 (T039 -> T081); it records only the role "project owner" and the date.
"""

import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

import lego_image_processor.templates as templates
from lego_image_processor.datasets import registry
from lego_image_processor.templates import load_template_file, winkel
from lego_image_processor.templates.board import board_counts

PACKAGE = Path(templates.__file__).resolve().parent.parent / "data" / "templates" / "winkel-tripel.json"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture(scope="module")
def doc():
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def template():
    return load_template_file(PACKAGE)


def test_package_file_loads(template):
    assert template.id == "winkel-tripel" and not template.is_kit
    assert template.path == PACKAGE.resolve()
    assert template.status == ("confirmed" if template.confirmation else "unconfirmed")
    assert template.buildable == (template.confirmation is not None)


def test_derived_counts_equal_the_recorded_ones(doc, template):
    assert board_counts(doc["classes"]) == doc["counts"] == template.counts
    c = doc["counts"]
    assert c["land"] + c["ocean"] + c["margin"] == 128 * 80
    assert set(c["corners"]) == {"top-left", "top-right", "bottom-left", "bottom-right"}
    assert c["modules"]["full"] + c["modules"]["partial"] + c["modules"]["empty"] == 40


def test_check_points_pass(doc):
    pts = np.array(doc["projection"]["check_points"], dtype=float)
    assert [tuple(p[:2]) for p in pts.tolist()] == [tuple(map(float, p)) for p in winkel.CHECK_POINTS]
    x, y = winkel.forward(pts[:, 0], pts[:, 1], doc["projection"]["lat_1"], doc["projection"]["lon_0"])
    assert np.max(np.abs(x - pts[:, 2])) < 1e-9 and np.max(np.abs(y - pts[:, 3])) < 1e-9


def test_projection_board_parts_frame(doc):
    p = doc["projection"]
    assert p["name"] == "winkel-tripel" and p["proj"] == "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"
    assert (p["lat_1"], p["lon_0"]) == (50.4598, 11.1)
    assert p["fit"] == winkel.fit(128, 80)                     # the exact extent (research R2)
    assert p["fit"]["extent"][1] == pytest.approx((math.pi / 2) * (1 + math.cos(math.radians(50.4598))))
    assert doc["board"] == {"modules": [8, 5], "module": 16, "width": 128, "height": 80, "pitch_mm": 8.0}
    assert doc["parts"] == {"land": "6141", "ocean": "98138", "margin": "3070b"}
    assert doc["frame"] == {"kit": "31203", "arrangements": ["A"], "source": "kit_31203_arrangements.json"}


def test_locations_exactly_on_land_and_ocean(doc):
    classes = np.array([list(r) for r in doc["classes"]])
    for axis, limit in (("lat", 90), ("lon", 180)):
        a = np.array([[np.nan if v is None else v for v in row] for row in doc["locations"][axis]], dtype=float)
        assert np.isnan(a[classes == "M"]).all() and np.isfinite(a[classes != "M"]).all()
        assert (np.abs(a[classes != "M"]) <= limit).all()
        assert np.allclose(a[classes != "M"], np.round(a[classes != "M"], 4), rtol=0, atol=1e-12)


def test_confirmation_is_null_or_exactly_role_and_date(doc):
    conf = doc["confirmation"]
    if conf is None:
        return
    assert set(conf) == {"role", "date"} and conf["role"] == "project owner"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", conf["date"])


def test_confirmed_by_the_project_owner_as_is(doc, template):
    """T039/T081: confirmed on 2026-11-24 with no corrections, so the classes are the generated ones
    (the layout digest of T037, which the ice file records)."""
    assert doc["confirmation"] == {"role": "project owner", "date": "2026-11-24"}
    assert doc["corrections"] == []
    assert template.status == "confirmed" and template.buildable
    assert template.layout_sha256 == "389963b5a48c14c21d80a7d1486e0792567923339e47cb4c2018414dd15ba67a"


def _keys(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + (k,)
            yield from _keys(v, path + (k,))
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v, path)


def test_no_personal_name(doc):
    text = PACKAGE.read_text(encoding="utf-8")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)          # no email address
    names = {"author", "authors", "by", "decided_by", "confirmed_by", "reviewed_by", "owner", "user", "email",
             "person", "maintainer"}
    assert not [p for p in _keys(doc) if p[-1] in names]
    assert all(set(c) == {"row", "col", "class", "reason"} for c in doc["corrections"])
    assert [p for p in _keys(doc) if p[-1] == "name"] == [("projection", "name")]


def test_source_dataset_agrees_with_the_registry(doc, template):
    entry = registry.load_registry(registry.DATA_DIR / "datasets.json").get("etopo2022-surface-10m")
    assert doc["source"]["dataset"] == {"id": entry.id, "version": entry.version, "url": entry.url,
                                        "sha256": entry.sha256, "citation": entry.citation,
                                        "license": entry.license}
    assert template.dataset.id == "etopo2022-surface-10m" and template.dataset.doi == entry.doi


def test_generated_by_the_tool_with_the_studys_method(doc):
    src = doc["source"]
    assert src["generator"] == "cli/tools/maptemplates"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", src["generated_on"])
    m = src["method"]
    assert (m["supersample"], m["on_globe_share"], m["land_share"], m["land_rule"], m["round_trip_tolerance"]) == \
        (4, 0.5, 0.5, "elevation > 0 m", 1e-6)
    assert "spherical mean" in m["location_rule"]
    assert src["software"]["pyproj"].startswith("3.7.") and src["software"]["proj"]
    assert src["disclaimer"] == doc["disclaimer"] == DISCLAIMER


def test_corrections_are_applied_to_the_classes(doc):
    last = {}
    for c in doc["corrections"]:
        last[(c["row"], c["col"])] = c["class"]
    code = {"land": "L", "ocean": "O", "margin": "M"}
    assert all(doc["classes"][r][col] == code[k] for (r, col), k in last.items())


def test_confirmed_winkel_uses_the_package_file(confirmed_winkel, template):
    """The package file is confirmed (T081), so ``confirmed_winkel`` is the package template; a copy
    with a test confirmation would have the same layout (the digest leaves the confirmation out)."""
    assert confirmed_winkel.buildable and confirmed_winkel.path == template.path
    assert confirmed_winkel.layout_sha256 == template.layout_sha256
    assert confirmed_winkel.counts == template.counts and confirmed_winkel.classes == template.classes
