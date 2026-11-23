"""Shared price wording and constants (011 T004; FR-018, contracts/estimate-format.md)."""

from lego_image_processor.kit.source import DISCLAIMER as KIT_DISCLAIMER
from lego_image_processor.prices import wording as w


def test_disclaimer_is_the_project_disclaimer():
    assert w.DISCLAIMER == KIT_DISCLAIMER == "Not affiliated with or endorsed by The LEGO Group."


def test_attribution_names_lego_bricklink_and_denies_endorsement():
    assert w.ATTRIBUTION == ("Price data: BrickLink price guide (bricklink.com). BrickLink is a "
                             "trademark of LEGO BrickLink, Inc. Not endorsed by BrickLink.")
    text = w.ATTRIBUTION.lower()
    assert "endorsed by bricklink" in text
    assert text.count("endorsed by bricklink") == text.count("not endorsed by bricklink")
    assert "bricklink corporation" not in text


def test_estimate_note():
    assert w.ESTIMATE_NOTE == ("Estimate only; excludes shipping, fees and taxes; prices vary by "
                               "seller and over time.")


def test_basis_text_covers_every_basis():
    assert set(w.BASIS_TEXT) == {"sold", "stock", "unpriced"}
    assert "sold" in w.BASIS_TEXT["sold"] and "6-month" in w.BASIS_TEXT["sold"]
    assert w.BASIS_TEXT["stock"] == "for-sale price (no sales in 6 months)"
    assert w.BASIS_TEXT["unpriced"] == "unpriced"


def test_unpriced_reasons():
    assert w.REASON_NOT_IN_SNAPSHOT == "not in the price snapshot"
    assert w.REASON_NO_DATA == "no BrickLink sales or listings"
    assert w.reason_unverified("color code mismatch") == "no verified BrickLink IDs (color code mismatch)"


def test_defaults_and_packaged_path():
    assert w.DEFAULT_STALE_DAYS == 90
    assert w.PACKAGED_SNAPSHOT_PATH.as_posix().endswith("data/bricklink_price_guide.json")
    assert w.PACKAGED_SNAPSHOT_PATH.name == "bricklink_price_guide.json"


def test_constants_are_reexported_from_the_package():
    from lego_image_processor import prices
    for name in ("ATTRIBUTION", "ESTIMATE_NOTE", "BASIS_TEXT", "DEFAULT_STALE_DAYS",
                 "PACKAGED_SNAPSHOT_PATH", "DISCLAIMER"):
        assert getattr(prices, name) == getattr(w, name)
