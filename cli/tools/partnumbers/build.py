"""Build ``data/part_numbers.json`` from pinned archived BrickLink and Rebrickable part pages.

For each of the kit's two map parts (project IDs 6141 plate, 98138 tile) the tool reads:

- the BrickLink catalog page (Internet Archive raw copy): catalog name, item number, alternate item
  numbers and the color list of the page's "All" color tab (BrickLink color IDs and names);
- the Rebrickable part page (Internet Archive raw copy): part number, name and the "External
  Sites" cross-references (LEGO design IDs, BrickLink numbers).

Consistency rules (any failure stops the build):

1. Rebrickable's part number equals the project part ID.
2. The project part ID is the BrickLink item number or one of its alternates.
3. Rebrickable's BrickLink cross-reference lists the BrickLink item number.
4. The BrickLink item number is one of the kit inventory's ``part_ids`` for the part (003 data).
5. LEGO design IDs = the project part ID plus the kit inventory's design IDs for the part, each
   listed by Rebrickable under "LEGO".

Pages are pinned by URL and SHA-256 of the decoded HTML; they live in the maintainer cache
(``<cache>/sources/partnumbers/``), never in the repository. Rebrickable's terms forbid scraping
its live pages, so only archived copies are used.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from lego_image_processor.kit.source import DISCLAIMER

ACCESSED = "2026-11-22"
PAGES: Tuple[Dict[str, str], ...] = (
    {"id": "bricklink-4073", "kind": "bricklink", "part": "6141", "file": "bricklink-4073.html",
     "title": "BrickLink catalog item 4073, Plate, Round 1 x 1 (Internet Archive copy of 2026-11-04)",
     "url": "http://web.archive.org/web/20261104074336id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=4073",
     "sha256": "957f23bd90a68006f3cbf7f1f4461a6d5de89f2b9b6ed67b5b14533db0b2c146", "accessed": ACCESSED},
    {"id": "bricklink-98138", "kind": "bricklink", "part": "98138", "file": "bricklink-98138.html",
     "title": "BrickLink catalog item 98138, Tile, Round 1 x 1 (Internet Archive copy of 2026-09-01)",
     "url": "http://web.archive.org/web/20260901170641id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=98138",
     "sha256": "d1683255e9ecb05ade31884614beb278526aed13efb5725cbc53f74f9e7ffeb0", "accessed": ACCESSED},
    {"id": "rebrickable-6141", "kind": "rebrickable", "part": "6141", "file": "rebrickable-6141.html",
     "title": "Rebrickable part 6141, Plate Round 1 x 1 with Solid Stud (Internet Archive copy of 2026-04-07)",
     "url": "http://web.archive.org/web/20260407093646id_/https://rebrickable.com/parts/6141/",
     "sha256": "d7e3a955add1e5080be58ab58bfc5e5719e4499950cdae7a0c186fcfa00e51f7", "accessed": ACCESSED},
    {"id": "rebrickable-98138", "kind": "rebrickable", "part": "98138", "file": "rebrickable-98138.html",
     "title": "Rebrickable part 98138, Tile Round 1 x 1 (Internet Archive copy of 2025-03-03)",
     "url": "http://web.archive.org/web/20250303234033id_/https://rebrickable.com/parts/98138/",
     "sha256": "4195c1bd0c0b0b5b01384f397e45be2737739a4b34d13dc942eeb9f1475a2fac", "accessed": ACCESSED},
)
PARTS = ("6141", "98138")
ROLE_FOR_PART = {"6141": "land", "98138": "ocean"}
USER_AGENT = "lego-image-processor maintainer tool (archived page fetch)"


class SourceError(Exception):
    """A pinned page is missing or its checksum differs (exit 4)."""

    exit_code = 4


class BuildError(Exception):
    """The pages disagree with each other or with the kit inventory (exit 5)."""

    exit_code = 5


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_pages(source_dir: Path, pages: Sequence[Mapping[str, str]] = PAGES) -> Dict[str, str]:
    out = {}
    for p in pages:
        path = Path(source_dir) / p["file"]
        if not path.is_file():
            raise SourceError(f"page {p['id']} missing: {path} (download {p['url']})")
        b = path.read_bytes()
        if sha256_bytes(b) != p["sha256"]:
            raise SourceError(f"page {p['id']} checksum mismatch: expected {p['sha256']}, "
                              f"actual {sha256_bytes(b)} ({path})")
        out[p["id"]] = b.decode("utf-8", "replace")
    return out


def fetch_missing(source_dir: Path, pages: Sequence[Mapping[str, str]] = PAGES) -> List[str]:
    """Download pinned pages that are not cached yet (maintainer use only; never in tests)."""
    source_dir = Path(source_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    fetched = []
    for p in pages:
        dest = source_dir / p["file"]
        if dest.is_file():
            continue
        req = urllib.request.Request(p["url"], headers={"User-Agent": USER_AGENT,
                                                        "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (pinned URL)
            body = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
        if sha256_bytes(body) != p["sha256"]:
            raise SourceError(f"page {p['id']} downloaded with checksum {sha256_bytes(body)}, "
                              f"pinned {p['sha256']}; the archive served different bytes, re-pin it")
        dest.write_bytes(body)
        fetched.append(p["id"])
    return fetched


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


class _BrickLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self._in_title = "", False
        self.chunks: List[str] = []
        self.colors: List[Tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        a = dict(attrs)
        if tag == "div" and a.get("data-tab") == "All" and a.get("data-color") is not None:
            cid = int(a["data-color"])
            if cid > 0:
                self.colors.append((cid, _ws(a.get("data-name") or "")))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        text = _ws(data)
        if text:
            self.chunks.append(text)


def parse_bricklink_part(html: str) -> Dict[str, Any]:
    p = _BrickLinkParser()
    p.feed(html)
    m = re.match(r"(.+?) : Part (\S+)", _ws(p.title))
    if not m:
        raise BuildError(f"BrickLink page title not recognised: {p.title!r}")
    item_no = alternates = None
    for i, c in enumerate(p.chunks[:-1]):
        if c.endswith("Alternate Item No:") and alternates is None:
            alternates = [a.strip() for a in p.chunks[i + 1].split(",") if a.strip()]
        elif c.endswith("Item No:") and item_no is None:
            item_no = p.chunks[i + 1]
    if not item_no:
        raise BuildError("BrickLink page has no 'Item No:'")
    if item_no != m.group(2):
        raise BuildError(f"BrickLink title says part {m.group(2)} but Item No is {item_no}")
    if not p.colors:
        raise BuildError("BrickLink page has no color list")
    return {"name": m.group(1), "item_no": item_no, "alternates": alternates or [],
            "colors": p.colors}


class _RebrickableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self._in_title = "", False
        self._armed = False      # saw the "External Sites" heading
        self._table = 0          # nesting depth inside the external-sites table
        self._done = False
        self._row: Optional[List[List[str]]] = None
        self._cell: Optional[List[str]] = None
        self.rows: List[List[List[str]]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if self._done:
            return
        if tag == "table" and (self._armed or self._table):
            self._table += 1
        elif self._table and tag == "tr":
            self._row = []
        elif self._table and tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if not self._table:
            return
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._table -= 1
            if not self._table:
                self._done, self._armed = True, False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        text = _ws(data)
        if not text:
            return
        if not self._done and not self._table and text == "External Sites":
            self._armed = True
        elif self._cell is not None:
            self._cell.append(text)


def parse_rebrickable_part(html: str) -> Dict[str, Any]:
    p = _RebrickableParser()
    p.feed(html)
    m = re.match(r"LEGO PART (\S+) (.+?) \| Rebrickable", _ws(p.title))
    if not m:
        raise BuildError(f"Rebrickable page title not recognised: {p.title!r}")
    external: Dict[str, List[str]] = {}
    for row in p.rows:
        if len(row) >= 2 and row[0]:
            external[" ".join(row[0])] = [t for cell in row[1:] for t in cell]
    if not external:
        raise BuildError("Rebrickable page has no External Sites table")
    return {"part_num": m.group(1), "name": m.group(2), "external": external}


def _kit_elements(inventory: Mapping[str, Any], part: str) -> List[Mapping[str, Any]]:
    return [e for e in inventory["elements"] if e["role"] == ROLE_FOR_PART[part]]


def build(texts: Mapping[str, str], inventory: Mapping[str, Any], generated_on: str,
          pages: Sequence[Mapping[str, str]] = PAGES) -> Dict[str, Any]:
    by_part: Dict[str, Dict[str, Mapping[str, str]]] = {}
    for p in pages:
        by_part.setdefault(p["part"], {})[p["kind"]] = p
    parts: Dict[str, Any] = {}
    for part in PARTS:
        blp, rbp = by_part[part]["bricklink"], by_part[part]["rebrickable"]
        bl = parse_bricklink_part(texts[blp["id"]])
        rb = parse_rebrickable_part(texts[rbp["id"]])
        if rb["part_num"] != part:
            raise BuildError(f"{rbp['id']}: Rebrickable part number {rb['part_num']} is not {part}")
        if part != bl["item_no"] and part not in bl["alternates"]:
            raise BuildError(f"{blp['id']}: {part} is neither the BrickLink item number "
                             f"{bl['item_no']} nor an alternate ({bl['alternates']})")
        if bl["item_no"] not in rb["external"].get("BrickLink", []):
            raise BuildError(f"{rbp['id']}: Rebrickable's BrickLink cross-reference "
                             f"{rb['external'].get('BrickLink')} does not list {bl['item_no']}")
        kit = _kit_elements(inventory, part)
        if not kit or any(bl["item_no"] not in e["part_ids"] for e in kit):
            raise BuildError(f"kit inventory part_ids for {part} do not list BrickLink {bl['item_no']}")
        design_ids: List[str] = [part]
        for e in kit:
            if e.get("design_id") and e["design_id"] not in design_ids:
                design_ids.append(e["design_id"])
        lego = rb["external"].get("LEGO", [])
        for d in design_ids:
            if d not in lego:
                raise BuildError(f"{rbp['id']}: LEGO design {d} is not in Rebrickable's LEGO list {lego}")
        parts[part] = {
            "name": bl["name"],
            "lego_design_ids": design_ids,
            "bricklink": {"item_type": "P", "item_no": bl["item_no"], "alternates": bl["alternates"],
                          "colors": [name for _, name in bl["colors"]], "citation": blp["id"]},
            "rebrickable": {"part_num": rb["part_num"], "name": rb["name"], "citation": rbp["id"]},
        }
    return {
        "format_version": "1",
        "source": {
            "title": "Marketplace part numbers for the kit's map parts",
            "generator": "tools/partnumbers build",
            "generated_on": generated_on,
            "pages": [{k: p[k] for k in ("id", "title", "url", "sha256", "accessed")} for p in pages],
            "rules": [
                "Rebrickable's part number equals the project part ID.",
                "The project part ID is the BrickLink item number or one of its alternates.",
                "Rebrickable's BrickLink cross-reference lists the BrickLink item number.",
                "The BrickLink item number is one of the kit inventory's part_ids for the part.",
                "LEGO design IDs are the project part ID plus the kit inventory's design IDs for the "
                "part, each listed by Rebrickable under LEGO.",
                "BrickLink colors are the color names of the catalog page's All tab.",
            ],
            "notes": "SHA-256 of the decoded HTML of the Internet Archive raw copy. Archived copies "
                     "are used because BrickLink's site redirected to a maintenance page on "
                     "2026-11-22 and Rebrickable's terms forbid scraping its live pages.",
            "disclaimer": DISCLAIMER,
        },
        "parts": parts,
    }


def to_text(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def differences(new: Mapping[str, Any], old: Mapping[str, Any]) -> List[str]:
    """Differences ignoring the generation date."""
    def strip(d):
        d = json.loads(json.dumps(d))
        d.get("source", {}).pop("generated_on", None)
        return d
    a, b = strip(new), strip(old)
    if a == b:
        return []
    out = [f"parts.{p}: {'added' if p not in b.get('parts', {}) else 'removed' if p not in a.get('parts', {}) else 'changed'}"
           for p in sorted(set(a.get("parts", {})) | set(b.get("parts", {})))
           if a.get("parts", {}).get(p) != b.get("parts", {}).get(p)]
    if a.get("source") != b.get("source"):
        out.append("source block differs")
    return out or ["files differ"]
