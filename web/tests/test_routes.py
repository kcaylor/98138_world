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
PAGES = ["/", "/about", "/maps/official-31203/A", "/maps/ocean-sst/B", "/maps/ocean-sst/C",
         "/maps/ocean-sst/winkel-tripel"]   # feature 016


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


# --- US4: about ----------------------------------------------------------------------------

def test_about(client):
    html = client.get("/about").text
    for text in ("frames 1·2·3, Europe and Africa in the centre",
                 "frames 3·1·2, America in the centre",
                 "frames 2·3·1, Asia and Australia in the centre",
                 "pp. 7–8", "cookies", "analytics", REPO):
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
            for v in list(mp["variants"].values()) + list(mp.get("template_variants", {}).values()):
                v.pop("estimates")
    with _client_for(site_dir, tmp_path, strip) as c:
        html = c.get("/maps/ocean-sst/A").text
        assert "Estimated cost" not in html and "bricklink.com\">" not in html
        assert ATTRIBUTION not in html and DISCLAIMER in html


def test_home_page_has_no_prices(client):
    html = client.get("/").text
    assert "Estimated cost" not in html and "$" not in html


# --- feature 016: Winkel versions (US3-2, US3-3; FR-020, FR-022; contracts/web.md) ----------

TID = "winkel-tripel"
WINKEL = f"/maps/ocean-sst/{TID}"
CAPTION = "Round studs for land and ocean, square tiles in the margin"
REHANG = "The frames of a curved map cannot be re-hung"


def _tv(manifest, map_id="ocean-sst"):
    return next(m for m in manifest["maps"] if m["id"] == map_id)["template_variants"][TID]


def test_winkel_page(client, manifest):
    r = client.get(WINKEL)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html, text = r.text, _text(r.text)
    v = _tv(manifest)
    t = manifest["templates"][0]
    # the nav: A, B, C and the Winkel version, which is the current page
    for c in ("A", "B", "C"):
        assert re.search(rf'<a href="/maps/ocean-sst/{c}"><span class="combo-id">{c}</span>', html)
    assert re.search(rf'<a href="{WINKEL}" aria-current="page"><span class="combo-id">Winkel tripel</span>', html)
    assert "aria-current=\"page\"><span class=\"combo-id\">A" not in html
    # preview, caption, the cannot-be-re-hung note and the parts note
    assert f'src="{WINKEL}/preview.png"' in html
    assert re.search(r'<img id="preview-img"[^>]*alt="[^"]*Winkel tripel[^"]*"', html)
    assert CAPTION in html and "8 × 5 modules, 128 × 80 studs" in html
    assert f"{t['counts']['margin']:,} margin" in text
    assert REHANG in html
    assert "Square tiles (part 3070b) fill the margin; one 31203 kit supplies none" in html
    assert "Every arrangement uses the same pieces" not in html
    assert "<title>Ocean temperature · Winkel tripel · 98138.world</title>" in html
    # parts, lots (with the square tile) and the incomplete estimate
    s = v["summary"]
    assert f"{s['pieces']:,}" in html and f"{s['to_buy_with_kit']:,}" in html
    assert "tile 1x1 square <span class=\"id\">3070b</span>" in html
    assert re.search(r"Margin: 1,996 square tiles \(part 3070b\) in Black", text.replace(f"{t['counts']['margin']:,}", "1,996"))
    assert f"Incomplete: {v['estimates']['full']['unpriced']['pieces']:,} pieces in 1 color could not be priced." in text
    assert "Downloads for the Winkel tripel version" in text
    # the palette chooser reads this variant's cells
    assert f'data-cells="{WINKEL}/cells.json"' in html
    assert DISCLAIMER in html


def test_winkel_page_cites_the_template_dataset(client, manifest):
    html = client.get(WINKEL).text
    kit = client.get("/maps/ocean-sst/A").text
    etopo = next(c for c in _tv(manifest)["citations"] if c["id"] == "etopo2022-surface-10m")
    assert escape(etopo["title"]) in html and escape(etopo["title"]) not in kit
    assert escape(etopo["license"]) in html and "https://doi.org/" + etopo["doi"] in html
    t = manifest["templates"][0]
    assert t["source"]["sha256"][:16] in html
    assert f"confirmed by the project owner on {t['source']['confirmation']['date']}" in html


def test_winkel_files(client, manifest):
    v = _tv(manifest)
    for kind in ("preview", "thumb", "cells"):
        r = client.get(f"{WINKEL}/{v['files'][kind]['path'].rsplit('/', 1)[1]}")
        assert r.status_code == 200, kind
        assert "attachment" not in r.headers.get("content-disposition", "")
        assert hashlib.sha256(r.content).hexdigest() == v["files"][kind]["sha256"]
    n = 0
    html = client.get(WINKEL).text
    for kind, f in v["files"].items():
        if kind in ("preview", "thumb", "cells"):
            continue
        assert f'href="{WINKEL}/download/{kind}"' in html          # works without JavaScript
        r = client.get(f"{WINKEL}/download/{kind}")
        assert r.status_code == 200, kind
        assert r.headers["content-disposition"] == f'attachment; filename="{f["filename"]}"'
        assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
        n += 1
    assert n == 9   # every download kind: one kit has no square tiles, so there is a top-up
    layout = client.get(f"{WINKEL}/download/layout").json()
    assert layout["metadata"]["template"]["id"] == TID
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(client.get(f"{WINKEL}/download/sheets-letter").content)).pages) >= 42


