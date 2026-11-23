"""Headers, privacy, health, fixed routes (FR-009, FR-017, FR-019, FR-021, FR-022)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "web98138"


@pytest.mark.parametrize("path", ["/", "/about", "/maps/ocean-sst/A", "/static/style.css",
                                  "/maps/ocean-sst/A/preview.png",
                                  "/maps/ocean-sst/A/download/layout", "/healthz", "/nope"])
def test_security_headers_no_cookies(client, path):
    r = client.get(path)
    h = r.headers
    assert "default-src 'none'" in h["content-security-policy"]
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff"
    assert h["referrer-policy"] == "no-referrer"
    assert h["x-frame-options"] == "DENY"
    assert "max-age=" in h["strict-transport-security"]
    assert "set-cookie" not in h
    assert "server" not in h or "uvicorn" not in h["server"]


def test_no_third_party_resources(client):
    for path in ("/", "/about", "/maps/ocean-sst/A", "/maps/official-31203/B"):
        html = client.get(path).text
        for attr in re.findall(r'(?:src|href)="([^"]+)"', html):
            tag_ok = attr.startswith("/") or attr.startswith("#")
            if not tag_ok:  # only plain links (<a>) may leave the site
                assert re.search(r'<a [^>]*href="' + re.escape(attr) + '"', html), attr
        for link in re.findall(r"<link [^>]*>", html):
            assert 'href="/' in link, link


def test_cache_headers(client):
    assert "max-age=86400" in client.get("/maps/ocean-sst/A/download/bricklink").headers["cache-control"]
    assert "max-age=86400" in client.get("/maps/ocean-sst/A/preview.png").headers["cache-control"]
    assert "max-age=300" in client.get("/").headers["cache-control"]
    r = client.get("/maps/ocean-sst/A/download/bricklink")
    etag = r.headers["etag"]
    assert client.get("/maps/ocean-sst/A/download/bricklink",
                      headers={"if-none-match": etag}).status_code == 304


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_framework_docs_disabled(client, path):
    assert client.get(path).status_code == 404


def test_www_redirects_to_apex(client):
    r = client.get("/maps/ocean-sst/A", headers={"host": "www.98138.world"}, follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://98138.world/maps/ocean-sst/A"


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok" and j["variants"] == 9 and j["generated_at"]


def test_manifest_public(client, site_dir):
    r = client.get("/manifest.json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert r.content == (site_dir / "manifest.json").read_bytes()


def test_robots(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")


@pytest.mark.parametrize("path", ["/maps/ocean-sst/A/download/..%2F..%2Fmanifest.json",
                                  "/maps/ocean-sst/A/download/%2e%2e",
                                  "/static/..%2F..%2Fmanifest.json", "/static/../catalog.py",
                                  "/maps/..%2F..%2Fetc/A", "/maps/ocean-sst/A/../../manifest.json/x"])
def test_traversal_404(client, path):
    assert client.get(path).status_code == 404


def test_post_not_allowed(client):
    assert client.post("/").status_code in (404, 405)


def test_head_allowed(client):
    assert client.head("/maps/ocean-sst/A/download/layout").status_code == 200


def test_service_does_not_import_the_library():
    for f in ("app.py", "catalog.py", "__init__.py"):
        tree = ast.parse((SRC / f).read_text())
        names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(n.startswith("lego_image_processor") for n in names), f
        assert not any(n.endswith("prebuild") for n in names), f


def test_missing_output_fails_at_startup(tmp_path):
    from web98138.app import create_app
    from web98138.catalog import CatalogError

    with pytest.raises(CatalogError):
        create_app(tmp_path)


def test_site_holds_no_price_fetch_config_or_credentials(site_dir):
    """FR-022: the build output has no API configuration, credentials or snapshot file."""
    names = {p.name for p in site_dir.rglob("*")}
    assert "bricklink_api.json" not in names
    assert "bricklink_price_guide.json" not in names
    assert not any(n.endswith(".progress.json") for n in names)
    for p in site_dir.rglob("*"):
        if p.is_file() and p.suffix in (".json", ".xml", ".csv", ".html"):
            text = p.read_text(encoding="utf-8")
            assert "BRICKLINK_" not in text, p
            assert "oauth" not in text.lower(), p
            assert "api.bricklink.com" not in text, p


def test_price_panel_links_only_plainly(client):
    html = client.get("/maps/official-31203/A").text
    assert '<a href="https://www.bricklink.com">' in html
    assert not re.search(r'<(?:img|link|script|iframe)[^>]+bricklink', html)
