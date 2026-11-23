"""The living-planet map on the site (feature 012, US3): built from the CLI's fixtures, offline.

Not affiliated with or endorsed by The LEGO Group.
"""

import hashlib
import json
from html import escape

from web98138 import MAP_IDS

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


def test_listed_in_the_site_maps():
    assert "living-planet" in MAP_IDS and len(MAP_IDS) == 8   # 013 added rainfall


def test_manifest_entry(living_site):
    m = json.loads((living_site / "manifest.json").read_text(encoding="utf-8"))
    (lp,) = m["maps"]
    assert lp["id"] == "living-planet" and lp["default_combination"] == "A"
    assert sorted(lp["variants"]) == ["A", "B", "C"]
    assert [d["id"] for d in lp["datasets"]] == ["mod17a3-npp-mean-2000-2015", "etopo2022-surface-10m",
                                                 "modis-aqua-chla-2013-2024"]
    chl = lp["datasets"][2]
    assert chl["sha256"] == "" and len(chl["content_sha256"]) == 64
    assert {c["id"] for c in lp["citations"]} >= {"mod17a3-npp-mean-2000-2015", "modis-aqua-chla-2013-2024",
                                                  "etopo2022-surface-10m"}


def test_map_page_and_downloads(living_client, living_site):
    m = json.loads((living_site / "manifest.json").read_text(encoding="utf-8"))["maps"][0]
    r = living_client.get("/maps/living-planet", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"].endswith("/maps/living-planet/A")
    html = living_client.get("/maps/living-planet/A").text
    assert escape(m["title"]) in html and escape(m["description"]) in html
    assert 'href="/maps/living-planet/B"' in html and 'href="/maps/living-planet/C"' in html
    assert "Zhao" in html and "R2022.0" in html and "ETOPO 2022" in html
    assert DISCLAIMER in html
    assert "content SHA-256 <code" in html and "SHA-256 <code class=\"hash\">…" not in html
    for c, v in m["variants"].items():
        for kind, f in v["files"].items():
            path = f"/maps/living-planet/{c}/" + (f"{kind}.png" if kind in ("preview", "thumb")
                                                   else f"download/{kind}")
            resp = living_client.get(path)
            assert resp.status_code == 200, (c, kind)
            assert hashlib.sha256(resp.content).hexdigest() == f["sha256"]
