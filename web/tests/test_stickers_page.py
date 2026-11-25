"""Map stickers on the site (feature 017, US2): the sticker routes and the map page's "Stickers for
a plaque" panel (FR-019, FR-020, FR-026; contracts/web.md "Routes" and "Map page"). Kit pages
show the kit set; a template page (feature 016: ocean-sst's Winkel tripel variant in the session
site) shows its own template's set (T059).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil

import pytest
from markupsafe import escape

from web98138 import COMBINATIONS

KIT = "kit-31203"
TID = "winkel-tripel"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
CSP = ("default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
KINDS = ("stickers-letter", "stickers-a4", "sticker-small", "sticker-large")
_PANEL = re.compile(r'<section id="stickers"[^>]*>.*?</section>', re.S)


def _size(n):
    """The page's size text (app._size)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{n / 1_000:.0f} kB"
    return f"{n} bytes"


def _panel(html):
    found = _PANEL.findall(html)
    assert len(found) == 1, "one sticker panel"
    return found[0]


def _block(manifest, map_id):
    return next(m for m in manifest["maps"] if m["id"] == map_id)["stickers"][KIT]


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _sets(manifest):
    """(map id, template id, block) of every sticker set, kit and template."""
    return [(m["id"], t, st) for m in manifest["maps"] for t, st in m["stickers"].items()]


# --- routes ---------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["sticker-small", "sticker-large"])
def test_svg_inline(client, manifest, name):
    sets = _sets(manifest)
    assert TID in {t for _, t, _ in sets}
    for map_id, tid, st in sets:
        f = st["files"][name]
        r = client.get(f"/maps/{map_id}/stickers/{tid}/{name}.svg")
        assert r.status_code == 200, (map_id, tid)
        assert r.headers["content-type"] == "image/svg+xml"
        assert "attachment" not in r.headers.get("content-disposition", "")
        assert "max-age=86400" in r.headers["cache-control"]
        assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
        assert r.headers["content-security-policy"] == CSP          # unchanged
        assert b"<script" not in r.content
        etag = r.headers["etag"]
        again = client.get(f"/maps/{map_id}/stickers/{tid}/{name}.svg", headers={"if-none-match": etag})
        assert again.status_code == 304


def test_downloads(client, manifest):
    n = 0
    sets = _sets(manifest)
    for map_id, tid, st in sets:
        for kind, f in st["files"].items():
            r = client.get(f"/maps/{map_id}/stickers/{tid}/download/{kind}")
            assert r.status_code == 200, (map_id, tid, kind)
            assert r.headers["content-type"] == f["media_type"]
            assert r.headers["content-disposition"] == f'attachment; filename="{f["filename"]}"'
            assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
            assert "max-age=86400" in r.headers["cache-control"] and r.headers["etag"]
            n += 1
    assert n == 4 * len(sets) > 4 * len(manifest["maps"])
    assert client.head(f"/maps/ocean-sst/stickers/{KIT}/download/stickers-letter").status_code == 200


@pytest.mark.parametrize("path", [
    f"/maps/nope/stickers/{KIT}/sticker-large.svg",
    "/maps/ocean-sst/stickers/mercator/sticker-large.svg",
    f"/maps/official-31203/stickers/{TID}/sticker-large.svg",     # no Winkel variant
    f"/maps/ocean-el-nino/stickers/{TID}/download/stickers-letter",
    f"/maps/ocean-sst/stickers/{TID}/download/layout",
    f"/maps/ocean-sst/{TID}/download/stickers-letter",
    f"/maps/ocean-sst/stickers/{KIT}/sticker-medium.svg",
    f"/maps/ocean-sst/stickers/{KIT}/stickers-letter.pdf",
    f"/maps/ocean-sst/stickers/{KIT}/download/nope",
    f"/maps/ocean-sst/stickers/{KIT}/download/layout",
    f"/maps/ocean-sst/stickers/{KIT}/download/preview",
    f"/maps/ocean-sst/stickers/{KIT}/download/cells",
    f"/maps/nope/stickers/{KIT}/download/stickers-letter",
    "/maps/ocean-sst/stickers/mercator/download/stickers-letter",
    f"/maps/ocean-sst/stickers/{KIT}/download/..%2F..%2F..%2Fmanifest.json",
    f"/maps/ocean-sst/stickers/{KIT}",
    "/maps/ocean-sst/stickers",
    "/maps/ocean-sst/A/download/stickers-letter",
    "/maps/ocean-sst/A/download/sticker-large",
])
def test_unknown_is_404(client, path):
    r = client.get(path)
    assert r.status_code == 404
    assert DISCLAIMER in r.text


