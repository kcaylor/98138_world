"""Human estimate table (011 T015; contracts/cli.md `parts estimate`, FR-018)."""

from datetime import date

from lego_image_processor.kit import load_official_design
from lego_image_processor.prices.estimate import estimate_layout
from lego_image_processor.prices.snapshot import load_snapshot, parse_snapshot
from lego_image_processor.prices.text import echo_estimate
from lego_image_processor.prices.wording import ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE

from ..parts.layouts import LAND_ELEVATION, SMALL, make_grid
from .conftest import FIXTURE_SNAPSHOT, figures, lot_entry, snapshot_dict


def _lines(report, **kw):
    out = []
    echo_estimate(report, echo=lambda s="": out.append(s), **kw)
    return out


def _official(as_of=date(2026, 12, 5)):
    return estimate_layout(load_official_design().to_layout(), load_snapshot(FIXTURE_SNAPSHOT),
                           as_of=as_of, layout_path="official.json")


def test_header_prices_line_table_and_trailer():
    r = _official()
    out = _lines(r)
    text = "\n".join(out)
    assert out[0].startswith("Price estimate for official.json (")
    assert "10,240 positions; map pieces only)" in out[0]
    prices = next(l for l in out if l.startswith("Prices: "))
    assert "BrickLink price guide, retrieved 2026-12-01" in prices
    assert "quantity-weighted" in prices
    assert f"(SHA-256 {r.snapshot['sha256'][:8]}" in text and "complete." in text
    header = next(l for l in out if l.strip().startswith("average"))
    assert "pieces" in header and "lots" in header and "unpriced" in header
    every = next(l for l in out if l.startswith("Every piece"))
    t = r.estimates["full"].totals
    assert f"${t['average']:,.2f}" in every and f"${t['high']:,.2f}" in every and "10,240" in every
    one = next(l for l in out if l.startswith("On top of one kit"))
    assert "One kit covers every piece" in one
    assert out[-3] == ESTIMATE_NOTE and out[-2] == ATTRIBUTION and out[-1] == DISCLAIMER
    # the stock-only fixture lot is named
    assert "Priced from current for-sale listings (no sales in 6 months): tile Medium Azur (LEGO 322)" in text


def test_thousands_separators():
    snap = parse_snapshot(snapshot_dict([lot_entry("6141", "lego_white",
                                                   sold=figures("1.0000", "0.5000", "2.0000"))]))
    grid = make_grid([("plate", "lego_white", "White", "1", 1500)])
    out = _lines(estimate_layout(grid, snap, as_of=date(2026, 12, 5)))
    every = next(l for l in out if l.startswith("Every piece"))
    assert "$1,500.00" in every and "$750.00" in every and "$3,000.00" in every and "1,500" in every


def test_stale_partial_and_incomplete_warnings():
    snap = parse_snapshot(snapshot_dict([
        lot_entry("6141", "lego_white"),
        lot_entry("6141", "lego_brick_yellow", sold=None, stock=figures("0.0500", "0.0200", "1.0000"))],
        complete=False, count=5))
    out = _lines(estimate_layout(make_grid(SMALL), snap, as_of=date(2027, 3, 31)))
    text = "\n".join(out)
    assert "Warning: prices are from 2026-12-01, 120 days before 2027-03-31; they may be out of date." in out
    assert "Warning: the snapshot is partial (2 of 5 lots)." in out
    assert "Incomplete: 27 pieces in 2 colors could not be priced:" in out
    assert "  tile 98138 Medium Azur (LEGO 322): not in the price snapshot; 20 pieces" in out
    assert "  tile 98138 Bright Red (LEGO 21): not in the price snapshot; 7 pieces" in out
    assert "  Hint: fetch every cited color with: lego-image-processor parts prices fetch --all-colors" in out
    assert "Priced from current for-sale listings (no sales in 6 months): plate Brick Yellow (LEGO 5)" in text
    stock_cell = next(l for l in out if l.startswith("Every piece"))
    assert "1 lot, 12 pcs" in stock_cell and "2 lots, 27 pcs" in stock_cell
    assert out[-1] == DISCLAIMER


def test_complete_estimate_has_no_warnings():
    out = _lines(_official())
    assert not any(l.startswith(("Warning", "Incomplete")) for l in out)


def test_lines_option_lists_every_lot_for_both_estimates():
    r = estimate_layout(make_grid(LAND_ELEVATION), load_snapshot(FIXTURE_SNAPSHOT), as_of=date(2026, 12, 5))
    out = _lines(r, lines=True)
    text = "\n".join(out)
    assert "Every piece, by lot:" in out and "On top of one kit, by lot:" in out
    i, j = out.index("Every piece, by lot:"), out.index("On top of one kit, by lot:")
    full_rows = [l for l in out[i:j] if l.startswith(("plate", "tile"))]
    assert len(full_rows) == len(r.estimates["full"].lines) == 13
    assert any("4073 / White (1)" in l and "sold" in l for l in full_rows)
    assert any("Dark Brown" in l and "unpriced" in l for l in full_rows)
    assert "$" in text and out[-1] == DISCLAIMER
    plain = _lines(r)
    assert "Every piece, by lot:" not in plain


# --- `parts prices fetch` text (011 T032; contracts/cli.md, FR-011) --------------------------------

