"""Build ``data/plaque_parts.json``: the Black tiles and plates of the map sticker plaques (feature 017).

Small plaque: tile 6x6 (10202) on plate 6x6 (3958); large: smooth tile 8x16 (4974) on plate 8x16
(92438); Black only (specs/017-map-stickers/research.md R10, contracts/plaque-parts-file.md). The
project owner chose the smooth (polished) 4974 in place of the textured 90498 on 2026-11-24.

The tool reuses the ``partcolors`` snapshot pins and readers (Rebrickable ``elements.csv`` and
``colors.csv``, LDraw ``LDConfig.ldr``, the BrickLink color guide, Rebrickable's terms page) and
``partnumbers``' page reader and BrickLink parser, and adds four archived BrickLink catalog pages
(``PLAQUE_PAGES``, kept out of ``partnumbers.build.PAGES``). A part is written only when every rule
holds; any failure stops the build (``BuildError``, exit 5), because each plaque needs both parts:

1. ``elements.csv`` lists at least one element of the part in Rebrickable color 0 (Black); the
   element ID is the lowest whose ``design_id`` equals the part number (partcolors rule 1); all
   are kept.
2. ``colors.csv``, ``LDConfig.ldr`` and the BrickLink color guide give the Rebrickable, LEGO and
   BrickLink names and IDs of Black and its RGB (partcolors rules 2-4); they must equal the
   ``lego_black`` row of ``part_colors.json``.
3. Rebrickable ``part_num`` equals the part ID: every Black element of the part's LEGO design is
   filed under it in ``elements.csv``.
4. LEGO design IDs are the ``design_id`` values of the part's Black elements (at least one).
5. The part ID is the BrickLink item number or one of its alternates (pinned BrickLink page).
6. The pinned BrickLink page lists Black, with the BrickLink id of the color guide (11).
7. No part is in ``kit_31203_inventory.json``; BrickLink's item name says Tile or Plate as the
   slot and the plaque's dimensions; every plaque's tile and plate have the same studs.
8. Every citation id resolves to ``source.snapshots``; SHA-256s are 64 hex characters; dates are
   ``YYYY-MM-DD``.
9. Only the color key ``lego_black``; both disclaimers present.

Rules 3 and 5-9 are re-checked by the package loader (``kit/plaque_parts.py``), which the build
runs on its result. Snapshots live in the maintainer cache, never in the repository.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from lego_image_processor.kit.plaque_parts import COLOR_KEY, parse_plaque_parts
from lego_image_processor.kit.source import DISCLAIMER
from partcolors import build as _pc
from partcolors.build import (TERMS_TEXT, SnapshotError, _norm, _pick_element, _rgb, check_terms,
                              color_key, parse_bricklink, parse_elements, parse_ldconfig,
                              parse_rebrickable_colors, read_snapshots)
from partnumbers.build import BuildError, SourceError, parse_bricklink_part, read_pages

# The partcolors pins this tool reads (same files, same SHA-256), in the order they are cited.
SNAPSHOT_IDS = ("rebrickable-elements", "rebrickable-colors", "ldraw", "bricklink")
TERMS_ID = "rebrickable-terms"
SNAPSHOTS: Tuple[Dict[str, str], ...] = tuple(
    s for s in _pc.SNAPSHOTS if s["id"] in SNAPSHOT_IDS + (TERMS_ID,))

# Feature 017 (T008): Internet Archive raw copies of BrickLink's catalog pages for the four plaque
# parts, accessed 2026-11-24 (two downloads gave the same bytes). SHA-256 of the decoded HTML. Files
# are kept in the maintainer cache (<cache>/sources/partnumbers/), never in the repository. The
# 4974 page (the latest archived copy) replaced the 90498 page when the project owner chose the
# smooth 8x16 tile (2026-11-24).
ACCESSED = "2026-11-24"
PLAQUE_PAGES: Tuple[Dict[str, str], ...] = (
    {"id": "bricklink-10202", "part": "10202", "file": "bricklink-10202.html",
     "title": "BrickLink catalog item 10202, Tile 6 x 6 with Bottom Tubes (Internet Archive copy of 2025-09-03)",
     "url": "http://web.archive.org/web/20250903205604id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=10202",
     "sha256": "0b82595ed2f8e04003d4887f669ba37b02014298acce7cd26fca0dbfa257b564", "accessed": ACCESSED},
    {"id": "bricklink-3958", "part": "3958", "file": "bricklink-3958.html",
     "title": "BrickLink catalog item 3958, Plate 6 x 6 (Internet Archive copy of 2026-09-12)",
     "url": "http://web.archive.org/web/20260912195200id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=3958",
     "sha256": "5867812587171c85a589f2ba9c2304ea79f28f11ab18f5b77e919d38f35d8264", "accessed": ACCESSED},
    {"id": "bricklink-4974", "part": "4974", "file": "bricklink-4974.html",
     "title": "BrickLink catalog item 4974, Tile 8 x 16 with Bottom Tubes, Polished Surface "
              "(Internet Archive copy of 2026-04-17)",
     "url": "http://web.archive.org/web/20260417023118id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=4974",
     "sha256": "4d07fbb5d5966298013164e86be6105d25e9b20f62c66db359d396ebc250c302", "accessed": ACCESSED},
    {"id": "bricklink-92438", "part": "92438", "file": "bricklink-92438.html",
     "title": "BrickLink catalog item 92438, Plate 8 x 16 (Internet Archive copy of 2026-09-12)",
     "url": "http://web.archive.org/web/20260912194401id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=92438",
     "sha256": "7ea9bff7c80f6e0d99f3cab3ccc2fe8d26fc4d043508c81ce908bcf1fc27ddf6", "accessed": ACCESSED},
)

# The two plaque sizes (spec; research R10): studs are width x height as the sticker is read.
PLAQUES: Dict[str, Dict[str, Any]] = {
    "small": {"studs": (6, 6), "tile": "10202", "plate": "3958"},
    "large": {"studs": (16, 8), "tile": "4974", "plate": "92438"},
}
REBRICKABLE_BLACK = 0
COLOR_CITATIONS = {"lego": "ldraw", "bricklink": "bricklink", "rebrickable": "rebrickable-colors",
                   "element": "rebrickable-elements"}
RULES = (
    "Rebrickable elements.csv lists at least one element of the part in Rebrickable color 0 "
    "(Black); the element ID is the lowest whose design_id equals the part number; all are kept.",
    "Rebrickable colors.csv, LDraw LDConfig.ldr and the BrickLink color guide give the Rebrickable, "
    "LEGO and BrickLink names and IDs of Black and its RGB (partcolors join rules 2-4); they equal "
    "the lego_black row of part_colors.json.",
    "The Rebrickable part number equals the part ID (elements.csv).",
    "LEGO design IDs are the design_id values of the part's Black elements in elements.csv.",
    "The part ID is the BrickLink item number or one of its alternates (pinned BrickLink page).",
    "The pinned BrickLink page lists Black (BrickLink id 11) among the item's colors.",
    "No part is in kit_31203_inventory.json; BrickLink's item name gives the slot (Tile or Plate) "
    "and the plaque's dimensions; every plaque's tile and plate have the same studs.",
    "Every citation id resolves to source.snapshots; SHA-256s are 64 hex characters; dates are "
    "YYYY-MM-DD.",
    "Only the color key lego_black; both disclaimers present.",
)
_NAME_RE = re.compile(r"^(Tile|Plate) (\d+) x (\d+)\b")


def _fail(rule: int, part: Optional[str], text: str) -> BuildError:
    return BuildError(f"rule {rule}: " + (f"part {part}: " if part else "") + text)


def read_sources(snapshot_dir: Path) -> Tuple[Dict[str, bytes], Dict[str, str]]:
    """The pinned snapshots (``snapshot_dir``, by default ``<cache>/sources/partcolors``) and the
    BrickLink pages (its sibling ``partnumbers/``), checked against their SHA-256."""
    snap = read_snapshots(Path(snapshot_dir), SNAPSHOTS)
    try:
        pages = read_pages(Path(snapshot_dir) / ".." / "partnumbers", PLAQUE_PAGES)
    except SourceError as exc:
        raise SnapshotError(str(exc)) from exc
    return snap, pages


def black_row(part_colors: Mapping[str, Any]) -> Dict[str, Any]:
    """The ``lego_black`` row of ``part_colors.json`` (rule 2 compares with it)."""
    for rows in part_colors["parts"].values():
        for r in rows:
            if r["key"] == COLOR_KEY:
                return dict(r)
    raise BuildError("rule 2: part_colors.json has no lego_black row")


def _black(snap: Mapping[str, bytes], black: Mapping[str, Any]) -> Dict[str, Any]:
    """Rules 2 and 9: Black from the snapshots, equal to part_colors.json's ``lego_black``."""
    rb = parse_rebrickable_colors(snap["rebrickable-colors"].decode("utf-8")).get(REBRICKABLE_BLACK)
    ld = parse_ldconfig(snap["ldraw"].decode("utf-8", "replace")).get(REBRICKABLE_BLACK)
    bl = parse_bricklink(snap["bricklink"].decode("latin-1"))
    if rb is None or rb["trans"]:
        raise _fail(2, None, f"colors.csv has no opaque color {REBRICKABLE_BLACK}")
    if ld is None or _norm(ld["name"]) != _norm(rb["name"]) or ld["lego"] is None:
        raise _fail(2, None, f"LDraw code {REBRICKABLE_BLACK} is {ld['name'] if ld else 'absent'!r} "
                             f"with no verified LEGO id for {rb['name']!r}")
    if rb["name"] not in bl:
        raise _fail(2, None, f"BrickLink color guide has no color named {rb['name']!r}")
    lego_id, lego_name = ld["lego"]
    key = color_key(lego_name)
    if key != COLOR_KEY:
        raise _fail(9, None, f"LEGO color {lego_id} is {lego_name!r} (key {key}); only {COLOR_KEY} is allowed")
    color = {"key": key,
             "lego": {"name": lego_name, "id": lego_id},
             "bricklink": {"name": rb["name"], "id": bl[rb["name"]]},
             "rebrickable": {"name": rb["name"], "id": REBRICKABLE_BLACK},
             "rgb": _rgb(rb["rgb"])}
    for f in ("lego", "bricklink", "rebrickable", "rgb"):
        if color[f] != black.get(f):
            raise _fail(2, None, f"{f} of Black from the snapshots is {color[f]}, part_colors.json "
                                 f"lego_black has {black.get(f)}")
    return color


