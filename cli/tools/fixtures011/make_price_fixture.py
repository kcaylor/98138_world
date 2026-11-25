"""Write the synthetic price snapshot fixture for the feature 011 tests (maintainer tool).

    python tools/fixtures011/make_price_fixture.py [--out tests/fixtures/prices]

Every price below is made up for tests; none is BrickLink data. The lots are the official 31203
layout's 10 lots (White plate, the kit's 9 tile colors) and the land-elevation plate colors except
Dark Brown (LEGO 308), so the tests see a missing lot. One tile lot (Medium Azur) has no sales and
is priced from stock. IDs come from the cited tables. Output is written with ``snapshot_to_json``,
so rerunning gives identical bytes.

Feature 016 (research R15) adds a second fixture, ``bricklink_price_guide_3070b.json``: the same
lots plus one 1x1 square tile lot (3070b Black, the default margin color), so a Winkel tripel
estimate can be complete; the first fixture is unchanged, so its Winkel estimates stay incomplete.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lego_image_processor import __version__
from lego_image_processor.prices.lots import PART_ORDER, lot_ref
from lego_image_processor.prices.snapshot import parse_snapshot, snapshot_to_json
from lego_image_processor.prices.wording import (ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE,
                                                 SOURCE_PUBLISHER, SOURCE_TITLE, SOURCE_URL)

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "prices"
NAME = "bricklink_price_guide.json"
NAME_3070B = "bricklink_price_guide_3070b.json"

# (part, color key, sold (qty_avg, avg, min, max, sales, pieces) or None, stock (...) or None)
LOTS = [
    ("6141", "lego_white", ("0.0385", "0.0612", "0.0100", "0.5000", 1204, 380211),
     ("0.0450", "0.0790", "0.0100", "2.0000", 3110, 2104455)),
    ("6141", "lego_brick_yellow", ("0.0420", "0.0650", "0.0150", "0.4000", 640, 120500),
     ("0.0500", "0.0800", "0.0150", "1.5000", 1500, 600000)),
    ("6141", "lego_dark_green", ("0.0610", "0.0800", "0.0200", "0.6000", 410, 51000),
     ("0.0700", "0.0950", "0.0200", "1.2000", 900, 210000)),
    ("6141", "lego_bright_green", ("0.0550", "0.0720", "0.0200", "0.5500", 380, 48200),
     ("0.0650", "0.0900", "0.0200", "1.0000", 820, 190000)),
    ("6141", "lego_bright_yellowish_green", ("0.0480", "0.0700", "0.0150", "0.5000", 350, 40100),
     ("0.0600", "0.0850", "0.0150", "1.1000", 760, 170000)),
    ("6141", "lego_sand_yellow", ("0.0890", "0.1100", "0.0300", "0.7500", 120, 9800),
     ("0.0990", "0.1300", "0.0300", "1.5000", 300, 41000)),
    ("6141", "lego_reddish_brown", ("0.0460", "0.0680", "0.0150", "0.4500", 520, 77000),
     ("0.0550", "0.0800", "0.0150", "1.3000", 1200, 400000)),
    ("6141", "lego_medium_stone_grey", ("0.0400", "0.0600", "0.0100", "0.4000", 700, 150000),
     ("0.0480", "0.0750", "0.0100", "1.6000", 1800, 800000)),
    ("6141", "lego_medium_nougat", ("0.0730", "0.0950", "0.0250", "0.6500", 260, 30500),
     ("0.0810", "0.1100", "0.0250", "1.4000", 610, 120000)),
    ("98138", "lego_bright_orange", ("0.0910", "0.1200", "0.0300", "0.8000", 300, 20400),
     ("0.1000", "0.1400", "0.0300", "1.5000", 700, 90000)),
    ("98138", "lego_bright_green", ("0.0880", "0.1150", "0.0300", "0.7000", 280, 19000),
     ("0.0970", "0.1300", "0.0300", "1.4000", 650, 85000)),
    ("98138", "lego_bright_bluish_green", ("0.0750", "0.0990", "0.0250", "0.6000", 450, 61000),
     ("0.0850", "0.1150", "0.0250", "1.2000", 980, 210000)),
    ("98138", "lego_bright_yellowish_green", ("0.0820", "0.1050", "0.0300", "0.6500", 330, 25000),
     ("0.0920", "0.1250", "0.0300", "1.3000", 720, 95000)),
    ("98138", "lego_brick_yellow", ("0.0640", "0.0850", "0.0200", "0.5500", 510, 70000),
     ("0.0720", "0.0990", "0.0200", "1.1000", 1100, 260000)),
    ("98138", "lego_earth_blue", ("0.0690", "0.0910", "0.0200", "0.6000", 812, 90412),
     ("0.0780", "0.1050", "0.0200", "1.2000", 140, 31000)),
    ("98138", "lego_flame_yellowish_orange", ("0.0950", "0.1250", "0.0350", "0.9000", 240, 15000),
     ("0.1050", "0.1450", "0.0350", "1.6000", 520, 66000)),
    ("98138", "lego_medium_azur", None,
     ("0.0870", "0.1100", "0.0300", "1.0000", 400, 52000)),
    ("98138", "lego_vibrant_coral", ("0.0712", "0.0950", "0.0250", "0.7000", 190, 12000),
     ("0.0800", "0.1100", "0.0250", "1.3000", 430, 51000)),
]
# Feature 016: the margin's default color on the 1x1 square tile (second fixture only).
LOTS_3070B = [
    ("3070b", "lego_black", ("0.0520", "0.0710", "0.0200", "0.6000", 950, 210000),
     ("0.0600", "0.0850", "0.0200", "1.5000", 2400, 1500000)),
]

STARTED, FINISHED = "2026-12-01T18:02:10Z", "2026-12-01T18:03:05Z"


def _figures(t):
    if t is None:
        return None
    keys = ("qty_avg_price", "avg_price", "min_price", "max_price", "unit_quantity", "total_quantity")
    return dict(zip(keys, t))


def snapshot_data(lot_rows=LOTS) -> dict:
    lots = []
    for i, (part, key, sold, stock) in enumerate(lot_rows):
        ref = lot_ref(part, key)
        lots.append({
            "part_id": ref.part_id, "lego_color_id": ref.lego_color_id, "color_key": ref.color_key,
            "lego_color_name": ref.lego_color_name,
            "bricklink": {"item_type": ref.bricklink_item_type, "item_no": ref.bricklink_item_no,
                          "color_id": ref.bricklink_color_id, "color_name": ref.bricklink_color_name},
            "retrieved_at": f"2026-12-01T18:02:{12 + 2 * i:02d}Z",
            "sold": _figures(sold), "stock": _figures(stock), "error": None})
    lots.sort(key=lambda l: (PART_ORDER[l["part_id"]], l["lego_color_id"]))
    return {
        "format_version": "1",
        "source": {
            "title": SOURCE_TITLE, "publisher": SOURCE_PUBLISHER, "url": SOURCE_URL,
            "api": {"base_url": "https://api.bricklink.com/api/store/v1",
                    "endpoint": "GET /items/{type}/{no}/price",
                    "documentation": [{"id": "bricklink-api-price-guide",
                                       "title": "BrickLink API: Get Price Guide",
                                       "url": "https://www.bricklink.com/v3/api.page?page=get-price-guide"}],
                    "checked": False},
            "tool": {"name": "lego-image-processor", "version": __version__,
                     "command": "tools/fixtures011/make_price_fixture.py (synthetic)"},
            "disclaimer": DISCLAIMER,
        },
        "retrieved": {"started_at": STARTED, "finished_at": FINISHED},
        "query": {"new_or_used": "N", "currency_code": "USD", "vat": "N", "country_code": None,
                  "region": None,
                  "guide_types": {"sold": "sales in the last 6 months (BrickLink's fixed period)",
                                  "stock": "items for sale at retrieval time"}},
        "statistic": {"average": "qty_avg_price", "low": "min_price", "high": "max_price",
                      "also_recorded": ["avg_price"],
                      "fallback": "stock when sold has no data; unpriced when neither has data"},
        "lot_set": {"kind": "named", "recipes": [], "count": len(lots)},
        "complete": True,
        "lots": lots,
        "attribution": ATTRIBUTION,
        "estimate_note": ESTIMATE_NOTE,
        "disclaimer": DISCLAIMER,
    }


LOTS_TEXT = ("official 31203 layout's 10 lots; land-elevation plate colors except Dark Brown "
             "(LEGO 308); Medium Azur tile priced from stock only")


def _write_one(out: Path, name: str, lot_rows, lots_text: str) -> None:
    text = snapshot_to_json(parse_snapshot(snapshot_data(lot_rows)))
    (out / name).write_bytes(text.encode("utf-8"))
    record = {
        "fixture": name,
        "synthetic": True,
        "note": "Synthetic values for tests; not BrickLink data.",
        "lots": lots_text,
        "generator": "tools/fixtures011/make_price_fixture.py",
        "disclaimer": DISCLAIMER,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    (out / name.replace(".json", ".source.json")).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _write_one(out, NAME, LOTS, LOTS_TEXT)
    _write_one(out, NAME_3070B, LOTS + LOTS_3070B,
               LOTS_TEXT + "; plus 1x1 square tile 3070b Black (feature 016, the default margin color)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    write(ap.parse_args().out)


if __name__ == "__main__":
    main()
