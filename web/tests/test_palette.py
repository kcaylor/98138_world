"""Palette chooser (feature 015): cells.json in the build, its route, the chooser markup, the
first-party script and its pure functions (FR-006-FR-021; SC-001, SC-003, SC-005)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
NOTE = "Preview only: parts lists, prices, build sheets and downloads use the map's default colors."
STATIC = Path(__file__).resolve().parents[1] / "src" / "web98138" / "static"
SCRIPT = STATIC / "palette.js"


def _variants(manifest):
    for m in manifest["maps"]:
        for c, v in m["variants"].items():
            yield m, c, v


def test_manifest_lists_cells_for_every_variant(manifest, site_dir):
    for m, c, v in _variants(manifest):
        f = v["files"]["cells"]
        assert f["path"] == f"maps/{m['id']}/{c}/cells.json"
        assert f["media_type"] == "application/json"
        data = (site_dir / f["path"]).read_bytes()
        assert len(data) == f["bytes"] and hashlib.sha256(data).hexdigest() == f["sha256"]
        assert len(data) < 300_000                                   # SC-005
        cells = json.loads(data)
        assert cells["recipe"]["id"] == m["id"] and cells["arrangement"] == c
        assert cells["disclaimer"] == DISCLAIMER and cells["note"] == NOTE


def test_default_rendering_equals_layout(manifest, site_dir):
    """SC-001: the chooser's default colors are the built layout's colors, stud for stud."""
    for m, c, v in _variants(manifest):
        cells = json.loads((site_dir / v["files"]["cells"]["path"]).read_text(encoding="utf-8"))
        layout = json.loads((site_dir / v["files"]["layout"]["path"]).read_text(encoding="utf-8"))
        want = {(p["x"], p["y"]): p["color_id"] for p in layout["positions"]}
        W = cells["width"]
        for i, k in enumerate(cells["cells"]):
            if k == "S":
                got = cells["shadow"]["color"]
            else:
                layer = cells["layers"]["land" if k == "L" else "ocean"]
                got = layer["colors"][layer["classes"][i]]
            assert got == want[(i % W, i // W)], (m["id"], c, i)


def test_cells_route(client, manifest):
    f = manifest["maps"][0]["variants"]["A"]["files"]["cells"]
    r = client.get(f"/maps/{manifest['maps'][0]['id']}/A/cells.json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "attachment" not in r.headers.get("content-disposition", "")
    assert hashlib.sha256(r.content).hexdigest() == f["sha256"]
    assert "max-age" in r.headers["cache-control"]


@pytest.mark.parametrize("path", ["/maps/nope/A/cells.json", "/maps/ocean-sst/F/cells.json",
                                  "/maps/ocean-sst/A/download/cells"])
def test_cells_route_not_found(client, path):
    assert client.get(path).status_code == 404


def test_csp_allows_only_own_scripts(client):
    csp = client.get("/maps/ocean-sst/A").headers["content-security-policy"]
    assert "script-src 'self'" in csp and "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "default-src 'none'" in csp


def test_script_served_first_party(client):
    r = client.get("/static/palette.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/javascript")
    assert len(r.content) < 30_000                                     # SC-003
    text = r.text
    assert DISCLAIMER in text
    for banned in ("http://", "https://", "document.cookie", "localStorage", "sessionStorage",
                   "indexedDB", "eval(", "new Function", "innerHTML"):
        assert banned not in text, banned


def test_map_page_chooser_markup(client):
    html = client.get("/maps/ocean-sst/B").text
    assert re.search(r'<section [^>]*id="palette"[^>]*hidden', html)
    assert 'data-cells="/maps/ocean-sst/B/cells.json"' in html
    assert re.search(r'<script src="/static/palette\.js\?v=[^"]+" defer></script>', html)
    assert "<noscript>" in html and "needs JavaScript" in html
    assert NOTE in html
    assert DISCLAIMER in html
    # the no-JS preview stays the built image, and every download is unchanged
    assert 'src="/maps/ocean-sst/B/preview.png"' in html
    assert "/download/cells" not in html


def test_downloads_and_parts_unchanged_by_chooser(client, manifest):
    """FR-019: the chooser adds no download kind; the download list is feature 008's."""
    from web98138.catalog import DOWNLOAD_KINDS

    assert "cells" not in DOWNLOAD_KINDS
    html = client.get("/maps/ocean-sst/A").text
    assert html.count("/download/") == sum(1 for k in DOWNLOAD_KINDS
                                           if k in manifest["maps"][1]["variants"]["A"]["files"])


