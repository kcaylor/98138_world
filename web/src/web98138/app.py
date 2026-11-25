"""The 98138.world service: pages and files from the prebuilt output (FR-017-FR-022).

Fixed routes only. Map IDs, combinations and download kinds are looked up in the manifest; no
part of a URL is ever used as a file path. Nothing here imports ``lego_image_processor``: every
file and number shown was produced by the CLI library in the build step. Map pages load one
first-party script, ``/static/palette.js`` (feature 015), which only recolors the prebuilt
``cells.json`` in the browser; every page works without it. Feature 016: a map's template variants
(``/maps/<map>/<template-id>``, e.g. ``winkel-tripel``) are served like its combinations A, B, C;
kit pages gain only a nav link to them. Each map's sticker set (feature 017) is served under
``/maps/<map>/stickers/<template>/``: both SVGs inline for the page's ``<img>`` and all four files
as downloads. Kit pages show the kit template's set, a template page its template's set.

Run: ``WEB98138_SITE_DIR=DIR uvicorn web98138.app:app --port 8080``.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import COMBINATIONS, DISCLAIMER, REPO_URL, SITE_HOST, __version__
from .catalog import DOWNLOAD_KINDS, KIT_TEMPLATE_ID, STICKER_IMAGES, STICKER_KINDS, Catalog

PKG = Path(__file__).resolve().parent
STATIC = {"style.css": "text/css; charset=utf-8", "favicon.svg": "image/svg+xml",
          "palette.js": "text/javascript; charset=utf-8"}
FILE_CACHE = "public, max-age=86400"
PAGE_CACHE = "public, max-age=300"
SECURITY_HEADERS = {
    # feature 015 (FR-008, FR-020): the site's own palette.js and its cells.json fetch only
    "content-security-policy": ("default-src 'none'; img-src 'self'; style-src 'self'; "
                                "script-src 'self'; connect-src 'self'; "
                                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "strict-transport-security": "max-age=63072000",
    "cross-origin-opener-policy": "same-origin",
}
ROLE_LABEL = {"data": "data-driven", "background": "background"}


def _size(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{n / 1_000:.0f} kB"
    return f"{n} bytes"


def _fmt(n: Any) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def _usd(n: Any) -> str:
    """Whole dollars from the manifest (integers computed by the CLI library): ``$1,150``."""
    return f"${n:,}" if isinstance(n, int) and not isinstance(n, bool) else str(n)


def _plural(n: Any, word: str) -> str:
    return f"{_fmt(n)} {word}" + ("" if n == 1 else "s")


def _ext(entry: Dict[str, Any]) -> str:
    return entry["path"].rsplit(".", 1)[-1].upper()


def create_app(site_dir) -> FastAPI:
    """The ASGI app serving ``site_dir`` (checked now; raises ``CatalogError`` if unusable)."""
    catalog = Catalog.load(site_dir)
    m = catalog.manifest
    etag_base = (m.get("generated_at") or "") + __version__
    statics = b"".join((PKG / "static" / n).read_bytes() for n in sorted(STATIC))
    asset_version = f"{__version__}-{hashlib.sha256(catalog.raw + statics).hexdigest()[:10]}"
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, debug=False,
                  title="98138.world")
    templates = Jinja2Templates(directory=str(PKG / "templates"))
    env = templates.env
    env.filters["n"] = _fmt
    env.filters["size"] = _size
    env.filters["ext"] = _ext
    env.filters["usd"] = _usd
    env.filters["plural"] = _plural
    env.globals.update(DISCLAIMER=DISCLAIMER, REPO_URL=REPO_URL, manifest=m,
                       asset_version=asset_version, arrangements=m["arrangements"],
                       role_label=ROLE_LABEL, part_labels=m.get("part_labels", {}),
                       download_kinds=DOWNLOAD_KINDS, catalog=catalog)

    @app.middleware("http")
    async def headers(request: Request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host == f"www.{SITE_HOST}":
            url = f"https://{SITE_HOST}{request.url.path}"
            if request.url.query:
                url += f"?{request.url.query}"
            response: Response = RedirectResponse(url, status_code=301)
        else:
            response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if "server" in response.headers:
            del response.headers["server"]
        return response

    def page(request: Request, name: str, status: int = 200, **ctx) -> Response:
        r = templates.TemplateResponse(request, name, ctx, status_code=status)
        r.headers["cache-control"] = PAGE_CACHE if status == 200 else "no-store"
        return r

    def not_found(request: Request) -> Response:
        return page(request, "error.html", 404, title="Not found",
                    message="There is no page at this address.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 405:
            return page(request, "error.html", 405, title="Method not allowed",
                        message="This site only answers GET requests.")
        return not_found(request)

    def serve(request: Request, entry: Dict[str, Any], path: Path, attachment: bool) -> Response:
        etag = f'"{entry["sha256"][:32]}"'
        hdrs = {"cache-control": FILE_CACHE, "etag": etag}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=hdrs)
        return FileResponse(path, media_type=entry["media_type"], headers=hdrs,
                            filename=entry["filename"] if attachment else None)

    get = lambda path: app.api_route(path, methods=["GET", "HEAD"], include_in_schema=False)  # noqa: E731

    @get("/")
    async def home(request: Request):
        return page(request, "home.html", maps=catalog.maps)

    @get("/about")
    async def about(request: Request):
        return page(request, "about.html", maps=catalog.maps)

    @get("/maps/{map_id}")
    async def map_root(request: Request, map_id: str):
        if catalog.map(map_id) is None:
            return not_found(request)
        return RedirectResponse(f"/maps/{map_id}/{catalog.map(map_id).default_combination}", status_code=307)

    # feature 017: sticker files, registered before the combination routes
    def sticker_image(kind: str):
        async def handler(request: Request, map_id: str, template_id: str):
            entry = catalog.sticker_entry(map_id, template_id, kind)
            if entry is None:
                return not_found(request)
            return serve(request, entry, catalog.sticker_file(map_id, template_id, kind), False)
        return handler

    for kind in STICKER_IMAGES:
        get(f"/maps/{{map_id}}/stickers/{{template_id}}/{kind}.svg")(sticker_image(kind))

    @get("/maps/{map_id}/stickers/{template_id}/download/{kind}")
    async def sticker_download(request: Request, map_id: str, template_id: str, kind: str):
        entry = catalog.sticker_entry(map_id, template_id, kind) if kind in STICKER_KINDS else None
        if entry is None:
            return not_found(request)
        return serve(request, entry, catalog.sticker_file(map_id, template_id, kind), True)

    @get("/maps/{map_id}/{combination}")
    async def map_page(request: Request, map_id: str, combination: str):
        entry = catalog.map(map_id)
        if entry is None:
            return not_found(request)
        template = None
        if combination not in COMBINATIONS:
            if combination in entry.template_ids:   # feature 016: a template variant
                template = catalog.template(combination)
            elif combination.upper() in COMBINATIONS:
                return RedirectResponse(f"/maps/{map_id}/{combination.upper()}", status_code=301)
            else:
                return not_found(request)
        variant = entry.variant(combination)
        # feature 017: the kit's sticker set on kit pages, the template's own set on a template page
        sticker_template = combination if template is not None else KIT_TEMPLATE_ID
        return page(request, "map.html", map=entry, data=entry.data, variant=variant,
                    combination=combination, arrangement=catalog.arrangement(combination),
                    template=template, map_templates=[catalog.template(t) for t in entry.template_ids],
                    stickers=catalog.stickers(map_id, sticker_template), sticker_template=sticker_template)

    def image(kind: str):
        async def handler(request: Request, map_id: str, combination: str):
            entry = catalog.file_entry(map_id, combination, kind)
            if entry is None:
                return not_found(request)
            return serve(request, entry, catalog.file(map_id, combination, kind), False)
        return handler

    get("/maps/{map_id}/{combination}/preview.png")(image("preview"))
    get("/maps/{map_id}/{combination}/thumb.png")(image("thumb"))
    get("/maps/{map_id}/{combination}/cells.json")(image("cells"))  # feature 015, inline JSON

    @get("/maps/{map_id}/{combination}/download/{kind}")
    async def download(request: Request, map_id: str, combination: str, kind: str):
        entry = catalog.file_entry(map_id, combination, kind) if kind in DOWNLOAD_KINDS else None
        if entry is None:
            return not_found(request)
        return serve(request, entry, catalog.file(map_id, combination, kind), True)

    @get("/manifest.json")
    async def manifest_json(request: Request):
        return Response(catalog.raw, media_type="application/json",
                        headers={"cache-control": PAGE_CACHE, "etag": f'"{etag_base}"'})

    @get("/healthz")
    async def healthz(request: Request):
        return JSONResponse({"status": "ok", "variants": catalog.variant_count,
                             "generated_at": m.get("generated_at"), "version": __version__},
                            headers={"cache-control": "no-store"})

    @get("/robots.txt")
    async def robots(request: Request):
        return PlainTextResponse("User-agent: *\nAllow: /\n", headers={"cache-control": PAGE_CACHE})

    @get("/static/{name}")
    async def static(request: Request, name: str):
        media = STATIC.get(name)
        if media is None:
            return not_found(request)
        return FileResponse(PKG / "static" / name, media_type=media,
                            headers={"cache-control": FILE_CACHE})

    return app


def _from_env() -> FastAPI:
    site = os.environ.get("WEB98138_SITE_DIR")
    if not site:
        raise RuntimeError("set WEB98138_SITE_DIR to the build step's output directory "
                           "(python -m web98138.prebuild --out DIR)")
    return create_app(site)


_app: Optional[FastAPI] = None


def __getattr__(name: str):  # lazy ``app`` for ``uvicorn web98138.app:app``
    global _app
    if name == "app":
        if _app is None:
            _app = _from_env()
        return _app
    raise AttributeError(name)
