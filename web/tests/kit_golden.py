"""Digests of a site's kit variants (feature 016, T009; SC-001, SC-006, research R9).

``site_digests(site_dir)`` digests every kit variant (``variants.A/B/C``) of a prebuilt site:

- timestamp-free files byte for byte: previews, thumbnails, BrickLink and Rebrickable exports,
  ``cells.json``;
- the layout and both parts lists after normalisation: ``metadata.generated_at`` removed from the
  layout, the layout's SHA-256 (``layout.sha256``) removed from the parts lists, then canonical
  JSON. The sheets PDFs embed the layout checksum and are covered by the CLI golden instead;
- the manifest variant entry, without the ``sha256`` and ``bytes`` of the files that embed the
  layout checksum or a timestamp (layout, parts lists, sheets PDFs);
- the rendered HTML of the map page ``/maps/<map>/<C>``, with the content-versioned asset tokens
  (``?v=…``) and the footer's build date and commit normalised.

Feature 016 (T089) allows exactly two changes of a site that also has template variants: each kit
page of a map with a template variant carries one nav item linking to it (``template_nav_item``),
which ``strip_template_nav`` removes before the page is digested (it must be there exactly once,
and a map without template variants must have none); and the site's ``part_labels`` add the
square tile (``TEMPLATE_PART_LABELS``). A site without template variants (main's) digests exactly
as before, so the golden file can still be written from an unmodified main.

It also keeps each map row of the manifest (fields other than ``variants``, digested; later
additive fields are not compared) and the top-level ``part_labels``. ``compare`` names the site,
map, combination and item that differ.

Feature 017 (T060) allows one more change of a site with template variants: each template variant
has its own sticker set in the map row's ``stickers`` (FR-020). ``kit_stickers`` removes those
sets before the row's ``stickers`` field is digested (``row_digests``), so the kit set is still
compared exactly; each template variant must have exactly one set, and no other non-kit set may be
there. A site without template variants digests exactly as before.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping

GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "kit_variants_golden.json"
FORMAT_VERSION = "1"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
COMBINATIONS = ("A", "B", "C")
# files that embed the layout checksum or a timestamp: no size or checksum in the normalised entry
LAYOUT_DERIVED = ("layout", "parts", "parts-1kit", "sheets-letter", "sheets-a4")
NORMALISED = ("layout", "parts", "parts-1kit")
SKIPPED = ("sheets-letter", "sheets-a4")   # PDFs: covered by the CLI golden
ASSET_TOKEN = "<asset>"
TEMPLATE_PART_LABELS = {"3070b": "tile 1x1 square"}   # feature 016: added only with template variants
KIT_TEMPLATE_ID = "kit-31203"   # feature 017: the kit's sticker set (catalog.KIT_TEMPLATE_ID)
_ASSET = re.compile(r"\?v=[^\"'&\s>]+")
_BUILT = re.compile(r"Built \d{4}-\d{2}-\d{2} with lego-image-processor (\S+?)(?: \(commit [0-9a-f]+\))?;")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def normalise_file(kind: str, data: bytes) -> bytes:
    """The bytes compared for a file of ``kind``: layout and parts lists normalised, others as is."""
    if kind == "layout":
        d = json.loads(data)
        d["metadata"].pop("generated_at", None)
        return canonical(d)
    if kind in ("parts", "parts-1kit"):
        d = json.loads(data)
        d["layout"].pop("sha256", None)
        return canonical(d)
    return data


def normalise_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """A manifest variant entry without the checksums and sizes that derive from the layout."""
    e = copy.deepcopy(dict(entry))
    for kind in LAYOUT_DERIVED:
        f = e.get("files", {}).get(kind)
        if f is not None:
            f.pop("sha256", None)
            f.pop("bytes", None)
    return e


def normalise_page(html: str) -> str:
    """A rendered page with asset tokens and the footer's build date and commit normalised."""
    html = _ASSET.sub("?v=" + ASSET_TOKEN, html)
    return _BUILT.sub(r"Built <date> with lego-image-processor \1;", html)


def template_nav_item(map_id: str, template_id: str) -> "re.Pattern[str]":
    """The nav item a kit page gains for a template variant (feature 016; map.html), with the
    whitespace before it, so that removing it leaves main's page."""
    return re.compile(r'\n      <li class="combo-template"><a href="/maps/' + re.escape(map_id) + "/"
                      + re.escape(template_id)
                      + r'"><span class="combo-id">[^<]+</span> <span class="combo-name">[^<]+</span></a></li>')


def strip_template_nav(html: str, map_id: str, template_ids) -> str:
    """``html`` without one nav item per template variant; raises if one is missing or doubled, or
    if any other template nav item is left."""
    for tid in template_ids:
        pattern = template_nav_item(map_id, tid)
        n = len(pattern.findall(html))
        if n != 1:
            raise AssertionError(f"/maps/{map_id}: {n} nav items for template {tid}, expected 1")
        html = pattern.sub("", html)
    if 'class="combo-template"' in html:
        raise AssertionError(f"/maps/{map_id}: a template nav item for a template it has no variant on")
    return html


def kit_stickers(stickers: Mapping[str, Any], map_id: str, template_ids) -> Dict[str, Any]:
    """A map row's ``stickers`` without its template variants' sets (feature 017, FR-020): the
    kit set as main's site has it. Raises if the kit set is missing, if a template variant has no
    set, or if a non-kit set belongs to no template variant."""
    tids = list(template_ids)
    if KIT_TEMPLATE_ID not in stickers:
        raise AssertionError(f"{map_id}: no {KIT_TEMPLATE_ID} sticker set")
    for tid in tids:
        if tid not in stickers:
            raise AssertionError(f"{map_id}: no sticker set for template variant {tid}")
    extra = [t for t in stickers if t != KIT_TEMPLATE_ID and t not in tids]
    if extra:
        raise AssertionError(f"{map_id}: sticker sets for {', '.join(extra)}, which it has no variant on")
    return {k: v for k, v in stickers.items() if k not in tids}