def test_about_mentions_chooser_and_ice(client):
    html = client.get("/about").text
    assert "Try other colors" in html
    assert "preview only" in html.lower()
    assert "60° S" in html and "ERSST" in html


def test_old_output_without_cells_still_serves(site_dir, tmp_path):
    """A build from before this feature (no cells files): no chooser, page otherwise unchanged."""
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    out = tmp_path / "site"
    shutil.copytree(site_dir, out)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for mm in m["maps"]:
        for v in mm["variants"].values():
            v["files"].pop("cells")
    (out / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with TestClient(create_app(out), base_url="https://98138.world") as c:
        html = c.get("/maps/ocean-sst/A").text
        assert 'id="palette"' not in html and "<script" not in html
        assert c.get("/maps/ocean-sst/A/cells.json").status_code == 404


# --- the script's pure functions, run with Node when it is installed --------------------------

NODE = shutil.which("node")

HARNESS = r"""
const P = require(process.argv[2]);
const fs = require('fs');
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const layout = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const out = {};
const st = P.defaultState(data);
const keys = P.cellColors(data, st);
const want = new Array(data.width * data.height);
for (const p of layout.positions) want[p.y * data.width + p.x] = p.color_id;
out.defaultEqualsLayout = keys.every((k, i) => k === want[i]);
out.bins = [P.classOf(-5, [0, 10]), P.classOf(0, [0, 10]), P.classOf(9.99, [0, 10]),
            P.classOf(10, [0, 10]), P.classOf(99, [0, 10])];
out.equal = P.equalShareBounds([1, 2, 3, 4, 5, 6, 7, 8], 4, 2);
out.spread = P.spreadColors(['a', 'b', 'c'], 5);
out.valid = [P.validBounds([1, 2, 3]), P.validBounds([1, 1, 3]), P.validBounds([3, 2]),
             P.validBounds([1, NaN])];
// ice White: every ice cell White except the shadow; shares count data cells only
const iceSt = P.defaultState(data); iceSt.ice = 'white';
const iceKeys = P.cellColors(data, iceSt);
out.iceWhite = data.ice.land.concat(data.ice.sea).every(i => data.cells[i] === 'S' ? iceKeys[i] === data.shadow.color : iceKeys[i] === 'lego_white');
const sh = P.classShares(data, iceSt, 'ocean');
out.iceShareTotal = sh.reduce((a, b) => a + b.cells, 0);
out.oceanCells = data.layers.ocean.cells;
out.oceanIce = data.ice.sea.filter(i => data.cells[i] === 'O').length;
// recolor one class
const rc = P.defaultState(data); rc.layers.ocean.colors[0] = 'lego_black';
const rk = P.cellColors(data, rc);
out.recolor = data.layers.ocean.classes.every((c, i) => c !== 0 || rk[i] === 'lego_black');
// custom bins on a data layer
const ocean = data.layers.ocean;
if (ocean.bounds) {
  const cb = P.defaultState(data); cb.layers.ocean.bounds = [ocean.bounds[1]]; cb.layers.ocean.colors = ['lego_black', 'lego_white'];
  const ck = P.cellColors(data, cb);
  out.custom = ocean.values.every((v, i) => data.cells[i] !== 'O' || ck[i] === (v < ocean.bounds[1] ? 'lego_black' : 'lego_white'));
}
// fragment round trip and rejection
const enc = P.encodeState(data, rc);
const dec = P.decodeState(data, enc);
out.roundTrip = JSON.stringify(dec.state) === JSON.stringify(rc);
out.badColor = P.decodeState(data, enc.replace('lego_black', 'lego_nope')).error !== null;
out.otherMap = P.decodeState(Object.assign({}, data, {recipe: {id: 'x'}}), enc).error !== null;
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed")
@pytest.mark.parametrize("map_id,c", [("ocean-sst", "A"), ("official-31203", "C"), ("ocean-el-nino", "B"),
                                      ("ocean-sst", "winkel-tripel")])   # feature 016: margin cells
def test_script_functions_with_node(site_dir, tmp_path, map_id, c):
    h = tmp_path / "harness.js"
    h.write_text(HARNESS, encoding="utf-8")
    d = site_dir / "maps" / map_id / c
    r = subprocess.run([NODE, str(h), str(SCRIPT), str(d / "cells.json"), str(d / "layout.json")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["defaultEqualsLayout"] is True
    assert out["bins"] == [0, 1, 1, 2, 2]
    assert out["equal"] == [2.5, 4.5, 6.5]
    assert out["spread"] == ["a", "b", "b", "c", "c"]
    assert out["valid"] == [True, False, False, False]
    assert out["iceWhite"] is True
    assert out["iceShareTotal"] == out["oceanCells"] - out["oceanIce"]
    assert out["recolor"] is True
    assert out.get("custom", True) is True
    assert out["roundTrip"] is True and out["badColor"] is True and out["otherMap"] is True



# --- feature 016: template variants (US3-4; FR-012, FR-020a; contracts/recipe-and-outputs.md) --

TEMPLATE_HARNESS = r"""
const P = require(process.argv[2]);
const fs = require('fs');
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = {};
const M = [];
for (let i = 0; i < data.cells.length; i++) if (data.cells[i] === 'M') M.push(i);
out.margins = M.length;
const margin = data.margin.color;
const other = data.palette['3070b'].map(r => r.key).find(k => k !== margin);
// default, recolored and ice White: margin cells keep the margin color
const st = P.defaultState(data);
out.defaultMargin = M.every(i => P.cellColors(data, st)[i] === margin);
const rc = P.defaultState(data);
rc.layers.land.colors = rc.layers.land.colors.map(() => 'lego_black');
rc.layers.ocean.colors = rc.layers.ocean.colors.map(() => 'lego_white');
const rk = P.cellColors(data, rc);
out.recolorOthers = rk.every((k, i) => data.cells[i] === 'M' || data.cells[i] === 'S' ||
                             k === (data.cells[i] === 'L' ? 'lego_black' : 'lego_white'));
rc.ice = 'white';
const wk = P.cellColors(data, rc);
out.recolorMargin = M.every(i => rk[i] === margin && wk[i] === margin);
out.iceWhite = data.ice.land.concat(data.ice.sea).every(i => data.cells[i] === 'S' || wk[i] === data.ice.color);
// ice flags leave margin cells out, even when an ice list names one
const iced = JSON.parse(JSON.stringify(data));
iced.ice.sea = iced.ice.sea.concat([M[0]]); iced.ice.land = iced.ice.land.concat([M[1]]);
const ik = P.cellColors(iced, Object.assign(P.defaultState(iced), {ice: 'white'}));
out.iceSkipsMargin = ik[M[0]] === margin && ik[M[1]] === margin;
// shares count land and ocean data studs only
const land = P.classShares(data, st, 'land').reduce((a, b) => a + b.cells, 0);
const ocean = P.classShares(data, st, 'ocean').reduce((a, b) => a + b.cells, 0);
out.landShare = land; out.oceanShare = ocean;
out.L = data.cells.split('').filter(k => k === 'L').length;
out.O = data.cells.split('').filter(k => k === 'O').length;
// the outline ring: ring cells in the ring color, the rest of the margin in the margin color
const ringed = JSON.parse(JSON.stringify(data));
ringed.margin.ring = {color: other, cells: M.slice(0, 7)};
const gk = P.cellColors(ringed, P.defaultState(ringed));
out.ring = M.every((i, j) => gk[i] === (j < 7 ? other : margin));
// drawing: rounds for land, ocean and shadow, squares for the margin, on black
const calls = [];
const ctx = {fillStyle: '', fillRect(x, y, w, h) { calls.push(['rect', x, y, w, h, this.fillStyle]); },
             beginPath() {}, arc(x, y, r) { calls.push(['arc', x, y, r, this.fillStyle]); }, fill() {}};
const rgb = (part, key) => data.palette[part].find(r => r.key === key).rgb;
P.drawStuds(ctx, data, P.cellColors(data, st), rgb, 10, 0.9);
out.background = calls[0];
const rects = calls.slice(1).filter(c => c[0] === 'rect'), arcs = calls.filter(c => c[0] === 'arc');
out.rects = rects.length; out.arcs = arcs.length;
const W = data.width, mrgb = 'rgb(' + rgb('3070b', margin).join(',') + ')';
out.squaresAtMargin = rects.every((c, j) => c[1] === (M[j] % W) * 10 && c[2] === Math.floor(M[j] / W) * 10 &&
                                  c[3] === 10 && c[4] === 10 && c[5] === mrgb);
out.radius = arcs.length ? arcs[0][3] : null;
out.marginColor = margin;
// owner 2026-11-24: Black margin studs are the black background (no square drawn); other margin
// colors and the ring keep their cited colors
const draw = (d) => {
  const c = [];
  const cx = {fillStyle: '', fillRect(x, y, w, h) { c.push([x / 10 + (y / 10) * W, this.fillStyle]); },
              beginPath() {}, arc() {}, fill() {}};
  P.drawStuds(cx, d, P.cellColors(d, P.defaultState(d)), rgb, 10, 0.9);
  return c.slice(1);
};
const css = (key) => 'rgb(' + rgb('3070b', key).join(',') + ')';
const yellow = data.palette['3070b'].map(r => r.key).find(k => k !== 'lego_black' && k !== 'lego_white');
const blackRing = JSON.parse(JSON.stringify(data));
blackRing.margin.color = 'lego_black'; blackRing.margin.ring = {color: yellow, cells: M.slice(0, 7)};
const br = draw(blackRing);
out.blackMarginRing = br.length === 7 && br.every((c, j) => c[0] === M[j] && c[1] === css(yellow));
const whiteBlack = JSON.parse(JSON.stringify(data));
whiteBlack.margin.color = 'lego_white'; whiteBlack.margin.ring = {color: 'lego_black', cells: M.slice(0, 7)};
const wb = draw(whiteBlack);
out.blackRingCited = wb.length === M.length &&
  wb.every((c, j) => c[0] === M[j] && c[1] === css(j < 7 ? 'lego_black' : 'lego_white'));
console.log(JSON.stringify(out));
"""


def _node(tmp_path, harness, cells):
    h = tmp_path / "harness.js"
    h.write_text(harness, encoding="utf-8")
    r = subprocess.run([NODE, str(h), str(SCRIPT), str(cells)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed")
def test_template_cells_with_node(site_dir, tmp_path):
    out = _node(tmp_path, TEMPLATE_HARNESS, site_dir / "maps" / "ocean-sst" / "winkel-tripel" / "cells.json")
    assert out["margins"] > 0
    assert out["defaultMargin"] and out["recolorMargin"] and out["recolorOthers"]
    assert out["iceSkipsMargin"] is True and out["iceWhite"] is True
    assert out["landShare"] == out["L"] and out["oceanShare"] == out["O"]
    assert out["ring"] is True
    assert out["background"] == ["rect", 0, 0, 1280, 800, "#000"]
    # the default margin is Black: its studs are the black background, no square drawn (owner,
    # 2026-11-24); land, ocean and shadow are rounds
    assert out["marginColor"] == "lego_black"
    assert out["rects"] == 0 and out["arcs"] == 10240 - out["margins"]
    assert out["squaresAtMargin"] is True and out["radius"] == 4.5
    assert out["blackMarginRing"] is True       # Black margin, colored ring: only the ring drawn
    assert out["blackRingCited"] is True        # White margin, Black ring: the ring in cited Black


KIT_DRAW = r"""
const P = require(process.argv[2]);
const data = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8'));
const calls = [];
const ctx = {fillStyle: '', fillRect() { calls.push('rect'); }, beginPath() {}, arc() { calls.push('arc'); }, fill() {}};
P.drawStuds(ctx, data, P.cellColors(data, P.defaultState(data)),
            (part, key) => data.palette[part].find(r => r.key === key).rgb, 10, 0.9);
console.log(JSON.stringify({rects: calls.filter(c => c === 'rect').length, arcs: calls.filter(c => c === 'arc').length}));
"""


@pytest.mark.skipif(NODE is None, reason="Node.js is not installed")
def test_kit_cells_draw_only_rounds_with_node(site_dir, tmp_path):
    out = _node(tmp_path, KIT_DRAW, site_dir / "maps" / "ocean-sst" / "B" / "cells.json")
    assert out == {"rects": 1, "arcs": 10240}      # the black background, then one round per stud


def test_template_page_chooser_markup(client):
    html = client.get("/maps/ocean-sst/winkel-tripel").text
    assert 'data-cells="/maps/ocean-sst/winkel-tripel/cells.json"' in html
    assert re.search(r'<script src="/static/palette\.js\?v=[^"]+" defer></script>', html)
    assert NOTE in html and 'src="/maps/ocean-sst/winkel-tripel/preview.png"' in html