def _misfiled(elements_text: str, part: str) -> List[Tuple[str, str]]:
    """Black elements of LEGO design ``part`` that Rebrickable files under another part number."""
    return [(r["element_id"], r["part_num"]) for r in csv.DictReader(io.StringIO(elements_text))
            if r.get("design_id") == part and r["part_num"] != part
            and int(r["color_id"]) == REBRICKABLE_BLACK]


def _kit_ids(inventory: Mapping[str, Any]) -> Tuple[set, set]:
    els = inventory["elements"]
    parts = {p for e in els for p in e.get("part_ids") or ()} | {e["design_id"] for e in els if e.get("design_id")}
    return parts, {e["element_id"] for e in els}


def _part(part: str, kind: str, studs: Tuple[int, int], page: Mapping[str, str], html: str,
          elements: Mapping[Tuple[str, int], List[Tuple[str, str]]], elements_text: str,
          color: Mapping[str, Any], kit: Tuple[set, set]) -> Dict[str, Any]:
    # rule 1
    els = elements.get((part, REBRICKABLE_BLACK))
    if not els:
        raise _fail(1, part, f"elements.csv lists no element of part {part} in Rebrickable color "
                             f"{REBRICKABLE_BLACK}")
    element_id, element_ids = _pick_element(els, part)
    # rule 3
    misfiled = _misfiled(elements_text, part)
    if misfiled:
        raise _fail(3, part, "elements.csv files Black elements of LEGO design "
                             f"{part} under other Rebrickable part numbers: {misfiled}")
    # rule 4
    designs = sorted({d for _, d in els if d}, key=lambda d: (d != part, d))
    if not designs:
        raise _fail(4, part, "no Black element of the part has a design_id in elements.csv")
    # rules 5 and 6
    bl = parse_bricklink_part(html)
    if part != bl["item_no"] and part not in bl["alternates"]:
        raise _fail(5, part, f"{page['id']}: {part} is neither the BrickLink item number "
                             f"{bl['item_no']} nor an alternate ({bl['alternates']})")
    listed = dict((name, cid) for cid, name in bl["colors"])
    if listed.get(color["bricklink"]["name"]) != color["bricklink"]["id"]:
        raise _fail(6, part, f"{page['id']} does not list {color['bricklink']['name']} "
                             f"(BrickLink id {color['bricklink']['id']})")
    # rule 7
    kit_parts, kit_elements = kit
    in_kit = sorted(({part, bl["item_no"], *designs} & kit_parts) | (set(element_ids) & kit_elements))
    if in_kit:
        raise _fail(7, part, f"{in_kit} is in the kit 31203 inventory")
    m = _NAME_RE.match(bl["name"])
    if not m or m.group(1).lower() != kind or sorted((int(m.group(2)), int(m.group(3)))) != sorted(studs):
        raise _fail(7, part, f"BrickLink names it {bl['name']!r}; the plaque needs a {kind} "
                             f"{studs[0]} x {studs[1]}")
    return {
        "kind": kind, "studs": list(studs), "name": bl["name"],
        "lego_design_ids": designs,
        "bricklink": {"item_type": "P", "item_no": bl["item_no"], "alternates": bl["alternates"],
                      "colors": [name for _, name in bl["colors"]], "citation": page["id"]},
        "rebrickable": {"part_num": part, "citation": "rebrickable-elements"},
        "color": {"key": color["key"], "element_id": element_id, "element_ids": element_ids,
                  "lego": dict(color["lego"]), "bricklink": dict(color["bricklink"]),
                  "rebrickable": dict(color["rebrickable"]), "rgb": list(color["rgb"]),
                  "citations": dict(COLOR_CITATIONS)},
    }


