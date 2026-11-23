"""Price estimates for maps (feature 011): BrickLink price snapshots and offline estimates.

Estimating is offline: it reads a layout and a dated, cited price snapshot
(``data/bricklink_price_guide.json`` or a file named by the caller). Only one function uses the
network, ``fetch_snapshot`` (behind ``parts prices fetch``), with credentials from environment
variables. ``lego_image_processor.parts`` never imports this package.
Not affiliated with or endorsed by The LEGO Group.
"""

from .api_config import ApiConfig, load_api_config
from .credentials import Credentials, MissingCredentialsError, credentials_from_env
from .estimate import (Estimate, EstimateLine, EstimateReport, estimate_layout,
                       estimate_parts_lists)
from .fetch import (AuthError, DailyLimitError, FetchInterrupted, FetchResult, PriceFetchError,
                    ProgressMismatchError, fetch_snapshot, make_lot_set)
from .lots import LotRef, all_cited_lots, lot_ref, named_lots, parse_lot, recipe_lots
from .snapshot import (GuideFigures, PriceSnapshot, SnapshotError, SnapshotLot,
                       SnapshotMissingError, largest_changes, load_snapshot, parse_snapshot,
                       snapshot_to_json)
from .wording import (ATTRIBUTION, BASIS_TEXT, DEFAULT_STALE_DAYS, DISCLAIMER, ESTIMATE_NOTE,
                      PACKAGED_SNAPSHOT_PATH)

__all__ = [
    "ATTRIBUTION", "ESTIMATE_NOTE", "BASIS_TEXT", "DEFAULT_STALE_DAYS", "PACKAGED_SNAPSHOT_PATH",
    "DISCLAIMER",
    "LotRef", "lot_ref", "recipe_lots", "all_cited_lots", "parse_lot", "named_lots",
    "PriceSnapshot", "SnapshotLot", "GuideFigures", "SnapshotError", "SnapshotMissingError",
    "load_snapshot", "parse_snapshot", "snapshot_to_json", "largest_changes",
    "estimate_parts_lists", "estimate_layout", "Estimate", "EstimateLine", "EstimateReport",
    "load_api_config", "ApiConfig", "Credentials", "credentials_from_env", "MissingCredentialsError",
    "fetch_snapshot", "make_lot_set", "FetchResult", "PriceFetchError", "AuthError",
    "DailyLimitError", "FetchInterrupted", "ProgressMismatchError",
]
