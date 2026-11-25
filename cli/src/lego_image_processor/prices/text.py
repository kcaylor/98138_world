"""Human-readable output for price estimates (feature 011; contracts/cli.md).

Formatting only: every figure comes from ``EstimateReport``. Output ends with the estimate
wording, the BrickLink attribution and the LEGO disclaimer (FR-018).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Callable, List, Sequence

from ..parts.partslist import PART_TYPE_TEXT, PLAQUE_PART_TYPE, positions_text, template_text
from .estimate import KINDS, Estimate, EstimateLine, EstimateReport, plaque_specs
from .wording import (ALL_COLORS_HINT, ATTRIBUTION, DISCLAIMER, ESTIMATE_NOTE, NOTHING_TO_BUY_TEXT,
                      REASON_NOT_IN_SNAPSHOT, SHORT_LABELS, STATISTIC_TEXT, plaque_lot_hint)

Echo = Callable[..., None]


def usd(d: Decimal) -> str:
    """``$1,150.00`` (cents; display only)."""
    return f"${d:,.2f}"


def unit_usd(d: Decimal) -> str:
    """A unit price exactly as in the snapshot, e.g. ``$0.0385``."""
    return f"${d:,}"


def _count(lots: int, pieces: int) -> str:
    if not lots:
        return "0"
    return f"{lots} lot{'s' if lots != 1 else ''}, {pieces:,} pcs"


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]], right: Sequence[int] = ()) -> List[str]:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]

    def fmt(cells):
        out = []
        for i, (c, w) in enumerate(zip(cells, widths)):
            out.append(str(c).rjust(w) if i in right else str(c).ljust(w))
        return "  ".join(out).rstrip()
    return [fmt(headers)] + [fmt(r) for r in rows]


def _summary_rows(report: EstimateReport) -> List[List[str]]:
    rows = []
    for k in KINDS:
        e = report.estimates[k]
        if e.nothing_to_buy:
            rows.append([SHORT_LABELS[k], NOTHING_TO_BUY_TEXT])
            continue
        t, b = e.totals, e.by_basis
        rows.append([SHORT_LABELS[k], usd(t["average"]), usd(t["low"]), usd(t["high"]),
                     f"{e.pieces:,}", str(e.lots), _count(**b["stock"]), _count(**b["unpriced"])])
    return rows


def _summary_table(report: EstimateReport) -> List[str]:
    headers = ["", "average", "low", "high", "pieces", "lots", "priced from stock", "unpriced"]
    width = len(max(SHORT_LABELS.values(), key=len))
    rows = [[r[0].ljust(width), *r[1:]] for r in _summary_rows(report)]
    full_rows = [r for r in rows if len(r) == len(headers)]
    lines = format_table(headers, full_rows or [[" " * width] + [""] * (len(headers) - 1)],
                         right=(1, 2, 3, 4, 5))
    out, it = [lines[0]], iter(lines[1:])
    for r in rows:
        out.append(next(it) if len(r) == len(headers) else f"{r[0].ljust(width)}   {r[1]}")
    return out


def _lot_name(l: EstimateLine) -> str:
    lot = l.lot
    if lot.ids is None:
        return (f"{PART_TYPE_TEXT[lot.part_type]} {lot.part_id} {lot.layout_color_name} "
                f"(code {lot.layout_color_code})")
    return f"{PART_TYPE_TEXT[lot.part_type]} {lot.part_id} {lot.ids.lego_name} (LEGO {lot.ids.lego_id})"


def _lot_rows(e: Estimate) -> List[List[str]]:
    rows = []
    for l in e.lines:
        lot = l.lot
        if lot.ids is None:
            color, bl = f"{lot.layout_color_name} ({lot.layout_color_code})", "unverified"
        else:
            r = lot.ids
            color = f"{r.lego_name} ({r.lego_id})"
            bl = f"{r.bricklink_item_no} / {r.bricklink_color_name} ({r.bricklink_color_id})"
        unit = [unit_usd(x) for x in l.unit] if l.unit else ["-"] * 3
        line = [usd(x) for x in l.line] if l.line else ["-"] * 3
        rows.append([PART_TYPE_TEXT[lot.part_type], color, bl, f"{l.quantity:,}", l.basis, *unit, *line,
                     l.reason or ""])
    return rows


def echo_estimate(report: EstimateReport, lines: bool = False, echo: Echo = None) -> None:
    """Print the estimate table (contracts/cli.md `parts estimate` human output)."""
    if echo is None:
        import click
        echo = click.echo
    lay = report.layout
    recipe = (lay.get("map") or {}).get("recipe") or {}
    what = f"recipe {recipe['id']}" if recipe.get("id") else lay.get("source_image") or "layout"
    lots = [l.lot for l in report.estimates["full"].lines]  # every lot: the full estimate needs them all
    echo(f"Price estimate for {lay.get('path') or 'layout'} ({what}; {positions_text(lay, lots)}; "
         "map pieces only)")
    arr = lay.get("arrangement") or {}
    if arr.get("id", "A") != "A":
        echo(f"Arrangement: {arr['id']} ({arr['name']}). {arr['note']}")
    t = lay.get("template")  # feature 016: non-kit layouts only
    if t:
        echo(template_text(t, lots))
    s = report.snapshot
    snap = report._snapshot_obj
    sha = f"SHA-256 {s['sha256'][:8]}…" if s.get("sha256") else "SHA-256 unknown"
    state = "complete" if s["complete"] else (
        f"partial ({len(snap.lots)} of {snap.lot_set['count']} lots)" if snap else "partial")
    echo(f"Prices: BrickLink price guide, retrieved {s['retrieved_at'][:10]} ({STATISTIC_TEXT}). "
         f"Snapshot {s.get('file') or 'in memory'} ({sha}), {state}.")
    echo()
    for line in _summary_table(report):
        echo(line)
    echo()
    st = report.staleness
    if st["stale"]:
        echo(f"Warning: prices are from {s['retrieved_at'][:10]}, {st['age_days']:,} days before "
             f"{st['as_of']}; they may be out of date.")
    if not s["complete"] and snap is not None:
        echo(f"Warning: the snapshot is partial ({len(snap.lots)} of {snap.lot_set['count']} lots).")
    full = report.estimates["full"]
    unpriced = full.unpriced_lines
    if unpriced:
        u = full.by_basis["unpriced"]
        echo(f"Incomplete: {_plural(u['pieces'], 'piece')} in {_plural(u['lots'], 'color')} could not "
             "be priced:")
        for l in unpriced:
            echo(f"  {_lot_name(l)}: {l.reason}; {_plural(l.quantity, 'piece')}")
        missing = [l for l in unpriced if l.reason == REASON_NOT_IN_SNAPSHOT]
        if any(l.lot.part_type != PLAQUE_PART_TYPE for l in missing):
            echo(f"  Hint: fetch every cited color with: {ALL_COLORS_HINT}")
        for spec in plaque_specs(missing):  # feature 017
            echo(f"  Hint: {plaque_lot_hint(spec)}")
    if full.stock_lines:
        echo("Priced from current for-sale listings (no sales in 6 months): "
             + ", ".join(l.label for l in full.stock_lines))
    if lines:
        headers = ["part", "color (LEGO id)", "BrickLink item / color (id)", "quantity", "basis",
                   "unit avg", "unit low", "unit high", "line avg", "line low", "line high", "reason"]
        for k in KINDS:
            e = report.estimates[k]
            echo()
            echo(f"{SHORT_LABELS[k]}, by lot:")
            if e.nothing_to_buy:
                echo(f"  {NOTHING_TO_BUY_TEXT}.")
                continue
            for line in format_table(headers, _lot_rows(e), right=(3, 5, 6, 7, 8, 9, 10)):
                echo(line)
        echo()
    echo(ESTIMATE_NOTE)
    echo(ATTRIBUTION)
    echo(DISCLAIMER)


def estimate_summary_line(report: EstimateReport) -> str:
    """One line for ``-o``: both estimates' averages and ranges."""
    parts = []
    for k in KINDS:
        e = report.estimates[k]
        if e.nothing_to_buy:
            parts.append(f"{SHORT_LABELS[k].lower()}: {NOTHING_TO_BUY_TEXT.lower()}")
            continue
        t = e.totals
        parts.append(f"{SHORT_LABELS[k].lower()} {usd(t['average'])} ({usd(t['low'])}-{usd(t['high'])})"
                     + ("" if e.complete else ", incomplete"))
    return "; ".join(parts)