def build(snap: Mapping[str, bytes], pages: Mapping[str, str], inventory: Mapping[str, Any],
          black: Mapping[str, Any], generated_on: str,
          snapshots: Optional[Sequence[Mapping[str, str]]] = None,
          plaque_pages: Optional[Sequence[Mapping[str, str]]] = None) -> Dict[str, Any]:
    """Join the snapshots into the plaque part table (rules 1-9)."""
    snapshots = SNAPSHOTS if snapshots is None else snapshots
    plaque_pages = PLAQUE_PAGES if plaque_pages is None else plaque_pages
    check_terms(snap[TERMS_ID].decode("utf-8", "replace"))
    color = _black(snap, black)
    elements_text = snap["rebrickable-elements"].decode("utf-8")
    all_parts = [spec[k] for spec in PLAQUES.values() for k in ("tile", "plate")]
    elements = parse_elements(elements_text, all_parts)
    page_for = {p["part"]: p for p in plaque_pages}
    kit = _kit_ids(inventory)
    parts: Dict[str, Any] = {}
    for spec in PLAQUES.values():
        for kind in ("tile", "plate"):
            part = spec[kind]
            page = page_for[part]
            parts[part] = _part(part, kind, spec["studs"], page, pages[page["id"]], elements,
                                elements_text, color, kit)
    by_id = {s["id"]: s for s in snapshots}
    terms = by_id[TERMS_ID]
    data = {
        "format_version": "1",
        "source": {
            "title": "Black tiles and plates for map sticker plaques",
            "generator": "tools/partcolors plaque-parts",
            "generated_on": generated_on,
            "snapshots": [{k: s[k] for k in ("id", "title", "url", "sha256", "accessed")}
                          for s in [by_id[i] for i in SNAPSHOT_IDS] + list(plaque_pages)],
            "rules": list(RULES),
            "terms": {"text": TERMS_TEXT, "url": terms["url"], "sha256": terms["sha256"],
                      "accessed": terms["accessed"]},
            "disclaimer": DISCLAIMER,
        },
        "plaques": {size: {"studs": list(spec["studs"]), "tile": spec["tile"], "plate": spec["plate"]}
                    for size, spec in PLAQUES.items()},
        "parts": parts,
        "disclaimer": DISCLAIMER,
    }
    try:  # rules 3 and 5-9 again, with the package's own loader
        parse_plaque_parts(data)
    except ValueError as exc:
        raise BuildError(str(exc)) from exc
    return data


