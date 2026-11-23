"""Fixed wording and constants for price snapshots and estimates (feature 011, FR-018).

Kept apart from ``snapshot`` and ``estimate`` so both import it without a cycle. The attribution
credits BrickLink as the price source without implying that BrickLink or The LEGO Group endorses
this project.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from ..kit.colors import DATA_DIR
from ..kit.source import DISCLAIMER

ATTRIBUTION = ("Price data: BrickLink price guide (bricklink.com). BrickLink is a trademark of "
               "LEGO BrickLink, Inc. Not endorsed by BrickLink.")
ESTIMATE_NOTE = ("Estimate only; excludes shipping, fees and taxes; prices vary by seller and over "
                 "time.")
SOURCE_TITLE = "BrickLink price guide (BrickLink API)"
SOURCE_PUBLISHER = "LEGO BrickLink, Inc."
SOURCE_URL = "https://www.bricklink.com"

# How a lot was priced (FR-013).
BASIS_TEXT = {
    "sold": "6-month average of new parts sold (quantity-weighted)",
    "stock": "for-sale price (no sales in 6 months)",
    "unpriced": "unpriced",
}
# What the whole estimate is based on (one sentence; the web page and the prices block).
BASIS_SENTENCE = ("Average price of new parts sold on BrickLink in the last 6 months "
                  "(quantity-weighted), US dollars; range from the lowest to the highest sale. Lots "
                  "with no sales use the current for-sale average.")
# The table's "Prices:" line.
STATISTIC_TEXT = ("6-month average of new parts sold, USD, quantity-weighted; range from lowest to "
                  "highest sale")

# Why a lot is unpriced (research R13).
REASON_NOT_IN_SNAPSHOT = "not in the price snapshot"
REASON_NO_DATA = "no BrickLink sales or listings"


def reason_unverified(parts_reason: str) -> str:
    """An unverified 005 lot has no BrickLink IDs to price it by."""
    return f"no verified BrickLink IDs ({parts_reason})"


ALL_COLORS_HINT = "lego-image-processor parts prices fetch --all-colors"
MISSING_SNAPSHOT_MESSAGE = ("no price snapshot is packaged yet; pass --prices FILE or run "
                            "`lego-image-processor parts prices fetch`")

LABELS = {"full": "Every piece", "one_kit": "On top of one 31203 kit"}
SHORT_LABELS = {"full": "Every piece", "one_kit": "On top of one kit"}
NOTHING_TO_BUY_TEXT = "One kit covers every piece"

DEFAULT_STALE_DAYS = 90
PACKAGED_SNAPSHOT_PATH = DATA_DIR / "bricklink_price_guide.json"

__all__ = [
    "ATTRIBUTION", "ESTIMATE_NOTE", "DISCLAIMER", "SOURCE_TITLE", "SOURCE_PUBLISHER", "SOURCE_URL",
    "BASIS_TEXT", "BASIS_SENTENCE", "STATISTIC_TEXT", "REASON_NOT_IN_SNAPSHOT", "REASON_NO_DATA",
    "reason_unverified", "ALL_COLORS_HINT", "MISSING_SNAPSHOT_MESSAGE", "LABELS", "SHORT_LABELS",
    "NOTHING_TO_BUY_TEXT", "DEFAULT_STALE_DAYS", "PACKAGED_SNAPSHOT_PATH",
]
