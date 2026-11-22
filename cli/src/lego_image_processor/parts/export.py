"""Marketplace files for a parts list (feature 005 US2): BrickLink wanted list and Rebrickable CSV.

Formats from the marketplaces' help pages (research R2, R3):

- BrickLink "Wanted List, Mass Upload": no XML declaration; ``<INVENTORY>`` with one ``<ITEM>`` per
  item; ``ITEMTYPE`` and ``ITEMID`` required; ``COLOR`` (BrickLink color ID), ``MINQTY`` (whole
  number > 0) and ``CONDITION`` (N or U) optional.
- Rebrickable "Importing Parts": header ``Part,Color,Quantity`` with Rebrickable part and color
  numbers.

Only verified lots with something to buy are written. The files carry no disclaimer and no
timestamp (Q4); the command that writes them prints the disclaimer.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from typing import Optional, Tuple
from xml.sax.saxutils import escape

from .partslist import Lot, PartsList

CONDITIONS = {"new": "N", "used": "U", "N": "N", "U": "U"}
BRICKLINK_UPLOAD_NOTE = ("BrickLink: uploading adds these quantities to items already on the chosen "
                         "wanted list.")


class UnverifiedLotsError(Exception):
    """Unverified lots have pieces to buy and ``allow_partial`` is False (exit 6)."""

    exit_code = 6

    def __init__(self, lots: Tuple[Lot, ...]):
        self.lots = lots
        names = ", ".join(f"{l.part_type} {l.layout_color_name} ({l.color_key}: {l.reason})" for l in lots)
        super().__init__(f"{len(lots)} lot(s) have no cited marketplace IDs: {names}")


def blocking_lots(parts_list: PartsList) -> Tuple[Lot, ...]:
    """Unverified lots that still have pieces to buy."""
    return tuple(l for l in parts_list.unverified_lots if l.to_buy > 0)


def export_lots(parts_list: PartsList, allow_partial: bool = False) -> Tuple[Lot, ...]:
    blocked = blocking_lots(parts_list)
    if blocked and not allow_partial:
        raise UnverifiedLotsError(blocked)
    return tuple(l for l in parts_list.lots if l.verified and l.to_buy > 0)


def to_bricklink_xml(parts_list: PartsList, condition: Optional[str] = None,
                     allow_partial: bool = False) -> Optional[str]:
    """BrickLink wanted-list XML, or None when there is nothing (verified) to buy."""
    cond = None
    if condition is not None:
        if condition not in CONDITIONS:
            raise ValueError(f"condition must be new or used, got {condition!r}")
        cond = CONDITIONS[condition]
    lots = export_lots(parts_list, allow_partial)
    if not lots:
        return None
    lines = ["<INVENTORY>"]
    for lot in lots:
        r = lot.ids
        lines += ["  <ITEM>",
                  f"    <ITEMTYPE>{escape(r.bricklink_item_type)}</ITEMTYPE>",
                  f"    <ITEMID>{escape(r.bricklink_item_no)}</ITEMID>",
                  f"    <COLOR>{int(r.bricklink_color_id)}</COLOR>",
                  f"    <MINQTY>{int(lot.to_buy)}</MINQTY>"]
        if cond:
            lines.append(f"    <CONDITION>{cond}</CONDITION>")
        lines.append("  </ITEM>")
    lines.append("</INVENTORY>")
    return "\n".join(lines) + "\n"


def _csv_field(value: str) -> str:
    v = str(value)
    if any(ch in v for ch in ',"\n\r'):
        return '"' + v.replace('"', '""') + '"'
    return v


def to_rebrickable_csv(parts_list: PartsList, allow_partial: bool = False) -> Optional[str]:
    """Rebrickable ``Part,Color,Quantity`` CSV, or None when there is nothing (verified) to buy."""
    lots = export_lots(parts_list, allow_partial)
    if not lots:
        return None
    rows = ["Part,Color,Quantity"]
    rows += [",".join((_csv_field(l.ids.rebrickable_part_num), str(int(l.ids.rebrickable_color_id)),
                       str(int(l.to_buy)))) for l in lots]
    return "\n".join(rows) + "\n"