from decimal import Decimal  # noqa: E402

from lego_image_processor.prices.fetch import AuthError, PriceFetchError  # noqa: E402
from lego_image_processor.prices.snapshot import SnapshotLot  # noqa: E402
from lego_image_processor.prices.lots import parse_lot  # noqa: E402
from lego_image_processor.prices.text import (UNCHECKED_NOTE, fetch_summary, progress_line,  # noqa: E402
                                              resume_command, stop_message)


def _entry(spec, sold=True, stock=True, error=None):
    snap = load_snapshot(FIXTURE_SNAPSHOT)
    base = snap.lots[0]
    return SnapshotLot(lot=parse_lot(spec), sold=base.sold if sold else None,
                       stock=base.stock if stock else None, retrieved_at=base.retrieved_at, error=error)


def test_progress_line_format():
    assert progress_line(3, 19, _entry("98138:140")) == (
        "[ 3/19] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63): sold 1,204 sales, "
        "stock 3,110 lots")
    assert progress_line(1, 2, _entry("6141:1", sold=False)).endswith("sold none, stock 3,110 lots")
    assert progress_line(1, 2, _entry("6141:1", sold=False, stock=False, error="not found")).endswith(
        ": not found on BrickLink (unpriced)")


def test_unchecked_note():
    assert UNCHECKED_NOTE == ("Note: BrickLink API details in bricklink_api.json are not yet checked "
                              "against the live documentation.")


def test_summary_first_snapshot():
    snap = load_snapshot(FIXTURE_SNAPSHOT)
    out = fetch_summary("data/x.json", snap, None)
    assert out[0] == ("Wrote price snapshot data/x.json: 18 lots (complete); priced from sales 17, "
                      "from stock only 1, unpriced 0.")
    assert out[1] == "Largest changes in unit average: none (first snapshot)."
    assert out[-3:] == ["Review the file, then commit it.", ATTRIBUTION, DISCLAIMER]


def test_summary_largest_changes():
    old = snapshot_dict(lots=[lot_entry("98138", "lego_vibrant_coral", sold=figures("0.0712")),
                              lot_entry("6141", "lego_white", sold=figures("0.0400")),
                              lot_entry("98138", "lego_earth_blue", sold=figures("0.0500"))])
    old["lots"].sort(key=lambda l: (l["part_id"] != "6141", l["lego_color_id"]))
    old["retrieved"] = {"started_at": "2026-09-01T10:00:00Z", "finished_at": "2026-09-01T10:01:00Z"}
    for l in old["lots"]:
        l["retrieved_at"] = "2026-09-01T10:00:30Z"
    new = snapshot_dict(lots=[lot_entry("98138", "lego_vibrant_coral", sold=figures("0.0950")),
                              lot_entry("6141", "lego_white", sold=figures("0.0400")),
                              lot_entry("98138", "lego_earth_blue", sold=figures("0.0450"))])
    new["lots"].sort(key=lambda l: (l["part_id"] != "6141", l["lego_color_id"]))
    out = fetch_summary("p.json", parse_snapshot(new), parse_snapshot(old))
    assert out[1] == "Largest changes in unit average since 2026-09-01:"
    assert out[2] == "  tile 98138 Vibrant Coral (353): $0.0712 -> $0.0950 (+33.4%)"
    assert out[3] == "  tile 98138 Earth Blue (140): $0.0500 -> $0.0450 (-10.0%)"
    assert out[4] == "  plate 6141 White (1): $0.0400 -> $0.0400 (0.0%)"
    assert out[5] == "Review the file, then commit it."


def test_summary_partial():
    d = snapshot_dict(complete=False, count=19)
    out = fetch_summary("p.json", parse_snapshot(d))
    assert out[0].startswith("Wrote price snapshot p.json: 2 lots (partial, 2 of 19);")


def test_resume_command_repeats_options():
    assert resume_command("data/snap.json") == "lego-image-processor parts prices fetch -o data/snap.json --resume"
    assert resume_command("my dir/s.json", all_colors=True, interval=2.0, max_attempts=3,
                          write_partial=True, compare="old.json") == (
        "lego-image-processor parts prices fetch -o 'my dir/s.json' --resume --all-colors "
        "--write-partial --interval 2 --max-attempts 3 --compare old.json")
    assert resume_command("s.json", lots=["98138:140", "6141:1"]).endswith("--lot 98138:140 --lot 6141:1")


def test_stop_message():
    from pathlib import Path

    e = PriceFetchError("BrickLink API HTTP 503 for tile 98138 Earth Blue (LEGO 140) (sold) after 5 attempts")
    e.done, e.total, e.progress_path = 12, 19, Path("d/s.progress.json")
    msg = stop_message(e, "lego-image-processor parts prices fetch -o d/s.json --resume")
    assert msg == ("BrickLink API HTTP 503 for tile 98138 Earth Blue (LEGO 140) (sold) after 5 attempts; "
                   "12 of 19 lots saved in d/s.progress.json; no snapshot written. Resume with: "
                   "lego-image-processor parts prices fetch -o d/s.json --resume")
    a = AuthError("BrickLink rejected the credentials (x). y")
    a.done, a.total, a.progress_path = 0, 19, Path("p")
    assert "no lot finished yet (0 of 19)" in stop_message(a, "cmd")
