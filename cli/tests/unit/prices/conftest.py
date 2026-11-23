"""Helpers for the prices tests (011 T008): snapshot dicts with real cited IDs, synthetic prices.

Values are synthetic; they are not BrickLink data.
"""

import copy
import json
from pathlib import Path

import pytest

from lego_image_processor.prices.lots import lot_ref
from lego_image_processor.prices.wording import ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "prices"
FIXTURE_SNAPSHOT = FIXTURE_DIR / "bricklink_price_guide.json"

STARTED, FINISHED = "2026-12-01T18:02:10Z", "2026-12-01T18:03:05Z"


def figures(avg="0.0400", min_="0.0100", max_="0.5000", plain=None, units=100, total=10000):
    return {"qty_avg_price": avg, "avg_price": plain or avg, "min_price": min_, "max_price": max_,
            "unit_quantity": units, "total_quantity": total}


def lot_entry(part_id, color_key, sold="default", stock="default", error=None,
              retrieved_at="2026-12-01T18:02:30Z"):
    ref = lot_ref(part_id, color_key)
    return {
        "part_id": ref.part_id, "lego_color_id": ref.lego_color_id, "color_key": ref.color_key,
        "lego_color_name": ref.lego_color_name,
        "bricklink": {"item_type": ref.bricklink_item_type, "item_no": ref.bricklink_item_no,
                      "color_id": ref.bricklink_color_id, "color_name": ref.bricklink_color_name},
        "retrieved_at": retrieved_at,
        "sold": figures() if sold == "default" else sold,
        "stock": figures("0.0500", "0.0100", "2.0000", units=300, total=50000) if stock == "default" else stock,
        "error": error,
    }


def snapshot_dict(lots=None, complete=True, count=None, kind="named"):
    if lots is None:
        lots = [lot_entry("6141", "lego_white"), lot_entry("98138", "lego_earth_blue")]
    return {
        "format_version": "1",
        "source": {
            "title": "BrickLink price guide (BrickLink API)",
            "publisher": "LEGO BrickLink, Inc.",
            "url": "https://www.bricklink.com",
            "api": {"base_url": "https://api.bricklink.com/api/store/v1",
                    "endpoint": "GET /items/{type}/{no}/price",
                    "documentation": [{"id": "bricklink-api-price-guide",
                                       "title": "BrickLink API: Get Price Guide",
                                       "url": "https://www.bricklink.com/v3/api.page?page=get-price-guide"}],
                    "checked": False},
            "tool": {"name": "lego-image-processor", "version": "0.1.0", "command": "parts prices fetch"},
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
        "lot_set": {"kind": kind, "recipes": [], "count": len(lots) if count is None else count},
        "complete": complete,
        "lots": lots,
        "attribution": ATTRIBUTION,
        "estimate_note": ESTIMATE_NOTE,
        "disclaimer": DISCLAIMER,
    }


@pytest.fixture
def snap_dict():
    return snapshot_dict()


@pytest.fixture
def write_snapshot(tmp_path):
    def _write(data, name="snap.json", raw=None):
        p = tmp_path / name
        if raw is not None:
            p.write_bytes(raw)
        else:
            p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return p
    return _write


def deep(d):
    return copy.deepcopy(d)