# --- `parts prices fetch` (contracts/cli.md) ------------------------------------------------------

UNCHECKED_NOTE = ("Note: BrickLink API details in bricklink_api.json are not yet checked against the "
                  "live documentation.")
REVIEW_TEXT = "Review the file, then commit it."


def _guide_count(figures, what: str) -> str:
    return "none" if figures is None else f"{figures.unit_quantity:,} {what}"


def progress_line(index: int, total: int, entry) -> str:
    """``[ 3/19] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63): sold 812 sales, stock 140 lots``."""
    lot = entry.lot
    head = (f"[{index:>{len(str(total))}}/{total}] {PART_TYPE_TEXT[lot.part_type]} {lot.part_id} {lot.lego_color_name} "
            f"(BrickLink {lot.bricklink_item_no} / {lot.bricklink_color_name}, color {lot.bricklink_color_id})")
    if entry.error:
        return f"{head}: {entry.error} on BrickLink (unpriced)"
    return f"{head}: sold {_guide_count(entry.sold, 'sales')}, stock {_guide_count(entry.stock, 'lots')}"


def _pct(p: Decimal) -> str:
    q = p.quantize(Decimal("0.1"))
    return f"{'+' if q > 0 else ''}{q}%"


def fetch_summary(path, snapshot, previous=None) -> List[str]:
    """The success summary (also printed with ``-q``), ending with attribution and disclaimer."""
    from .snapshot import largest_changes

    count = snapshot.lot_set["count"]
    state = "complete" if snapshot.complete else f"partial, {len(snapshot.lots)} of {count}"
    bases = [l.basis for l in snapshot.lots]
    out = [f"Wrote price snapshot {path}: {len(snapshot.lots)} lots ({state}); priced from sales "
           f"{bases.count('sold')}, from stock only {bases.count('stock')}, unpriced {bases.count('unpriced')}."]
    if previous is None:
        out.append("Largest changes in unit average: none (first snapshot).")
    else:
        changes = largest_changes(previous, snapshot)
        if not changes:
            out.append(f"Largest changes in unit average since {previous.retrieved_on}: no lot is priced "
                       "in both snapshots.")
        else:
            out.append(f"Largest changes in unit average since {previous.retrieved_on}:")
            for lot, old, new, pct in changes:
                out.append(f"  {PART_TYPE_TEXT[lot.part_type]} {lot.part_id} {lot.lego_color_name} ({lot.lego_color_id}): "
                           f"{unit_usd(old)} -> {unit_usd(new)} ({_pct(pct)})")
    out += [REVIEW_TEXT, ATTRIBUTION, DISCLAIMER]
    return out