# --- the panel ------------------------------------------------------------------------------

def test_panel_same_in_every_combination(client, manifest):
    """US2-2: the same panel in every combination, A-E (D and E: feature 010)."""
    assert COMBINATIONS == ("A", "B", "C", "D", "E")
    for m in manifest["maps"]:
        panels = {c: _panel(client.get(f"/maps/{m['id']}/{c}").text) for c in COMBINATIONS}
        assert all(panels[c] == panels["A"] for c in COMBINATIONS), m["id"]
        assert panels["A"] and f"/stickers/{KIT}/" in panels["A"], m["id"]


def _pages(manifest):
    """(page path, map row, template id, block): each map's default kit page with the kit set,
    and each template page with its template's set."""
    out = []
    for m in manifest["maps"]:
        out.append((f"/maps/{m['id']}/{m['default_combination']}", m, KIT, m["stickers"][KIT]))
        for tid in m.get("template_variants", {}):
            out.append((f"/maps/{m['id']}/{tid}", m, tid, m["stickers"][tid]))
    return out


def test_panel_content(client, manifest):
    """US2-2, US2-4: both stickers with alt texts and captions, what the large one says, the
    plaque parts with IDs, the two notes and four downloads with sizes, on kit pages (the kit set)
    and template pages (the template's set)."""
    from lego_image_processor.kit.plaque_parts import load_plaque_parts

    tiles = {size: p.tile.part_id for size, p in load_plaque_parts().plaques.items()}
    pages = _pages(manifest)
    assert TID in {tid for _, _, tid, _ in pages}
    for path, m, tid, st in pages:
        html = client.get(path).text
        panel = _panel(html)
        text = _text(panel)
        assert '<h2 id="stickers-heading">Stickers for a plaque</h2>' in panel
        figures = re.findall(r"<figure\b[^>]*>.*?</figure>", panel, re.S)
        assert len(figures) == 2
        for fig, size, mm in ((figures[0], "large", "125.8 × 61.8 mm"),
                              (figures[1], "small", "45.8 × 45.8 mm")):
            tile = tiles[size]
            src = f"/maps/{m['id']}/stickers/{tid}/sticker-{size}.svg"
            assert f'src="{src}"' in fig and f'alt="{escape(st["alt"][size])}"' in fig
            cap = _text(re.search(r"<figcaption>.*?</figcaption>", fig, re.S).group(0))
            assert mm in cap and tile in cap and "Black" in cap
            assert "The sticker is printed, not a LEGO part." in cap
        details = re.search(r"<details\b[^>]*>.*?</details>", panel, re.S).group(0)
        assert "<summary>What the large sticker says</summary>" in details
        for value in (st["title"], st["line"], *st["credit"], DISCLAIMER, "98138.world"):
            assert str(escape(value)) in details, value
        for row in st["legend"]:
            assert str(escape(row["label"])) in details and str(escape(row["color"])) in details
        assert "Parts for a standalone plaque" in panel
        for plaque in st["plaques"]:
            for part in plaque["parts"]:
                for value in (part["name"], part["part_id"], part["element_id"],
                              *part["lego_design_ids"], part["bricklink_item"],
                              part["rebrickable_part"]):
                    assert str(escape(value)) in panel, value
                c = part["color"]
                assert f"{c['lego']['name']} ({c['lego']['id']}" in text
                assert f"{part['bricklink_item']} / {c['bricklink']['name']} ({c['bricklink']['id']})" in text
                assert f"{part['rebrickable_part']} / {c['rebrickable']['name']} ({c['rebrickable']['id']})" in text
        assert "Printed colors only approximate the LEGO colors." in panel
        assert "The sticker is printed, not a LEGO part." in panel
        for kind in KINDS:
            f = st["files"][kind]
            href = f"/maps/{m['id']}/stickers/{tid}/download/{kind}"
            assert f'href="{href}" download="{f["filename"]}"' in panel
            assert str(escape(f["description"])) in panel
            assert f"{f['path'].rsplit('.', 1)[1].upper()} · {_size(f['bytes'])}" in text
        assert DISCLAIMER in html[html.index("<footer"):]


def test_panel_without_javascript(client, manifest):
    """US2-3: with scripts removed the panel, its images and downloads are all plain HTML."""
    html = client.get("/maps/ocean-sst/A").text
    no_js = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
    panel = _panel(no_js)
    assert "<noscript" not in panel and " hidden" not in panel.split(">", 1)[0]
    for src in re.findall(r'<img [^>]*src="([^"]+)"', panel):
        assert client.get(src).status_code == 200
    links = re.findall(r'<a href="([^"]+)" download=', panel)
    assert len(links) == 4
    for href in links:
        assert client.get(href).status_code == 200


