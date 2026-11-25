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
    # FR-009 as amended by feature 015 (FR-020): works without JavaScript; the only script is
    # the site's own /static/palette.js, on map pages, with no inline script.
    for tag in re.findall(r"<script\b[^>]*>", html):
        assert re.fullmatch(r'<script src="/static/palette\.js\?v=[^"]+" defer>', tag), tag
    assert len(re.findall(r"<script\b[^>]*>\s*</script>", html)) == html.count("<script")
    if not path.startswith("/maps/"):
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


def test_map_page_leftovers(client, manifest):
    """Feature 014: every kit color's leftover and the total are on the map page."""
    sst = manifest["maps"][1]
    v = sst["variants"]["A"]
    html = client.get("/maps/ocean-sst/A").text
    assert "Left over in the box" in html
    assert f"{v['summary']['left_over_with_kit']:,}" in html
    for r in v["leftovers"]:
        assert escape(r["lego"]["name"]) in html
    assert html.count('class="leftover-row"') == 10


def test_gray_background_and_stud_mat(client):
    css = client.get("/static/style.css").text
    assert "--bg: #e9e9e9;" in css and "--stud-mat: #e9e9e9;" in css and "--stud-round-mat: #000000;" in css
    assert ".stud-img" in css and "background: var(--stud-mat)" in css


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
                if kind not in ("preview", "thumb", "cells"):  # cells: feature 015, not a download
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
    # feature 017: each map's four sticker files
    for m in manifest["maps"]:
        for kind, f in m["stickers"]["kit-31203"]["files"].items():
            r = client.get(f"/maps/{m['id']}/stickers/kit-31203/download/{kind}")
            assert r.status_code == 200, (m["id"], kind)
            assert r.headers["content-disposition"] == f'attachment; filename="{f["filename"]}"'
            assert hashlib.sha256(r.content).hexdigest() == f["sha256"]


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
        if kind in ("preview", "thumb", "cells"):  # cells: feature 015, not a download
            continue
        assert f'href="/maps/ocean-sst/A/download/{kind}"' in html
        assert escape(f["description"]) in html
    for kind, f in manifest["maps"][1]["stickers"]["kit-31203"]["files"].items():  # feature 017
        assert f'href="/maps/ocean-sst/stickers/kit-31203/download/{kind}"' in html
        assert escape(f["description"]) in html


# --- US4: about ----------------------------------------------------------------------------

def test_about(client):
    html = client.get("/about").text
    for text in ("frames 1·2·3, Europe and Africa in the centre",
                 "frames 3·1·2, America in the centre",
                 "frames 2·3·1, Asia and Australia in the centre",
                 "pp. 7–8", "cookies", "analytics", REPO,
                 "Stickers for a plaque"):   # feature 017
        assert text in html, text


# --- feature 011: estimated cost -----------------------------------------------------------

ESTIMATE_NOTE = "Estimate only; excludes shipping, fees and taxes; prices vary by seller and over time."
ATTRIBUTION = ("Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of "
               "LEGO BrickLink, Inc. Not endorsed by BrickLink.")


def _usd(n):
    return f"${n:,}"


def _client_for(site_dir, tmp_path, fn):
    import shutil

    from fastapi.testclient import TestClient

    from web98138.app import create_app

    dst = tmp_path / "site"
    shutil.copytree(site_dir, dst)
    p = dst / "manifest.json"
    m = json.loads(p.read_text())
    fn(m)
    p.write_text(json.dumps(m))
    return TestClient(create_app(dst), base_url="https://98138.world")


