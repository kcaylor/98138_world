"""The rainfall map on the site (feature 013, US4): built from the CLI's fixtures, offline.

Not affiliated with or endorsed by The LEGO Group.
"""

import hashlib
import json
from html import escape

from web98138 import MAP_IDS

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def test_listed_in_the_site_maps():
    assert MAP_IDS[-1] == "rainfall" and len(MAP_IDS) == 8


def test_manifest_entry(rainfall_site):
    m = json.loads((rainfall_site / "manifest.json").read_text(encoding="utf-8"))
    (rf,) = m["maps"]
    assert rf["id"] == "rainfall" and rf["title"] == "Rainfall" and rf["default_combination"] == "A"
    assert sorted(rf["variants"]) == ["A", "B", "C"]
    gpcp, nsidc = rf["datasets"]
    assert gpcp["id"] == "gpcp-v23-ltm-1991-2020" and len(gpcp["sha256"]) == 64 and "files" not in gpcp
    assert nsidc["id"] == "nsidc-cdr-v6-seaice-minimum-1991-2020" and nsidc["sha256"] == ""
    assert nsidc["files"] == 4 and len(nsidc["files_sha256"]) == 64      # the fixture's 4 of 60
    assert {c["id"] for c in rf["citations"]} == {gpcp["id"], nsidc["id"]}


def test_map_page_and_downloads(rainfall_client, rainfall_site):
    m = json.loads((rainfall_site / "manifest.json").read_text(encoding="utf-8"))["maps"][0]
    r = rainfall_client.get("/maps/rainfall", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].endswith("/maps/rainfall/A")
    html = rainfall_client.get("/maps/rainfall/A").text
    assert escape(m["title"]) in html and escape(m["description"]) in html
    assert 'href="/maps/rainfall/B"' in html and 'href="/maps/rainfall/C"' in html
    assert "Adler" in html and "Meier" in html and "10.7265/b18j-z797" in html
    assert "Pinned files: nsidc-cdr-v6-seaice-minimum-1991-2020, 4 files" in html
    assert DISCLAIMER in html
    for c, v in m["variants"].items():
        for kind, f in v["files"].items():
            path = f"/maps/rainfall/{c}/" + (f"{kind}.png" if kind in ("preview", "thumb")
                                              else f"download/{kind}")
            resp = rainfall_client.get(path)
            assert resp.status_code == 200, (c, kind)
            assert hashlib.sha256(resp.content).hexdigest() == f["sha256"]