def summary(data: Mapping[str, Any]) -> List[str]:
    """One line per plaque part for the command's output."""
    out = []
    for size, pl in data["plaques"].items():
        for kind in ("tile", "plate"):
            pid = pl[kind]
            p = data["parts"][pid]
            c, bl = p["color"], p["bricklink"]
            out.append(f"{size} plaque {kind} {pid} ({p['name']}): {c['lego']['name']} element "
                       f"{c['element_id']}; BrickLink {bl['item_type']} {bl['item_no']} "
                       f"{c['bricklink']['name']} ({c['bricklink']['id']}); Rebrickable "
                       f"{p['rebrickable']['part_num']} {c['rebrickable']['name']} "
                       f"({c['rebrickable']['id']}); LEGO design {', '.join(p['lego_design_ids'])} "
                       f"{c['lego']['name']} ({c['lego']['id']})")
    return out


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
    out = []
    for block in ("plaques", "parts"):
        ka, kb = a.get(block) or {}, b.get(block) or {}
        for k in sorted(set(ka) | set(kb)):
            if ka.get(k) != kb.get(k):
                out.append(f"{block}.{k}: {'added' if k not in kb else 'removed' if k not in ka else 'changed'}")
    for k in ("format_version", "source", "disclaimer"):
        if a.get(k) != b.get(k):
            out.append(f"{k} differs")
    return out or ["files differ"]