def _text(html):
    """The page's text with tags and repeated whitespace removed."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_price_panel(client, manifest):
    """US3-2, SC-006: both estimates, date, source link, wording, attribution, disclaimer."""
    for m in manifest["maps"]:
        for c in ("A", "B"):
            html = client.get(f"/maps/{m['id']}/{c}").text
            text = _text(html)
            p = manifest["prices"]
            assert '<h2 id="cost-heading">Estimated cost</h2>' in html
            full = m["variants"][c]["estimates"]["full"]
            w = full["whole_dollars"]
            assert f"Every piece about {_usd(w['average'])} (range {_usd(w['low'])}–{_usd(w['high'])})" in text
            one = m["variants"][c]["estimates"]["one_kit"]
            if one["nothing_to_buy"]:
                assert "On top of one 31203 kit One kit covers every piece" in text
            else:
                w1 = one["whole_dollars"]
                assert f"On top of one 31203 kit about {_usd(w1['average'])}" in text
            assert f"Prices from {p['snapshot']['retrieved_on']}" in text
            assert str(escape(p["basis"])) in html
            assert '<a href="https://www.bricklink.com">BrickLink price guide</a>' in html
            assert ESTIMATE_NOTE in html and ATTRIBUTION in html
            assert DISCLAIMER in html
            assert "may be out of date" not in html and "partial" not in text
    # the panel comes after the Parts panel and before the Lots table
    html = client.get("/maps/ocean-sst/A").text
    assert html.index('id="parts-heading"') < html.index('id="cost-heading"') < html.index('id="lots-heading"')


def test_thousands_separator(client, manifest):
    w = manifest["maps"][0]["variants"]["A"]["estimates"]["full"]["whole_dollars"]
    html = client.get("/maps/official-31203/A").text
    if w["high"] >= 1000:
        assert f"{w['high']:,}" in html and "," in f"{w['high']:,}"


def test_one_kit_covers_every_piece(client, manifest):
    """US3-3: the official design needs nothing beyond one kit."""
    assert manifest["maps"][0]["variants"]["A"]["estimates"]["one_kit"]["nothing_to_buy"] is True
    text = _text(client.get("/maps/official-31203/A").text)
    assert "On top of one 31203 kit One kit covers every piece" in text


def _set(m, map_i, c, kind, **kw):
    e = m["maps"][map_i]["variants"][c]["estimates"][kind]
    for k, v in kw.items():
        e[k] = v


def test_incomplete_note(site_dir, tmp_path):
    """US3-4."""
    def edit(m):
        _set(m, 1, "A", "full", complete=False, unpriced={"lots": 2, "pieces": 1312})
        _set(m, 1, "A", "one_kit", complete=False, unpriced={"lots": 1, "pieces": 1})
    with _client_for(site_dir, tmp_path, edit) as c:
        text = _text(c.get("/maps/ocean-sst/A").text)
        assert "Incomplete: 1,312 pieces in 2 colors could not be priced." in text
        assert "Incomplete: 1 piece in 1 color could not be priced." in text
        assert "Incomplete" not in _text(c.get("/maps/ocean-sst/B").text)


def test_stale_and_partial_notes(site_dir, tmp_path):
    """US3-5."""
    def edit(m):
        m["prices"]["staleness"].update(stale=True, age_days=200)
        m["prices"]["snapshot"]["complete"] = False
    with _client_for(site_dir, tmp_path, edit) as c:
        text = _text(c.get("/maps/ocean-sst/A").text)
        assert "These prices are from 2026-12-01 and may be out of date." in text
        assert "The price snapshot is partial." in text


def test_single_value_range(site_dir, tmp_path):
    def edit(m):
        _set(m, 1, "A", "full", whole_dollars={"average": 7, "low": 7, "high": 7})
    with _client_for(site_dir, tmp_path, edit) as c:
        text = _text(c.get("/maps/ocean-sst/A").text)
        assert "Every piece about $7 (range $7)" in text and "$7–$7" not in text


def test_no_price_panel_without_prices(site_dir, tmp_path):
    def strip(m):
        m.pop("prices")
        for mp in m["maps"]:
            for v in mp["variants"].values():
                v.pop("estimates")
    with _client_for(site_dir, tmp_path, strip) as c:
        html = c.get("/maps/ocean-sst/A").text
        assert "Estimated cost" not in html and "bricklink.com\">" not in html
        assert ATTRIBUTION not in html and DISCLAIMER in html


def test_home_page_has_no_prices(client):
    html = client.get("/").text
    assert "Estimated cost" not in html and "$" not in html
