"""Map stickers on the site (feature 017, US2): the sticker routes and the map page's "Stickers for
a plaque" panel (FR-019, FR-026; contracts/web.md "Routes" and "Map page").

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil

import pytest
from markupsafe import escape

KIT = "kit-31203"
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


# --- routes ---------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["sticker-small", "sticker-large"])
def test_svg_inline(client, manifest, name):
    for m in manifest["maps"]:
        f = m["stickers"][KIT]["files"][name]
        r = client.get(f"/maps/{m['id']}/stickers/{KIT}/{name}.svg")
        assert r.status_code == 200, m["id"]
        assert r.headers["content-type"] == "image/svg+xml"
        assert "attachment" not in r.headers.get("content-disposition", "")
        assert "max-age=86400" in r.headers["cache-control"]
        assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
        assert r.headers["content-security-policy"] == CSP          # unchanged
        assert b"<script" not in r.content
        etag = r.headers["etag"]
        again = client.get(f"/maps/{m['id']}/stickers/{KIT}/{name}.svg", headers={"if-none-match": etag})
        assert again.status_code == 304


def test_downloads(client, manifest):
    n = 0
    for m in manifest["maps"]:
        for kind, f in m["stickers"][KIT]["files"].items():
            r = client.get(f"/maps/{m['id']}/stickers/{KIT}/download/{kind}")
            assert r.status_code == 200, (m["id"], kind)
            assert r.headers["content-type"] == f["media_type"]
            assert r.headers["content-disposition"] == f'attachment; filename="{f["filename"]}"'
            assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
            assert "max-age=86400" in r.headers["cache-control"] and r.headers["etag"]
            n += 1
    assert n == 4 * len(manifest["maps"])
    assert client.head(f"/maps/ocean-sst/stickers/{KIT}/download/stickers-letter").status_code == 200


@pytest.mark.parametrize("path", [
    f"/maps/nope/stickers/{KIT}/sticker-large.svg",
    "/maps/ocean-sst/stickers/winkel-tripel/sticker-large.svg",
    f"/maps/ocean-sst/stickers/{KIT}/sticker-medium.svg",
    f"/maps/ocean-sst/stickers/{KIT}/stickers-letter.pdf",
    f"/maps/ocean-sst/stickers/{KIT}/download/nope",
    f"/maps/ocean-sst/stickers/{KIT}/download/layout",
    f"/maps/ocean-sst/stickers/{KIT}/download/preview",
    f"/maps/ocean-sst/stickers/{KIT}/download/cells",
    f"/maps/nope/stickers/{KIT}/download/stickers-letter",
    "/maps/ocean-sst/stickers/winkel-tripel/download/stickers-letter",
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

def test_panel_same_for_a_b_c(client, manifest):
    """US2-2: the same panel in every combination."""
    for m in manifest["maps"]:
        panels = {c: _panel(client.get(f"/maps/{m['id']}/{c}").text) for c in ("A", "B", "C")}
        assert panels["A"] == panels["B"] == panels["C"], m["id"]


def test_panel_content(client, manifest):
    """US2-2: both stickers with alt texts and captions, what the large one says, the plaque parts
    with IDs, the two notes and four downloads with sizes."""
    from lego_image_processor.kit.plaque_parts import load_plaque_parts

    tiles = {size: p.tile.part_id for size, p in load_plaque_parts().plaques.items()}
    for m in manifest["maps"]:
        st = m["stickers"][KIT]
        html = client.get(f"/maps/{m['id']}/{m['default_combination']}").text
        panel = _panel(html)
        text = _text(panel)
        assert '<h2 id="stickers-heading">Stickers for a plaque</h2>' in panel
        figures = re.findall(r"<figure\b[^>]*>.*?</figure>", panel, re.S)
        assert len(figures) == 2
        for fig, size, mm in ((figures[0], "large", "125.8 × 61.8 mm"),
                              (figures[1], "small", "45.8 × 45.8 mm")):
            tile = tiles[size]
            src = f"/maps/{m['id']}/stickers/{KIT}/sticker-{size}.svg"
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
            href = f"/maps/{m['id']}/stickers/{KIT}/download/{kind}"
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


def test_template_page_shows_no_kit_set(client, manifest):
    """After the 016 merge (T053) and until T060 builds template sets: a template page looks up its
    own template's set (none yet), so it shows no Stickers panel rather than the kit's set; the kit
    pages keep theirs. T059/T060 replace this with "the Winkel page shows the Winkel set"."""
    sst = next(m for m in manifest["maps"] if m["id"] == "ocean-sst")
    assert list(sst["stickers"]) == [KIT] and "winkel-tripel" in sst["template_variants"]
    html = client.get("/maps/ocean-sst/winkel-tripel").text
    assert 'id="stickers"' not in html and f"/stickers/{KIT}/" not in html and DISCLAIMER in html
    assert 'id="stickers"' in client.get("/maps/ocean-sst/A").text
    assert client.get("/maps/ocean-sst/stickers/winkel-tripel/sticker-large.svg").status_code == 404