def test_stickers_outside_the_palette_chooser(client):
    """palette.js recolors only the preview: the stickers are not in its section or classes."""
    from pathlib import Path

    html = client.get("/maps/ocean-sst/A").text
    palette = re.search(r'<section id="palette".*?</section>', html, re.S).group(0)
    assert "sticker" not in palette
    panel = _panel(html)
    assert html.index('id="palette"') < html.index('id="stickers"')
    for img in re.findall(r"<img [^>]*>", panel):
        assert "stud-img" not in img and "preview-img" not in img
    js = (Path(__file__).resolve().parents[1] / "src" / "web98138" / "static" / "palette.js").read_text()
    assert "sticker" not in js


def test_panel_comes_after_the_lots(client):
    html = client.get("/maps/ocean-sst/A").text
    assert html.index('id="lots-heading"') < html.index('id="stickers-heading"') < html.index('id="layers-heading"')


def test_about_has_a_sticker_paragraph(client):
    html = client.get("/about").text
    assert "<h2>Stickers for a plaque</h2>" in html
    text = _text(html)
    assert "Black tile" in text and "printed, not a LEGO part" in text
    assert "Printed colors only approximate the LEGO colors." in text


def test_sticker_css(client):
    css = client.get("/static/style.css").text
    assert ".sticker-figs" in css and ".sticker-fig img" in css


def test_older_manifest_has_no_panel(site_dir, tmp_path):
    """A manifest without sticker blocks still serves, without the panel or its routes."""
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    dst = tmp_path / "site"
    shutil.copytree(site_dir, dst)
    p = dst / "manifest.json"
    m = json.loads(p.read_text())
    for mp in m["maps"]:
        mp.pop("stickers")
    p.write_text(json.dumps(m))
    with TestClient(create_app(dst), base_url="https://98138.world") as c:
        r = c.get("/maps/ocean-sst/A")
        assert r.status_code == 200 and 'id="stickers"' not in r.text and DISCLAIMER in r.text
        assert c.get(f"/maps/ocean-sst/stickers/{KIT}/sticker-large.svg").status_code == 404
        assert c.get(f"/maps/ocean-sst/stickers/{KIT}/download/stickers-a4").status_code == 404


def test_template_page_shows_the_template_set(client, manifest):
    """US2-4 (FR-020): the Winkel page shows the Winkel set, whose line names the projection; the
    kit pages show the kit set and never the Winkel one."""
    sst = next(m for m in manifest["maps"] if m["id"] == "ocean-sst")
    assert list(sst["stickers"]) == [KIT, TID] and TID in sst["template_variants"]
    wk = sst["stickers"][TID]
    assert wk["line"].endswith(" Winkel tripel projection.")
    panel = _panel(client.get(f"/maps/ocean-sst/{TID}").text)
    assert f"/stickers/{TID}/" in panel and f"/stickers/{KIT}/" not in panel
    assert str(escape(wk["line"])) in panel and str(escape(wk["alt"]["large"])) in panel
    for kind, f in wk["files"].items():
        assert f'download="98138-world_ocean-sst_{TID}_{kind}.' in panel
    note = _text(re.search(r'<p class="note">.*?</p>', panel, re.S).group(0))
    assert "Winkel tripel" in note and "every combination" not in note
    for c in COMBINATIONS:
        kit = _panel(client.get(f"/maps/ocean-sst/{c}").text)
        assert f"/stickers/{TID}/" not in kit and f"/stickers/{KIT}/" in kit
        assert "The stickers are the same for every combination." in kit
        assert str(escape(wk["line"])) not in kit


def test_template_page_without_its_set_shows_no_panel(site_dir, tmp_path):
    """A manifest whose template variant has no sticker set serves the template page without a
    panel (never the kit's set), and the kit pages keep theirs."""
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    dst = tmp_path / "site"
    shutil.copytree(site_dir, dst)
    p = dst / "manifest.json"
    m = json.loads(p.read_text())
    sst = next(r for r in m["maps"] if r["id"] == "ocean-sst")
    del sst["stickers"][TID]
    p.write_text(json.dumps(m))
    with TestClient(create_app(dst), base_url="https://98138.world") as c:
        html = c.get(f"/maps/ocean-sst/{TID}").text
        assert 'id="stickers"' not in html and f"/stickers/{KIT}/" not in html and DISCLAIMER in html
        assert 'id="stickers"' in c.get("/maps/ocean-sst/A").text
        assert c.get(f"/maps/ocean-sst/stickers/{TID}/sticker-large.svg").status_code == 404
