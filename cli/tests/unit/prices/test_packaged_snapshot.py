"""The packaged price snapshot `data/bricklink_price_guide.json` (011 T037; SC-001).

Skipped until the owner runs `parts prices fetch` and commits the file (T051, merge gate).
"""

import pytest

from lego_image_processor.prices import PACKAGED_SNAPSHOT_PATH, load_snapshot, recipe_lots

pytestmark = pytest.mark.skipif(not PACKAGED_SNAPSHOT_PATH.is_file(),
                                reason="packaged snapshot not committed yet")


def test_packaged_snapshot_is_complete_and_covers_every_bundled_recipe():
    snap = load_snapshot()
    assert snap.packaged and snap.complete
    keys = {l.lot.key for l in snap.lots}
    missing = [l.spec for l in recipe_lots() if l.key not in keys]
    assert missing == [], f"lots of the bundled recipes not in the snapshot: {missing}"
    unpriced = [l.lot.spec for l in snap.lots if l.lot.key in {r.key for r in recipe_lots()}
                and l.figures is None]
    assert unpriced == [], f"recipe lots without a price: {unpriced}"
