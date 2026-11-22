"""Pages and downloads (US1-US4; FR-001-FR-013)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET

import pytest
from markupsafe import escape

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
REPO = "https://github.com/kcaylor/98138_world"
PAGES = ["/", "/about", "/maps/official-31203/A", "/maps/ocean-sst/B", "/maps/ocean-sst/C"]


@pytest.mark.parametrize("path", PAGES)
def test_every_page_has_footer_and_basics(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert DISCLAIMER in html
    assert f'href="{REPO}"' in html
    assert '<html lang="en">' in html
    assert html.count("<h1") == 1
    assert "<main" in html and "<footer" in html and "<nav" in html
    assert "<script" not in html
    for img in re.findall(r"<img [^>]*>", html):
        assert re.search(r'alt="[^"]+"', img), img


def test_home_gallery(client, manifest):
    html = client.get("/").text
    for m in manifest["maps"]:
        c = m["default_combination"]
        assert f'href="/maps/{m["id"]}/{c}"' in html
        assert f'src="/maps/{m["id"]}/{c}/thumb.png"' in html
        assert escape(m["title"]) in html and escape(m["description"]) in html


def test_map_page_content(client, manifest):
    html = client.get("/maps/ocean-sst/A").text
    sst = manifest["maps"][1]
    assert 'src="/maps/ocean-sst/A/preview.png"' in html
    assert escape(sst["title"]) in html and escape(sst["description"]) in html
    cit = sst["citations"][0]
    assert escape(cit["license"]) in html
    assert escape(cit["citation"].split(",")[0]) in html
    assert "https://doi.org/" + cit["doi"] in html
    s = sst["variants"]["A"]["summary"]
    assert f"{s['pieces']:,}" in html and f"{s['one_kit_covers']:,}" in html
    assert "Rebrickable" in html and escape(manifest["acknowledgement"]) in html
    lot = sst["variants"]["A"]["lots"][0]
    assert lot["bricklink"]["item_no"] in html and lot["rebrickable"]["part_num"] in html
    assert escape(lot["lego"]["name"]) in html
    assert "data" in html and "background" in html


def test_map_page_without_dataset_cites_design(client, manifest):
    html = client.get("/maps/official-31203/A").text
    assert escape(manifest["maps"][0]["citations"][0]["citation"][:40]) in html


def test_warnings_listed(client, manifest):
    for m in manifest["maps"]:
        w = m["variants"]["A"]["warnings"]
        if w:
            html = client.get(f"/maps/{m['id']}/A").text
            assert escape(w[0]) in html


# --- US2: combinations ---------------------------------------------------------------------

def test_combination_switcher(client):
    html = client.get("/maps/ocean-sst/B").text
    assert 'src="/maps/ocean-sst/B/preview.png"' in html
    assert "Combination B" in html and "frames 3·1·2, America in the centre" in html
    assert re.search(r'<a [^>]*href="/maps/ocean-sst/B"[^>]*aria-current="page"', html)
    assert 'href="/maps/ocean-sst/A"' in html and 'href="/maps/ocean-sst/C"' in html
    assert "/maps/ocean-sst/B/download/sheets-letter" in html
    assert "/maps/ocean-sst/A/download/" not in html


def test_map_root_redirects_to_a(client):
    r = client.get("/maps/ocean-sst", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/maps/ocean-sst/A"


def test_map_root_redirects_to_recipe_arrangement(client):
    # feature 009: a recipe's `arrangement` key is the map's default combination on the site
    r = client.get("/maps/ocean-el-nino", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/maps/ocean-el-nino/B"


def test_home_links_default_combination(client):
    html = client.get("/").text
    assert 'href="/maps/ocean-el-nino/B"' in html and 'href="/maps/ocean-sst/A"' in html


def test_lowercase_combination_redirects(client):
    r = client.get("/maps/ocean-sst/b", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/maps/ocean-sst/B"


@pytest.mark.parametrize("path", ["/maps/ocean-sst/D", "/maps/nope/A", "/maps/nope",
                                  "/maps/ocean-sst/AB", "/maps/land-elevation/A"])
def test_unknown_is_404(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert DISCLAIMER in r.text and "<h1" in r.text


# --- US3: downloads ------------------------------------------------------------------------

def _downloads(manifest):
    for m in manifest["maps"]:
        for c, v in m["variants"].items():
            for kind, f in v["files"].items():
                if kind not in ("preview", "thumb"):
                    yield m["id"], c, kind, f


def test_every_download(client, manifest):
    n = 0
    for map_id, c, kind, f in _downloads(manifest):
        r = client.get(f"/maps/{map_id}/{c}/download/{kind}")
        assert r.status_code == 200, (map_id, c, kind)
        assert r.headers["content-type"] == f["media_type"]
        assert r.headers["content-disposition"] == f'attachment; filename="{f["filename"]}"'
        assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
        n += 1
    assert n >= 6 * 7


def test_download_contents_parse(client):
    base = "/maps/ocean-sst/B/download/"
    layout = client.get(base + "layout").json()
    assert layout["metadata"]["schema_version"] == "2.0"
    assert len(layout["positions"]) == 10240
    assert layout["metadata"]["arrangement"]["id"] == "B"
    root = ET.fromstring(client.get(base + "bricklink").content)
    assert root.tag == "INVENTORY" and root.findall("ITEM")
    rows = list(csv.reader(io.StringIO(client.get(base + "rebrickable").text)))
    assert rows[0] == ["Part", "Color", "Quantity"] and len(rows) > 1
    from pypdf import PdfReader
    pdf = PdfReader(io.BytesIO(client.get(base + "sheets-a4").content))
    assert len(pdf.pages) >= 42
    parts = client.get(base + "parts-1kit").json()
    assert parts["owned"]["kits"] == 1


def test_images_inline(client):
    r = client.get("/maps/official-31203/C/preview.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "attachment" not in r.headers.get("content-disposition", "")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/maps/official-31203/C/thumb.png").status_code == 200


@pytest.mark.parametrize("kind", ["nope", "preview", "thumb", "bricklink-1kit", "manifest", "layout.json"])
def test_unknown_download_kind_404(client, kind):
    # official-31203: one kit covers everything, so there is no bricklink-1kit file
    assert client.get(f"/maps/official-31203/A/download/{kind}").status_code == 404


def test_nothing_to_buy_message(client):
    html = client.get("/maps/official-31203/A").text
    assert "One kit covers every piece; nothing to buy" in html
    assert "/download/bricklink-1kit" not in html


def test_downloads_listed_with_size(client, manifest):
    html = client.get("/maps/ocean-sst/A").text
    for kind, f in manifest["maps"][1]["variants"]["A"]["files"].items():
        if kind in ("preview", "thumb"):
            continue
        assert f'href="/maps/ocean-sst/A/download/{kind}"' in html
        assert escape(f["description"]) in html


# --- US4: about ----------------------------------------------------------------------------

def test_about(client):
    html = client.get("/about").text
    for text in ("frames 1·2·3, Europe and Africa in the centre",
                 "frames 3·1·2, America in the centre",
                 "frames 2·3·1, Asia and Australia in the centre",
                 "pp. 7–8", "cookies", "analytics", REPO):
        assert text in html, text
