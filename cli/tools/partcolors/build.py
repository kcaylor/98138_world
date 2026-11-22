"""Join pinned Rebrickable, LDraw and BrickLink snapshots into the cited part-color table.

Join rules (a row is kept only when every rule holds; otherwise it is excluded and reported):

1. Rebrickable ``elements.csv`` lists at least one element of the part in the color
   (Rebrickable color id). The element ID is the lowest numeric element whose ``design_id`` equals
   the part number (else the lowest listed); all listed elements are kept in ``element_ids``.
2. Rebrickable ``colors.csv`` gives the Rebrickable name, id and RGB; transparent colors are
   excluded.
3. LDraw ``LDConfig.ldr`` gives the LEGO name and id: the LDraw ``CODE`` equals the Rebrickable
   color id and the LDraw name equals the Rebrickable name (case-insensitive, ``_`` as space,
   "grey" as "gray"), and a ``LEGOID`` comment precedes the color.
4. The BrickLink color guide lists a color whose name equals the Rebrickable name exactly; its
   BrickLink id is used.
5. The color is listed, with the same BrickLink id, on BrickLink's pinned catalog page for the part
   (item 4073 for the plate, 98138 for the tile; feature 005).

Every color Rebrickable lists for the part is tried (feature 005, Q3); rows that fail a rule are
excluded and reported. Rebrickable's terms (archived downloads page) are recorded in
``source.terms`` after checking that the quoted text is on the pinned page.

Kit colors are copied from ``kit_colors.json`` (the authority for them); the tool reports any
disagreement between that table and the snapshots but does not change it.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from lego_image_processor.kit.source import DISCLAIMER
from partnumbers.build import parse_bricklink_part

# Pinned snapshots (fetched 2026-11-22 except where noted). Files are kept in the maintainer cache
# (<cache>/sources/partcolors/), never in the repository.
SNAPSHOTS: Tuple[Dict[str, str], ...] = (
    {"id": "rebrickable-elements", "file": "elements.csv.gz",
     "title": "Rebrickable elements.csv (catalog download)",
     "url": "https://cdn.rebrickable.com/media/downloads/elements.csv.gz",
     "sha256": "dfc8641d58591c8188fe156a43831a7d774b48e61570d03e79940fefb812cbfc",
     "accessed": "2026-11-22"},
    {"id": "rebrickable-colors", "file": "colors.csv.gz",
     "title": "Rebrickable colors.csv (catalog download)",
     "url": "https://cdn.rebrickable.com/media/downloads/colors.csv.gz",
     "sha256": "ca59b7368c4ee4abf157c723689957de250e1485d036a2ae8b2b235102c8fe28",
     "accessed": "2026-11-22"},
    {"id": "ldraw", "file": "LDConfig.ldr",
     "title": "LDraw LDConfig.ldr (update 2026-11-09)",
     "url": "https://library.ldraw.org/library/official/LDConfig.ldr",
     "sha256": "fb7c02d8f4fbb49ff6f4f5c85c70ca60b945e80365ca8bd12bea6b70d6d2f96b",
     "accessed": "2026-11-21"},
    {"id": "bricklink", "file": "catalogColors.html",
     "title": "BrickLink Color Guide (archived 2025-10-02)",
     "url": "http://web.archive.org/web/20251002182704/https://www.bricklink.com/catalogColors.asp",
     "sha256": "93b28f3a1f6bb668c9f4102edaf3b2e6f500cf90084b087ead3af02c32e9ecda",
     "accessed": "2026-11-21"},
    # Feature 005: BrickLink part pages (rule 5) and Rebrickable's terms, shared with the
    # partnumbers tool's cache (<cache>/sources/partnumbers/).
    {"id": "bricklink-4073", "file": "../partnumbers/bricklink-4073.html",
     "title": "BrickLink catalog item 4073, Plate, Round 1 x 1 (Internet Archive copy of 2026-11-04)",
     "url": "http://web.archive.org/web/20261104074336id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=4073",
     "sha256": "957f23bd90a68006f3cbf7f1f4461a6d5de89f2b9b6ed67b5b14533db0b2c146",
     "accessed": "2026-11-22"},
    {"id": "bricklink-98138", "file": "../partnumbers/bricklink-98138.html",
     "title": "BrickLink catalog item 98138, Tile, Round 1 x 1 (Internet Archive copy of 2026-09-01)",
     "url": "http://web.archive.org/web/20260901170641id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=98138",
     "sha256": "d1683255e9ecb05ade31884614beb278526aed13efb5725cbc53f74f9e7ffeb0",
     "accessed": "2026-11-22"},
    {"id": "rebrickable-terms", "file": "../partnumbers/rebrickable-downloads.html",
     "title": "Rebrickable downloads page with the catalog terms (Internet Archive copy of 2026-10-29)",
     "url": "http://web.archive.org/web/20261029125803id_/https://rebrickable.com/downloads/",
     "sha256": "1c514a79f8cb70a0faacccf7174ee4329a307a6d91221b8c318b6982a7b91b75",
     "accessed": "2026-11-22"},
)
BRICKLINK_PART_PAGE = {"6141": "bricklink-4073", "98138": "bricklink-98138"}
TERMS_TEXT = ("Free for personal and commercial use, provided you acknowledge Rebrickable as your "
              "data source.")
ACKNOWLEDGEMENT = "Catalog data: Rebrickable (rebrickable.com)."

PARTS = ("6141", "98138")
# Feature 004 used a hand-reviewed list of Rebrickable color ids (research R9 of 004). Feature 005
# (Q3) tries every color listed for the part; ``reviewed`` remains for tests and comparisons.
REVIEWED_004: Dict[str, Tuple[int, ...]] = {
    "6141": (0, 2, 10, 27, 378, 326, 19, 28, 92, 84, 70, 308, 71, 72),
    "98138": (),
}
PART_NUMBERS = {
    "6141": "Rebrickable elements.csv files element 614101 (and every other 1x1 round plate "
            "element) under part_num 6141 with design_id 6141; it lists no elements under 4073. "
            "BrickLink files the part as item 4073 with 6141 as an alternate number (pinned "
            "BrickLink catalog page bricklink-4073). Marketplace numbers: part_numbers.json.",
    "98138": "Rebrickable elements.csv files the 1x1 round tile under part_num 98138 (design_id "
             "35381 for newer elements); BrickLink item 98138 (pinned page bricklink-98138). "
             "Marketplace numbers: part_numbers.json.",
}


JOIN_RULES = (
    "Rebrickable elements.csv lists an element of the part in the color; the element ID is the "
    "lowest numeric element whose design_id equals the part number (else the lowest listed).",
    "Rebrickable colors.csv gives the Rebrickable name, id and RGB; transparent colors are excluded.",
    "LDraw LDConfig.ldr gives the LEGO name and id: the LDraw CODE equals the Rebrickable id, the "
    "names agree (case-insensitive, '_' as space, grey as gray) and a LEGOID comment precedes it.",
    "The BrickLink color guide lists a color with exactly the Rebrickable name; its id is used.",
    "BrickLink's pinned catalog page for the part (4073 plate, 98138 tile) lists the color with the "
    "same BrickLink id.",
    "Kit colors are copied from kit_colors.json, the authority for them.",
)


class SnapshotError(Exception):
    exit_code = 4


@dataclass
class BuildResult:
    data: Dict[str, Any]
    excluded: List[Dict[str, Any]]
    kit_notes: List[str]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_snapshots(snapshot_dir: Path, snapshots: Sequence[Mapping[str, str]] = SNAPSHOTS,
                   check_sha: bool = True) -> Dict[str, bytes]:
    out = {}
    for s in snapshots:
        p = Path(snapshot_dir) / s["file"]
        if not p.is_file():
            raise SnapshotError(f"snapshot {s['id']} missing: {p} (download {s['url']})")
        b = p.read_bytes()
        if check_sha and sha256_bytes(b) != s["sha256"]:
            raise SnapshotError(f"snapshot {s['id']} checksum mismatch: expected {s['sha256']}, "
                                f"actual {sha256_bytes(b)} ({p})")
        out[s["id"]] = gzip.decompress(b) if s["file"].endswith(".gz") else b
    return out


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("_", " ")).strip().lower().replace("grey", "gray")


def parse_rebrickable_colors(text: str) -> Dict[int, Dict[str, Any]]:
    return {int(r["id"]): {"name": r["name"], "rgb": r["rgb"], "trans": r["is_trans"] == "True"}
            for r in csv.DictReader(io.StringIO(text))}


def parse_elements(text: str, parts: Sequence[str]) -> Dict[Tuple[str, int], List[Tuple[str, str]]]:
    out: Dict[Tuple[str, int], List[Tuple[str, str]]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        if r["part_num"] in parts:
            out.setdefault((r["part_num"], int(r["color_id"])), []).append(
                (r["element_id"], r.get("design_id") or ""))
    return out


def parse_ldconfig(text: str) -> Dict[int, Dict[str, Any]]:
    out, last = {}, None
    for line in text.splitlines():
        m = re.search(r"LEGOID\s+(\d+)(?:\s*/\s*\d+)*\s*-\s*(.+?)\s*$", line)
        if m:
            last = (int(m.group(1)), m.group(2).strip())
            continue
        m = re.search(r"!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})", line)
        if m:
            out[int(m.group(2))] = {"name": m.group(1).replace("_", " "), "lego": last}
            last = None
    return out


def parse_bricklink(html: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    pat = (r'<TD\s+ALIGN="RIGHT"><FONT FACE="Tahoma,Arial" SIZE="2">(\d+)&nbsp;</TD>'
           r'<TD BGCOLOR="[0-9A-Fa-f]*">.*?<TD width="180px"><FONT FACE="Tahoma,Arial" SIZE="2">'
           r'([^<&]+)&nbsp;')
    for m in re.finditer(pat, html, re.S):
        out.setdefault(m.group(2).strip(), int(m.group(1)))
    return out


def color_key(lego_name: str) -> str:
    return "lego_" + re.sub(r"[^a-z0-9]+", "_", lego_name.lower()).strip("_")


def _rgb(hexstr: str) -> List[int]:
    return [int(hexstr[i:i + 2], 16) for i in (0, 2, 4)]


def _pick_element(els: List[Tuple[str, str]], part: str) -> Tuple[str, List[str]]:
    ids = sorted({e for e, _ in els}, key=int)
    preferred = sorted({e for e, d in els if d == part}, key=int)
    return (preferred or ids)[0], ids


def check_terms(html: str, text: str = TERMS_TEXT) -> None:
    if text not in re.sub(r"\s+", " ", html):
        raise SnapshotError(f"Rebrickable terms text not found on the pinned page: {text!r}")


def build(snap: Mapping[str, bytes], kit_colors: Mapping[str, Any], generated_on: str,
          reviewed: Optional[Mapping[str, Sequence[int]]] = None,
          snapshots: Sequence[Mapping[str, str]] = SNAPSHOTS) -> BuildResult:
    """Join the snapshots. ``reviewed`` limits the colors tried per part (default: every color
    Rebrickable lists for the part)."""
    rb = parse_rebrickable_colors(snap["rebrickable-colors"].decode("utf-8"))
    elements = parse_elements(snap["rebrickable-elements"].decode("utf-8"), list(PARTS))
    if reviewed is None:
        reviewed = {p: tuple(sorted({c for (q, c) in elements if q == p})) for p in PARTS}
    ld = parse_ldconfig(snap["ldraw"].decode("utf-8", "replace"))
    bl = parse_bricklink(snap["bricklink"].decode("latin-1"))
    part_page = {p: dict((n, i) for i, n in parse_bricklink_part(
        snap[BRICKLINK_PART_PAGE[p]].decode("utf-8", "replace"))["colors"]) for p in PARTS}
    terms_page = next(s for s in snapshots if s["id"] == "rebrickable-terms")
    check_terms(snap["rebrickable-terms"].decode("utf-8", "replace"))
    kit_src = kit_colors["source"]
    citations = [dict(c) for c in kit_src["citations"]]
    known = {c["id"] for c in citations}
    for s in snapshots:
        cid = s["id"]
        if cid == "rebrickable-terms":
            continue
        if cid == "rebrickable-colors":
            cid = "rebrickable-colors-snapshot"
        if cid not in known:
            citations.append({"id": cid, "title": s["title"], "url": s["url"], "accessed": s["accessed"]})
            known.add(cid)
    role_for = {"6141": "land", "98138": "ocean"}
    parts: Dict[str, List[Dict[str, Any]]] = {}
    excluded: List[Dict[str, Any]] = []
    kit_notes: List[str] = []
    for part, rb_ids in reviewed.items():
        rows: List[Dict[str, Any]] = []
        kit_rows = [c for c in kit_colors["colors"] if c["role"] == role_for[part]]
        kit_rb = {c["rebrickable"]["id"] for c in kit_rows}
        for c in kit_rows:
            row = {k: c[k] for k in ("key", "element_id", "lego", "bricklink", "rebrickable", "rgb", "citations")}
            listed = sorted({e for e, _ in elements.get((part, c["rebrickable"]["id"]), [])}, key=int)
            row["element_ids"] = [c["element_id"]] + [e for e in listed if e != c["element_id"]]
            row["in_kit"] = True
            row["notes"] = "Kit color; values from kit_colors.json."
            rows.append(row)
            r = rb.get(c["rebrickable"]["id"])
            if r is None or r["name"] != c["rebrickable"]["name"] or _rgb(r["rgb"]) != c["rgb"]:
                kit_notes.append(f"{part} {c['key']}: Rebrickable snapshot differs from kit_colors.json")
            if c["element_id"] not in listed:
                kit_notes.append(f"{part} {c['key']}: kit element {c['element_id']} is not listed in "
                                 f"Rebrickable elements.csv for part {part} (listed: {listed or 'none'})")
            if part_page[part].get(c["bricklink"]["name"]) != c["bricklink"]["id"]:
                kit_notes.append(f"{part} {c['key']}: BrickLink {c['bricklink']['name']} "
                                 f"({c['bricklink']['id']}) is not on BrickLink's part page")
        extra: List[Dict[str, Any]] = []
        for cid in sorted(rb_ids):
            if cid in kit_rb:
                continue
            why = None
            r = rb.get(cid)
            els = elements.get((part, cid))
            l = ld.get(cid)
            if not els:
                why = "no element of this part in elements.csv"
            elif r is None:
                why = "color id not in colors.csv"
            elif r["trans"]:
                why = "transparent"
            elif l is None or _norm(l["name"]) != _norm(r["name"]):
                why = (f"LDraw code {cid} is {l['name'] if l else 'absent'!r}, not {r['name']!r}: "
                       "no verified LEGO id")
            elif l["lego"] is None:
                why = "LDraw entry has no LEGOID"
            elif r["name"] not in bl:
                why = f"BrickLink color guide has no color named {r['name']!r}"
            elif part_page[part].get(r["name"]) != bl[r["name"]]:
                why = (f"BrickLink's catalog page for part {part} does not list {r['name']!r} "
                       f"(id {bl[r['name']]})")
            elif any(x["key"] == color_key(l["lego"][1]) for x in rows + extra):
                why = f"LEGO color key {color_key(l['lego'][1])} is already taken by another row"
            if why:
                excluded.append({"part": part, "rebrickable_id": cid,
                                 "name": r["name"] if r else None, "reason": why})
                continue
            lego_id, lego_name = l["lego"]
            element_id, ids = _pick_element(els, part)
            extra.append({
                "key": color_key(lego_name), "element_id": element_id,
                "lego": {"name": lego_name, "id": lego_id},
                "bricklink": {"name": r["name"], "id": bl[r["name"]]},
                "rebrickable": {"name": r["name"], "id": cid},
                "rgb": _rgb(r["rgb"]),
                "citations": {"lego": "ldraw", "bricklink": "bricklink",
                              "rebrickable": "rebrickable-colors-snapshot",
                              "element": "rebrickable-elements"},
                "element_ids": ids, "in_kit": False, "notes": "",
            })
        parts[part] = rows + extra
    data = {
        "format_version": "1",
        "source": {
            "title": "Colors in which the kit's map parts (6141 plate, 98138 tile) are made",
            "generator": "tools/partcolors build",
            "generated_on": generated_on,
            "snapshots": [{k: s[k] for k in ("id", "title", "url", "sha256", "accessed")} for s in snapshots],
            "citations": citations,
            "join_rules": list(JOIN_RULES),
            "part_numbers": dict(PART_NUMBERS),
            "terms": {"text": TERMS_TEXT, "url": terms_page["url"], "sha256": terms_page["sha256"],
                      "accessed": terms_page["accessed"]},
            "acknowledgement": ACKNOWLEDGEMENT,
            "excluded": excluded,
            "disclaimer": DISCLAIMER,
        },
        "parts": parts,
    }
    return BuildResult(data=data, excluded=excluded, kit_notes=kit_notes)


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
    for part in sorted(set(a.get("parts", {})) | set(b.get("parts", {}))):
        ka = {r["key"]: r for r in a.get("parts", {}).get(part, [])}
        kb = {r["key"]: r for r in b.get("parts", {}).get(part, [])}
        for k in sorted(set(ka) | set(kb)):
            if ka.get(k) != kb.get(k):
                out.append(f"parts.{part}.{k}: {'added' if k not in kb else 'removed' if k not in ka else 'changed'}")
    if a.get("source") != b.get("source"):
        out.append("source block differs")
    return out or ["files differ"]