@pytest.mark.parametrize("path", [
    "/maps/ocean-sst/mercator", "/maps/official-31203/winkel-tripel", "/maps/ocean-el-nino/winkel-tripel",
    "/maps/official-31203/winkel-tripel/preview.png", "/maps/ocean-el-nino/winkel-tripel/cells.json",
    f"{WINKEL}/download/nope", f"{WINKEL}/download/cells", f"{WINKEL}/nope.png", "/maps/ocean-sst/WINKEL-TRIPEL",
    "/maps/nope/winkel-tripel", f"{WINKEL}/download/preview"])
def test_winkel_unknown_is_404(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 404, path
    assert DISCLAIMER in r.text


def test_map_root_still_redirects_to_a_kit_combination(client):
    r = client.get("/maps/ocean-sst", follow_redirects=False)
    assert r.headers["location"] == "/maps/ocean-sst/A"


def test_winkel_page_without_javascript(client):
    """US3-3: the built preview and plain links; the only script is the site's own chooser."""
    html = client.get(WINKEL).text
    for tag in re.findall(r"<script\b[^>]*>", html):
        assert re.fullmatch(r'<script src="/static/palette\.js\?v=[^"]+" defer>', tag), tag
    assert "<noscript>" in html
    assert re.search(r'<img id="preview-img" src="/maps/ocean-sst/winkel-tripel/preview\.png"', html)
    assert html.count("/download/") == 9


def test_winkel_page_headers_and_footer(client):
    r = client.get(WINKEL)
    kit = client.get("/maps/ocean-sst/A")
    assert r.status_code == 200
    assert r.headers["content-security-policy"] == kit.headers["content-security-policy"]
    assert "script-src 'self'; connect-src 'self'" in r.headers["content-security-policy"]
    assert "set-cookie" not in r.headers
    footer = r.text[r.text.index("<footer"):]
    assert DISCLAIMER in footer


def test_about_templates_paragraph(client, manifest):
    html = client.get("/about").text
    t = manifest["templates"][0]
    assert "Winkel tripel" in html and "square tiles" in html and "part 3070b" in html
    assert f"{t['counts']['margin']:,}" in html
    assert "cannot be re-hung" in html
    assert 'href="/maps/ocean-sst/winkel-tripel"' in html


def test_about_without_templates_has_no_paragraph(site_dir, tmp_path):
    def strip(m):
        m.pop("templates")
        for mp in m["maps"]:
            mp.pop("template_variants", None)
    with _client_for(site_dir, tmp_path, strip) as c:
        about = c.get("/about").text
        assert "Winkel" not in about and "3070b" not in about
        page = c.get("/maps/ocean-sst/A").text
        assert "combo-template" not in page and "Winkel" not in page
        assert c.get(WINKEL).status_code == 404


@pytest.fixture(scope="module")
def golden_sites(site_dir, living_site, rainfall_site):
    return {"small": site_dir, "living-planet": living_site, "rainfall": rainfall_site}


def test_kit_pages_change_only_by_the_winkel_link(golden_sites):
    """Kit map pages of the eligible maps equal the T009 golden after removing the "Winkel tripel"
    nav item (asset tokens normalised); kit pages of official-31203 and ocean-el-nino equal it
    exactly (kit_golden.py; the golden file was written from an unmodified main)."""
    from fastapi.testclient import TestClient

    import kit_golden
    from web98138.app import create_app

    doc = json.loads(kit_golden.GOLDEN_PATH.read_text(encoding="utf-8"))
    golden = {(s["site"], v["map"], v["combination"]): v["digests"] for s in doc["sites"] for v in s["variants"]}
    seen = {}
    for name, d in golden_sites.items():
        with TestClient(create_app(d), base_url="https://98138.world") as c:
            for m in json.loads((d / "manifest.json").read_text(encoding="utf-8"))["maps"]:
                eligible = TID in m.get("template_variants", {})
                seen[m["id"]] = eligible
                for comb in ("A", "B", "C"):
                    path = f"/maps/{m['id']}/{comb}"
                    html = c.get(path).text
                    want = golden[(name, m["id"], comb)][f"page {path}"]
                    links = kit_golden.template_nav_item(m["id"], TID).findall(html)
                    assert len(links) == (1 if eligible else 0), path
                    if eligible:
                        assert kit_golden.page_digest(html) != want      # the link is there ...
                        stripped = kit_golden.strip_template_nav(html, m["id"], [TID])
                        assert kit_golden.page_digest(stripped) == want, path   # ... and nothing else
                    else:
                        assert kit_golden.page_digest(html) == want, path
    assert seen == {"official-31203": False, "ocean-sst": True, "ocean-el-nino": False,
                    "living-planet": True, "rainfall": True}
