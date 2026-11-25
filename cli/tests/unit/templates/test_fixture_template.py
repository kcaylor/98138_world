"""The committed synthetic template fixture (feature 016, T025): ``tools/maptemplates/testing.py``
regenerates it byte for byte, and its ``.source.json`` files describe it."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from maptemplates import testing

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "templates"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
FILES = ("winkel-tripel.json", "winkel-tripel-ice.json")


def test_fixture_is_reproducible(tmp_path):
    written = testing.write_synthetic_template(tmp_path)
    assert sorted(p.name for p in written) == sorted(FILES)
    for name in FILES:
        assert (tmp_path / name).read_bytes() == (FIXTURES / name).read_bytes(), name


@pytest.mark.parametrize("name", FILES)
def test_source_json_describes_the_fixture(name):
    path = FIXTURES / name
    src = json.loads((FIXTURES / name.replace(".json", ".source.json")).read_text(encoding="utf-8"))
    assert src["fixture"] == name
    assert src["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "maptemplates" in src["generator"]
    assert src["disclaimer"] == DISCLAIMER
    assert "synthetic" in src["what"].lower()


def test_fixture_is_small_and_one_board_row_per_line():
    text = (FIXTURES / "winkel-tripel.json").read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) < 250_000
    lines = text.splitlines()
    class_rows = [l for l in lines if l.strip().strip('",') and set(l.strip().strip('",')) <= set("LOM")
                  and len(l.strip().strip('",')) == 128]
    assert len(class_rows) == 80


def test_synthetic_document_shape():
    doc = json.loads((FIXTURES / "winkel-tripel.json").read_text(encoding="utf-8"))
    assert doc["id"] == "winkel-tripel" and doc["format_version"] == "1"
    assert doc["confirmation"] == {"role": "project owner", "date": "2026-11-23"}
    assert doc["parts"] == {"land": "6141", "ocean": "98138", "margin": "3070b"}
    assert doc["projection"]["proj"] == "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1"
    assert len(doc["projection"]["check_points"]) == 24
    classes = np.array([list(r) for r in doc["classes"]])
    lat = np.array(doc["locations"]["lat"], dtype=float)
    assert classes.shape == (80, 128) and lat.shape == (80, 128)
    assert (classes == "L").sum() > 1000 and (classes == "O").sum() > 3000 and (classes == "M").sum() > 1000
    assert np.isnan(lat[classes == "M"]).all() and np.isfinite(lat[classes != "M"]).all()
    # One recorded correction, already applied to the classes.
    (c,) = doc["corrections"]
    assert classes[c["row"], c["col"]] == {"land": "L", "ocean": "O", "margin": "M"}[c["class"]]
    assert "synthetic" in doc["title"].lower() and "synthetic" in doc["description"].lower()


def test_synthetic_ice_follows_its_rules():
    doc = json.loads((FIXTURES / "winkel-tripel.json").read_text(encoding="utf-8"))
    ice = json.loads((FIXTURES / "winkel-tripel-ice.json").read_text(encoding="utf-8"))
    from lego_image_processor.templates.digest import layout_sha256

    assert ice["format_version"] == "1" and ice["template_id"] == "winkel-tripel"
    assert ice["grid"] == {"width": 128, "height": 80,
                           "coordinates": "board, row-major index = row * 128 + column"}
    assert ice["source"]["template_layout_sha256"] == layout_sha256(doc)
    assert ice["source"]["disclaimer"] == DISCLAIMER
    classes = np.array([list(r) for r in doc["classes"]]).ravel()
    lat = np.array(doc["locations"]["lat"], dtype=float).ravel()
    land = sorted(int(i) for i in np.flatnonzero((classes == "L") & (lat < -60)))
    sea = sorted(int(i) for i in np.flatnonzero((classes == "O") & (np.abs(lat) > 75)))
    assert ice["land_ice"] == {"count": len(land), "cells": land} and land
    assert ice["sea_ice"] == {"count": len(sea), "cells": sea} and sea


def test_inverse_round_trips_the_forward_formula():
    from lego_image_processor.templates import winkel

    rng = np.random.default_rng(5)
    lon = rng.uniform(-180, 180, 5000)
    lat = np.degrees(np.arcsin(rng.uniform(-0.999, 0.999, 5000)))
    x, y = winkel.forward(lon, lat)
    la, lo = testing.inverse(x, y)
    assert np.max(np.abs(la - lat)) < 1e-9
    dlon = (lo - lon + 540) % 360 - 180
    assert np.max(np.abs(dlon * np.cos(np.radians(lat)))) < 1e-9


def test_confirmed_copy_sets_a_test_confirmation(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    doc = json.loads((FIXTURES / "winkel-tripel.json").read_text(encoding="utf-8"))
    doc["confirmation"] = None
    (src / "winkel-tripel.json").write_text(json.dumps(doc), encoding="utf-8")
    (src / "winkel-tripel-ice.json").write_bytes((FIXTURES / "winkel-tripel-ice.json").read_bytes())
    dst = tmp_path / "dst"
    out = testing.confirmed_copy(src, dst, "2026-11-23")
    assert out == dst / "winkel-tripel.json"
    copied = json.loads(out.read_text(encoding="utf-8"))
    assert copied["confirmation"] == {"role": "project owner", "date": "2026-11-23"}
    assert {k: v for k, v in copied.items() if k != "confirmation"} == \
        {k: v for k, v in doc.items() if k != "confirmation"}
    assert (dst / "winkel-tripel-ice.json").read_bytes() == (src / "winkel-tripel-ice.json").read_bytes()


def test_confirmed_copy_without_an_ice_file(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "winkel-tripel.json").write_bytes((FIXTURES / "winkel-tripel.json").read_bytes())
    out = testing.confirmed_copy(src, tmp_path / "dst", "2027-01-02")
    assert json.loads(out.read_text(encoding="utf-8"))["confirmation"]["date"] == "2027-01-02"
    assert not (tmp_path / "dst" / "winkel-tripel-ice.json").exists()


def test_use_template_dir_points_the_loader_and_restores(tmp_path):
    import lego_image_processor.templates as templates

    before = templates.TEMPLATE_DIR
    with testing.use_template_dir(tmp_path) as d:
        assert templates.TEMPLATE_DIR == tmp_path == d
    assert templates.TEMPLATE_DIR == before
