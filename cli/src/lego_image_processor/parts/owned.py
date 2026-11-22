"""Parts a maker already owns (feature 005 US3, Q1): whole kits plus loose and missing parts.

Loose (``--owned``) and missing (``--missing``) parts are read from Rebrickable's documented import
CSV (help page "Importing Parts"): ``Part,Color,Quantity`` with Rebrickable part and color numbers,
or ``Element,Quantity``. Headers are case-insensitive and in any order; extra columns (for example
Rebrickable's ``Is Spare``) are ignored; a BOM and CRLF line endings are accepted; blank lines are
skipped and duplicate rows are summed. Rows for parts other than the two map parts are ignored and
counted, so a full set inventory export can be passed in.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from ..kit.part_colors import PartColorTable, load_part_colors
from ..kit.part_numbers import PartNumberTable, load_part_numbers

LotKey = Tuple[str, str]  # (project part ID, color key)


class OwnedFileError(ValueError):
    """A bad owned/missing file; carries the file and line number."""

    def __init__(self, path: Union[str, Path], line: Optional[int], message: str):
        self.path, self.line = str(path), line
        where = f"{self.path}:{line}" if line else self.path
        super().__init__(f"{where}: {message}")


@dataclass(frozen=True)
class OwnedFile:
    path: str
    sha256: str
    quantities: Dict[LotKey, int]
    ignored_rows: int

    def __hash__(self) -> int:
        return hash((self.path, self.sha256))


@dataclass(frozen=True)
class OwnedInputs:
    """What the maker says they own. Nothing is assumed beyond this."""

    kits: int = 0
    owned_files: Tuple[OwnedFile, ...] = ()
    missing_files: Tuple[OwnedFile, ...] = ()
    spares_percent: Fraction = field(default_factory=lambda: Fraction(0))

    def __post_init__(self) -> None:
        if not isinstance(self.kits, int) or isinstance(self.kits, bool) or self.kits < 0:
            raise ValueError(f"kits must be an integer >= 0, got {self.kits!r}")
        p = Fraction(self.spares_percent)
        if p < 0 or p > 100:
            raise ValueError(f"spares percent must be between 0 and 100, got {self.spares_percent}")
        object.__setattr__(self, "spares_percent", p)

    @property
    def ignored_rows(self) -> int:
        return sum(f.ignored_rows for f in self.owned_files + self.missing_files)

    def loose(self, key: LotKey) -> int:
        return sum(f.quantities.get(key, 0) for f in self.owned_files)

    def missing(self, key: LotKey) -> int:
        return sum(f.quantities.get(key, 0) for f in self.missing_files)


def parse_percent(value: Union[str, int, float, Decimal, Fraction]) -> Fraction:
    """A spares percentage 0-100 as an exact fraction (no float rounding)."""
    if isinstance(value, Fraction):
        p = value
    else:
        try:
            p = Fraction(Decimal(str(value).strip()))
        except (InvalidOperation, ValueError):
            raise ValueError(f"spares percent must be a number between 0 and 100, got {value!r}")
    if p < 0 or p > 100:
        raise ValueError(f"spares percent must be between 0 and 100, got {value}")
    return p


def percent_text(p: Fraction) -> str:
    """Decimal text for a percentage, e.g. ``2``, ``2.5``."""
    if p.denominator == 1:
        return str(p.numerator)
    d = (Decimal(p.numerator) / Decimal(p.denominator)).normalize()
    return format(d, "f")


def _quantity(text: str, path, line) -> int:
    t = (text or "").strip()
    if not t.isdigit():
        raise OwnedFileError(path, line, f"quantity must be a whole number >= 0, got {text!r}")
    return int(t)


def parse_owned_text(text: str, path: Union[str, Path] = "<owned>",
                     part_colors: Optional[PartColorTable] = None,
                     part_numbers: Optional[PartNumberTable] = None) -> Tuple[Dict[LotKey, int], int]:
    """Quantities per (part, color key) and the number of ignored rows (non-map parts)."""
    part_colors = part_colors or load_part_colors()
    part_numbers = part_numbers or load_part_numbers()
    if text.startswith("﻿"):
        text = text[1:]
    reader = csv.reader(io.StringIO(text, newline=""))
    header = None
    for row in reader:
        if any(c.strip() for c in row):
            header = [c.strip().lower() for c in row]
            break
    if header is None:
        raise OwnedFileError(path, None, "empty file: expected a header 'Part,Color,Quantity' or "
                                         "'Element,Quantity' (Rebrickable import CSV)")
    hline = reader.line_num
    col = {name: i for i, name in reversed(list(enumerate(header)))}
    if {"part", "color", "quantity"} <= set(col):
        shape = "part"
    elif {"element", "quantity"} <= set(col):
        shape = "element"
    else:
        raise OwnedFileError(path, hline, f"header {','.join(header)!r} not recognised: expected "
                                          "'Part,Color,Quantity' or 'Element,Quantity' (Rebrickable import CSV)")
    rebrickable_part = {part_numbers.get(p).rebrickable_part_num: p for p in part_numbers.parts}
    other_numbers = {}
    for p, n in part_numbers.parts.items():
        for alt in (n.bricklink_item_no,) + n.bricklink_alternates + n.lego_design_ids:
            if alt not in rebrickable_part:
                other_numbers[alt] = p
    by_color = {p: {c.rebrickable.id: c.key for c in part_colors.for_part(p)} for p in part_colors.parts}
    by_element = {}
    for p in part_colors.parts:
        for c in part_colors.for_part(p):
            for e in (c.element_id,) + tuple(c.element_ids):
                by_element[e] = (p, c.key)
    out: Dict[LotKey, int] = {}
    ignored = 0
    for row in reader:
        line = reader.line_num
        if not any(c.strip() for c in row):
            continue
        cell = lambda name: row[col[name]].strip() if col[name] < len(row) else ""  # noqa: E731
        qty = _quantity(cell("quantity"), path, line)
        if shape == "part":
            num, color = cell("part"), cell("color")
            if num in other_numbers:
                raise OwnedFileError(path, line, f"part {num} is another catalog's number for map part "
                                                 f"{other_numbers[num]}; this file must use Rebrickable "
                                                 f"part numbers ({', '.join(sorted(rebrickable_part))})")
            if num not in rebrickable_part:
                ignored += 1
                continue
            part = rebrickable_part[num]
            try:
                cid = int(color)
            except ValueError:
                raise OwnedFileError(path, line, f"color {color!r} is not a Rebrickable color number")
            key = by_color[part].get(cid)
            if key is None:
                raise OwnedFileError(path, line, f"part {num} in Rebrickable color {cid} has no cited "
                                                 f"row (see: lego-image-processor kit part-colors --part {part})")
        else:
            element = cell("element")
            if element not in by_element:
                raise OwnedFileError(path, line, f"element {element!r} is not listed for a cited map "
                                                 "part color (see: lego-image-processor kit part-colors)")
            part, key = by_element[element]
        out[(part, key)] = out.get((part, key), 0) + qty
    return out, ignored


def parse_owned_csv(path: Union[str, Path], part_colors: Optional[PartColorTable] = None,
                    part_numbers: Optional[PartNumberTable] = None) -> OwnedFile:
    p = Path(path)
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise OwnedFileError(path, None, f"cannot read file ({exc.strerror or exc})")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise OwnedFileError(path, None, "file is not UTF-8 text")
    quantities, ignored = parse_owned_text(text, path, part_colors, part_numbers)
    return OwnedFile(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                     quantities=quantities, ignored_rows=ignored)