def row_digests(m: Mapping[str, Any]) -> Dict[str, str]:
    """Digests of a manifest map row's fields other than ``variants``; ``stickers`` as
    ``kit_stickers`` leaves it."""
    tids = list(m.get("template_variants") or ())
    out = {}
    for k, v in m.items():
        if k == "variants":
            continue
        if k == "stickers":
            v = kit_stickers(v, m["id"], tids)
        out[k] = _sha(canonical(v))
    return out


def page_digest(html: str) -> str:
    return _sha(normalise_page(html).encode("utf-8"))


def site_digests(site_dir, name: str = "site") -> Dict[str, Any]:
    """Digests of every kit variant of the site in ``site_dir`` (see the module docstring)."""
    from fastapi.testclient import TestClient

    from web98138.app import create_app

    site_dir = Path(site_dir)
    manifest = json.loads((site_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: Dict[str, Dict[str, str]] = {}
    variants: List[Dict[str, Any]] = []
    templates: Dict[str, List[str]] = {}
    with TestClient(create_app(site_dir), base_url="https://98138.world") as client:
        for m in manifest["maps"]:
            rows[m["id"]] = row_digests(m)
            tids = list(m.get("template_variants") or ())
            if tids:
                templates[m["id"]] = tids
            for c in COMBINATIONS:
                entry = m["variants"][c]
                d: Dict[str, str] = {}
                for kind, f in entry["files"].items():
                    if kind in SKIPPED:
                        continue
                    name_ = f["path"].rsplit("/", 1)[1] + (" (normalised)" if kind in NORMALISED else "")
                    d[name_] = _sha(normalise_file(kind, (site_dir / f["path"]).read_bytes()))
                d["manifest entry (normalised)"] = _sha(canonical(normalise_entry(entry)))
                path = f"/maps/{m['id']}/{c}"
                r = client.get(path)
                if r.status_code != 200:
                    raise AssertionError(f"{path}: HTTP {r.status_code}")
                d[f"page {path}"] = page_digest(strip_template_nav(r.text, m["id"], tids))
                variants.append({"map": m["id"], "combination": c, "digests": d})
    doc = {"site": name, "maps": [m["id"] for m in manifest["maps"]],
           "part_labels": manifest.get("part_labels"), "map_rows": rows, "variants": variants}
    if templates:   # feature 016; never in main's golden
        doc["template_variants"] = templates
    return doc


def golden_document(sites: Mapping[str, Any]) -> Dict[str, Any]:
    """The golden document for ``sites`` (name -> site directory)."""
    return {"format_version": FORMAT_VERSION,
            "title": "Digests of the web site's kit variants (feature 016, SC-001, SC-006)",
            "generator": "web/tests/test_kit_golden.py with KIT_GOLDEN_WRITE=1",
            "sites": [site_digests(d, name) for name, d in sites.items()],
            "disclaimer": DISCLAIMER}


def compare(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> List[str]:
    """Differences, naming the site, map, combination and item."""
    diffs: List[str] = []
    es = {s["site"]: s for s in expected["sites"]}
    acts = {s["site"]: s for s in actual["sites"]}
    for site in sorted(set(es) | set(acts)):
        if site not in acts or site not in es:
            diffs.append(f"{site}: site {'missing' if site not in acts else 'unexpected'}")
            continue
        e, a = es[site], acts[site]
        if e["maps"] != a["maps"]:
            diffs.append(f"{site}: maps {a['maps']} instead of {e['maps']}")
        want = dict(e["part_labels"] or {})
        if a.get("template_variants"):   # feature 016: the square tile, and nothing else
            want.update(TEMPLATE_PART_LABELS)
        if want != a["part_labels"]:
            diffs.append(f"{site}: part_labels {a['part_labels']} instead of {want}")
        for map_id, fields in e["map_rows"].items():
            got = a["map_rows"].get(map_id, {})
            for k, v in fields.items():
                if got.get(k) != v:
                    diffs.append(f"{site} {map_id}: manifest map field {k} differs")
        ev = {(v["map"], v["combination"]): v["digests"] for v in e["variants"]}
        av = {(v["map"], v["combination"]): v["digests"] for v in a["variants"]}
        for key in sorted(set(ev) | set(av)):
            where = f"{site} {key[0]} {key[1]}"
            if key not in av or key not in ev:
                diffs.append(f"{where}: variant {'missing' if key not in av else 'unexpected'}")
                continue
            for item in sorted(set(ev[key]) | set(av[key])):
                if item not in av[key]:
                    diffs.append(f"{where}: {item} missing")
                elif item not in ev[key]:
                    diffs.append(f"{where}: {item} unexpected")
                elif ev[key][item] != av[key][item]:
                    diffs.append(f"{where}: {item} differs")
    return diffs


_LEAF = re.compile(r'\{\n(?:[ ]+"[^"\n]*": (?:"[^"\n]*"|-?\d+|true|false|null),?\n)+[ ]*\}')


def to_text(doc: Mapping[str, Any]) -> str:
    """Indented JSON with each innermost object on one line."""
    text = json.dumps(doc, indent=2, ensure_ascii=False)
    return _LEAF.sub(lambda m: "{" + ", ".join(x.strip().rstrip(",") for x in
                                               m.group(0)[1:-1].strip().split("\n")) + "}", text) + "\n"