def stop_message(exc, resume: str) -> str:
    """The error text for a stopped fetch: the cause, what was saved, and how to resume."""
    msg = str(exc)
    if getattr(exc, "progress_path", None) is None:
        return msg
    if exc.done:
        msg += f"; {exc.done} of {exc.total} lots saved in {exc.progress_path}"
    else:
        msg += f"; no lot finished yet (0 of {exc.total})"
    if getattr(exc, "partial_path", None) is not None:
        msg += f"; partial snapshot (complete: false) written to {exc.partial_path}"
    else:
        msg += "; no snapshot written"
    return msg + (f". Resume with: {resume}" if exc.done else ". Run the same command again to retry.")


def resume_command(output, *, all_colors=False, lots=(), interval=None, max_attempts=None,
                   write_partial=False, compare=None) -> str:
    """``lego-image-processor parts prices fetch -o PATH --resume`` plus the options used."""
    import shlex

    parts = ["lego-image-processor", "parts", "prices", "fetch", "-o", shlex.quote(str(output)), "--resume"]
    if all_colors:
        parts.append("--all-colors")
    for spec in lots:
        parts += ["--lot", shlex.quote(spec)]
    if write_partial:
        parts.append("--write-partial")
    if interval is not None:
        parts += ["--interval", f"{interval:g}"]
    if max_attempts is not None:
        parts += ["--max-attempts", str(max_attempts)]
    if compare is not None:
        parts += ["--compare", shlex.quote(str(compare))]
    return " ".join(parts)
