"""Combinations D and E on the site (feature 010 US4, FR-013-FR-015).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import json
import re
import shutil

import pytest

from web98138 import COMBINATIONS
from web98138.catalog import Catalog, CatalogError

NOT_OFFICIAL = "not one of the three combinations in the building instructions"


def _arr(manifest, aid):
    return next(a for a in manifest["arrangements"] if a["id"] == aid)


def test_five_combinations():
    assert COMBINATIONS == ("A", "B", "C", "D", "E")


def test_manifest_rows(manifest):
    a, d, e = _arr(manifest, "A"), _arr(manifest, "D"), _arr(manifest, "E")
    assert a["description"] == "frames 1·2·3, Europe and Africa in the centre"
    assert a["in_instructions"] is True and a["groups"] == ["1", "2", "3"]
    assert d["name"] == "pacific" and d["column_shift"] == 64 and d["strips"] == "EFGHABCD"
    assert d["groups"] == ["2b", "3", "1", "2a"] and d["in_instructions"] is False
    assert d["frames"] == ["Europe & Africa (2b)", "Asia & Australia", "America", "Europe & Africa (2a)"]
    assert d["description"] == "frames 2b·3·1·2a, the Pacific (date line) in the centre"
    assert "134" in d["citation"] and "140" in d["citation"]
    assert NOT_OFFICIAL in d["note"]
    assert any("Unpeg frame 2 between strips D and E" in s for s in d["assembly"])
    assert any("Unpeg frame 2 between strips C and D" in s for s in e["assembly"])
    assert not any("Unpeg" in s for s in a["assembly"])
    assert manifest["joints_source"]["pages"] == [134, 135, 136, 137, 138, 139, 140]


def test_catalog_rejects_three(site_dir, tmp_path):
    dst = tmp_path / "site"
    shutil.copytree(site_dir, dst)
    p = dst / "manifest.json"
    m = json.loads(p.read_text())
    m["arrangements"] = m["arrangements"][:3]
    p.write_text(json.dumps(m))
    with pytest.raises(CatalogError, match="A, B, C, D, E"):
        Catalog.load(dst)


def test_enso_opens_in_d(client):
    r = client.get("/maps/ocean-el-nino", follow_redirects=False)
    assert r.headers["location"] == "/maps/ocean-el-nino/D"


def test_d_map_page(client):
    html = client.get("/maps/ocean-el-nino/D").text
    for c in COMBINATIONS:
        assert f'href="/maps/ocean-el-nino/{c}"' in html
    assert re.search(r'<a [^>]*href="/maps/ocean-el-nino/D"[^>]*aria-current="page"', html)
    assert 'src="/maps/ocean-el-nino/D/preview.png"' in html
    assert "Combination D" in html and "the Pacific (date line) in the centre" in html
    assert NOT_OFFICIAL in html and "pp. 134–140" in html
    assert "Unpeg frame 2 between strips D and E" in html
    assert "F|G, H|A and B|C" in html
    assert "/maps/ocean-el-nino/D/download/sheets-letter" in html


def test_a_page_gets_assembly_but_stays_official(client):
    html = client.get("/maps/official-31203/A").text
    assert "is one of the three combinations in the building instructions" in html
    assert NOT_OFFICIAL not in html and "Unpeg" not in html
    assert "B|C and F|G" in html


def test_about_five_ways(client):
    html = client.get("/about").text
    assert "Five ways to hang the frames" in html
    for text in ("frames 2b·3·1·2a, the Pacific (date line) in the centre",
                 "frames 2b·3·1·2a, Asia-Pacific (146° E) in the centre",
                 "pp. 134–140", "15 connector pegs", "pp. 7–8"):
        assert text in html, text
    assert html.count("not in the building instructions") >= 2
    for c in COMBINATIONS:
        assert f"/{c}/thumb.png" in html
