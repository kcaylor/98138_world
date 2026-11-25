"""Sticker text: the resolved title and line, legend numbers, and text blocks that wrap, then
shrink, but never truncate (feature 017; FR-004, FR-013; research R3, R7, R8).

- ``resolve_text(recipe)``: the sticker title (``[sticker] title``, else the recipe title) and
  line (``[sticker] line``, else the recipe description), each with its source.
- Numbers: hyphen-minus, comma thousands separator, no trailing zeros, a space before the unit,
  "°C" for the Celsius spellings (``maps.cells`` mapping). Without a step a number keeps up to six
  significant digits; rank-derived bounds round to the display step
  10^(floor(log10(max - min)) - 1), half away from zero (``decimal.ROUND_HALF_UP``).
- ``fit_block``: a block starts at its preferred size, wraps at spaces within its line limit (and
  height, when given), then shrinks in 0.25 pt steps to 5 pt; a block of several paragraphs
  (``TextSpec.paragraphs``, such as one data credit per line) starts each on a new line, all at
  one size; ``fit_stack`` shrinks a top-down
  stack of blocks together. A word wider than the block at 5 pt, or text that still does not fit,
  raises ``StickerError`` with the sticker, the field and the space needed and available in mm.
  Widths are Helvetica's standard metrics (``sheets.compose.text_width``), which the SVG keeps
  with ``textLength`` (research R4). The build sheets' ``wrap``/``fit`` cut text with "...";
  stickers never do.
- A sticker title that wraps is balanced (``balanced_wrap``; approved with the sticker texts by
  the project owner, 2026-11-24): the greedy wrap's number of lines, with the break points that
  make the widest line narrowest, so the last line is not a single short word ("El Niño, /
  December 1997"); a title does not break between a word and the number after it ("World Map, /
  kit 31203 design") unless nothing else fits. Sizes are chosen exactly as for a greedy wrap.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Sequence, Tuple, Union

from ..maps.cells import _UNITS
from ..maps.recipe import Recipe
from ..sheets.compose import text_width
from ..sheets.model import PT_MM, WHITE, RGB, Text
from . import StickerError

MIN_PT = 5.0          # FR-013: no sticker text below 5 pt
STEP_PT = 0.25        # research R3: shrink in quarter points
LEADING = 1.3         # line pitch in em, as the build sheets' text flow (sheets/compose.py Flow)
CAP_HEIGHT = 0.718    # Helvetica cap height in em (sheets/compose.py cap_offset)
SIGNIFICANT = 6       # digits kept by a number without a display step (research R7)
_EPS = 1e-9

SOURCE_TABLE = "sticker table"
SOURCE_TITLE = "recipe title"
SOURCE_DESCRIPTION = "recipe description"
ALIGNS = ("left", "center", "right")
BALANCED_FIELDS = ("title",)   # wrapped by ``balanced_wrap`` (the project owner, 2026-11-24)

Number = Union[int, float, Decimal]


# --- resolved title and line (FR-004) ----------------------------------------------------------

@dataclass(frozen=True)
class ResolvedText:
    """The sticker title and line and where each came from (data-model.md StickerText)."""

    title: str
    title_source: str
    line: str
    line_source: str

    def to_dict(self):
        return {"title": self.title, "title_source": self.title_source, "line": self.line,
                "line_source": self.line_source}


def resolve_text(recipe: Recipe) -> ResolvedText:
    """Title: the ``[sticker]`` table's, else the recipe's. Line: the table's, else the recipe's
    description; with neither, ``StickerError`` "add a [sticker] line"."""
    table = recipe.sticker
    if table is not None and table.title:
        title, title_source = table.title, SOURCE_TABLE
    else:
        title, title_source = recipe.title, SOURCE_TITLE
    if table is not None:
        line, line_source = table.line, SOURCE_TABLE
    elif (recipe.description or "").strip():
        line, line_source = recipe.description.strip(), SOURCE_DESCRIPTION
    else:
        raise StickerError(f"recipe {recipe.id} has no sticker line and no description: add a "
                           f"[sticker] line (contracts/recipe-sticker.md)")
    return ResolvedText(title=title, title_source=title_source, line=line, line_source=line_source)


# --- numbers (research R7, R8) -----------------------------------------------------------------

def to_decimal(value: Number) -> Decimal:
    """``value`` as a Decimal: floats by their shortest round-trip text (so 0.15 is 0.15)."""
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, int) and not isinstance(value, bool):
        d = Decimal(value)
    else:
        d = Decimal(repr(float(value)))
    if not d.is_finite():
        raise ValueError(f"not a finite number: {value!r}")
    return d


def display_step(lo: Number, hi: Number) -> Decimal:
    """Two significant digits of the range: 10^(floor(log10(hi - lo)) - 1); ocean-sst 1 °C,
    bathymetry 100 m (research R8). A range of one value uses that value's magnitude (1 for 0)."""
    span = to_decimal(hi) - to_decimal(lo)
    if span < 0:
        raise ValueError(f"display_step: {hi!r} is below {lo!r}")
    ref = span if span > 0 else abs(to_decimal(hi))
    if ref == 0:
        return Decimal(1)
    return Decimal(1).scaleb(ref.adjusted() - 1)


def round_to_step(value: Number, step: Number) -> Decimal:
    """``value`` rounded to a multiple of ``step`` (a power of ten), half away from zero."""
    step = to_decimal(step)
    if step <= 0:
        raise ValueError(f"step must be > 0, not {step}")
    d = (to_decimal(value) / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step
    return Decimal(0) if d == 0 else d


def round_significant(value: Number, digits: int = SIGNIFICANT) -> Decimal:
    d = to_decimal(value)
    if d == 0:
        return Decimal(0)
    d = d.quantize(Decimal(1).scaleb(d.adjusted() - digits + 1), rounding=ROUND_HALF_UP)
    return Decimal(0) if d == 0 else d


def format_number(value: Number, step: Optional[Number] = None) -> str:
    """"3,000", "-1.5", "0.08": hyphen-minus, comma thousands, no trailing zeros, no exponent."""
    d = round_significant(value) if step is None else round_to_step(value, step)
    d = d.normalize()
    if d == 0:
        return "0"
    return format(d, ",f")


def display_units(units: str) -> str:
    """"°C" for the Celsius spellings (``degC`` ...), other units as given."""
    return _UNITS.get((units or "").lower(), units or "")


def format_quantity(value: Number, units: str, step: Optional[Number] = None) -> str:
    """A number and its unit with a space between ("3,000 m", "1 °C"); no unit, no space."""
    u = display_units(units)
    n = format_number(value, step)
    return f"{n} {u}" if u else n


def number_value(d: Decimal) -> Union[int, float]:
    """A displayed Decimal as a JSON number: an int when whole, else a float."""
    d = to_decimal(d)
    if d == d.to_integral_value():
        return int(d)
    return float(d)


# --- text blocks (research R3, FR-013) ---------------------------------------------------------

def line_pitch(size_pt: float) -> float:
    """Baseline to baseline (mm) at ``size_pt``."""
    return size_pt * PT_MM * LEADING


def block_height(n_lines: int, size_pt: float) -> float:
    return n_lines * line_pitch(size_pt)


@dataclass(frozen=True)
class TextSpec:
    """What a block holds and how it may be set: ``max_lines`` at most, from ``preferred_pt``
    down to ``min_pt``."""

    field: str
    text: str
    preferred_pt: float
    max_lines: int
    bold: bool = False
    align: str = "left"
    min_pt: float = MIN_PT
    paragraphs: Tuple[str, ...] = ()   # when set, each starts a new line and ``text`` is unused

    def parts(self) -> Tuple[str, ...]:
        """The paragraphs to set: ``paragraphs``, else ``text`` as one."""
        return tuple(self.paragraphs) if self.paragraphs else (self.text,)

    def words(self) -> List[str]:
        return [w for p in self.parts() for w in _words(p)]

    def wrap(self, size_pt: float, width_mm: float) -> List[str]:
        """The lines at ``size_pt``: greedy, or balanced for the fields in ``BALANCED_FIELDS``
        (the same number of lines either way)."""
        if self.field in BALANCED_FIELDS:
            return [ln for p in self.parts()
                    for ln in balanced_wrap(p, size_pt, width_mm, self.bold, self.max_lines)]
        return [ln for p in self.parts() for ln in wrap_words(p, size_pt, width_mm, self.bold)]


@dataclass(frozen=True)
class TextBlock:
    """A fitted block (data-model.md TextBlock). ``box`` is (x, y, w, h) in the sticker's cut
    coordinates, ``y`` its top and ``h`` the height of its lines."""

    field: str
    lines: Tuple[str, ...]
    size_pt: float
    preferred_pt: float
    min_pt: float
    bold: bool
    align: str
    box: Tuple[float, float, float, float]

    def baselines(self) -> List[float]:
        """Each line's baseline: the cap height centred in its line pitch."""
        pitch = line_pitch(self.size_pt)
        off = (pitch + CAP_HEIGHT * self.size_pt * PT_MM) / 2
        y = self.box[1]
        return [y + i * pitch + off for i in range(len(self.lines))]

    def line_x(self) -> float:
        x, _, w, _ = self.box
        return {"left": x, "center": x + w / 2, "right": x + w}[self.align]

    def items(self, color: RGB = WHITE, tag: Optional[str] = None) -> List[Text]:
        """The block as ``sheets.model`` text items (tag: the field unless given)."""
        x = self.line_x()
        return [Text(x, y, line, self.size_pt, align=self.align, bold=self.bold, color=color,
                     tag=self.field if tag is None else tag)
                for line, y in zip(self.lines, self.baselines())]


def _words(text: str) -> List[str]:
    return text.split()


def wrap_words(text: str, size_pt: float, width_mm: float, bold: bool = False) -> List[str]:
    """Greedy wrap at spaces; never cuts a word, so a line can be wider than ``width_mm`` only
    when it is a single word that is."""
    lines: List[str] = []
    line = ""
    for word in _words(text):
        trial = word if not line else f"{line} {word}"
        if line and text_width(trial, size_pt, bold) > width_mm + _EPS:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def _starts_with_digit(word: str) -> bool:
    return word[:1].isdigit()


def balanced_wrap(text: str, size_pt: float, width_mm: float, bold: bool = False,
                  max_lines: Optional[int] = None) -> List[str]:
    """The lines of ``wrap_words`` (the same number), with the break points at spaces that make
    the widest line as narrow as possible (then the next widest, and so on), every line within
    ``width_mm``. A break never falls between a word and the number after it ("kit 31203",
    "December 1997") unless no split fits otherwise. One line, more lines than ``max_lines``
    (the block does not fit anyway) or a word wider than the block: the greedy lines as they
    are."""
    greedy = wrap_words(text, size_pt, width_mm, bold)
    n = len(greedy)
    if n < 2 or (max_lines is not None and n > max_lines):
        return greedy
    words = _words(text)
    m = len(words)
    widths = {}

    def width(i: int, j: int) -> float:
        if (i, j) not in widths:
            widths[(i, j)] = text_width(" ".join(words[i:j]), size_pt, bold)
        return widths[(i, j)]

    def best(breaks: Sequence[int]) -> Optional[Tuple[int, ...]]:
        chosen: Optional[Tuple[int, ...]] = None
        chosen_key: Optional[Tuple[float, ...]] = None
        for cuts in itertools.combinations(breaks, n - 1):
            bounds = (0, *cuts, m)
            ws = [width(bounds[k], bounds[k + 1]) for k in range(n)]
            if max(ws) > width_mm + _EPS:
                continue
            key = tuple(sorted(ws, reverse=True))
            if chosen_key is None or key < chosen_key:
                chosen, chosen_key = cuts, key
        return chosen

    tied = [b for b in range(1, m) if not _starts_with_digit(words[b])]
    cuts = best(tied) or best(range(1, m))
    if cuts is None:
        return greedy
    bounds = (0, *cuts, m)
    return [" ".join(words[bounds[k]:bounds[k + 1]]) for k in range(n)]


def _sizes(preferred: float, minimum: float) -> List[float]:
    if preferred < minimum:
        raise ValueError(f"preferred size {preferred} pt is below the minimum {minimum} pt")
    n = int(round((preferred - minimum) / STEP_PT + 1e-6))
    out = [preferred - i * STEP_PT for i in range(n + 1)]
    if out[-1] > minimum + _EPS:
        out.append(minimum)
    return out


def _check_spec(spec: TextSpec) -> None:
    if spec.align not in ALIGNS:
        raise ValueError(f"align must be one of {', '.join(ALIGNS)}")
    if spec.max_lines < 1:
        raise ValueError("max_lines must be at least 1")


def _try(spec: TextSpec, size: float, width_mm: float,
         height_mm: Optional[float]) -> Optional[List[str]]:
    """The wrapped lines when ``spec`` fits at ``size``, else None."""
    lines = spec.wrap(size, width_mm)
    if any(text_width(w, size, spec.bold) > width_mm + _EPS for w in spec.words()):
        return None
    if len(lines) > spec.max_lines:
        return None
    if height_mm is not None and block_height(len(lines), size) > height_mm + _EPS:
        return None
    return lines


def _block(spec: TextSpec, lines: Sequence[str], size: float, x: float, y: float,
           width_mm: float) -> TextBlock:
    return TextBlock(field=spec.field, lines=tuple(lines), size_pt=size, preferred_pt=spec.preferred_pt,
                     min_pt=spec.min_pt, bold=spec.bold, align=spec.align,
                     box=(x, y, width_mm, block_height(len(lines), size)))


def _fit_error(spec: TextSpec, sticker: str, width_mm: float,
               height_mm: Optional[float]) -> StickerError:
    size = spec.min_pt
    wide = [w for w in spec.words() if text_width(w, size, spec.bold) > width_mm + _EPS]
    if wide:
        need = max(text_width(w, size, spec.bold) for w in wide)
        return StickerError.does_not_fit(sticker, spec.field, need, width_mm, size)
    lines = spec.wrap(size, width_mm)
    need = block_height(len(lines), size)
    have = block_height(spec.max_lines, size)
    if height_mm is not None:
        have = min(have, height_mm)
    return StickerError.does_not_fit(sticker, spec.field, need, have, size)


def fit_block(spec: TextSpec, *, sticker: str, x: float, y: float, width_mm: float,
              height_mm: Optional[float] = None) -> TextBlock:
    """The largest size from ``spec.preferred_pt`` down to ``spec.min_pt`` (0.25 pt steps) at
    which the text wraps into ``spec.max_lines`` lines of ``width_mm`` (and ``height_mm``)."""
    _check_spec(spec)
    if not spec.words():
        raise StickerError(f"{sticker} sticker: {spec.field} is empty", sticker=sticker,
                           field=spec.field)
    for size in _sizes(spec.preferred_pt, spec.min_pt):
        lines = _try(spec, size, width_mm, height_mm)
        if lines is not None:
            return _block(spec, lines, size, x, y, width_mm)
    raise _fit_error(spec, sticker, width_mm, height_mm)


def fit_stack(specs: Sequence[TextSpec], *, sticker: str, x: float, y: float, width_mm: float,
              height_mm: float, gap_mm: float = 0.0) -> Tuple[TextBlock, ...]:
    """Blocks placed top-down from ``y`` with ``gap_mm`` between them, all within ``height_mm``.
    Each block first takes the size ``fit_block`` gives it; while the stack is too tall, every
    block drops one more 0.25 pt step (none below its minimum). Still too tall at the minimums:
    ``StickerError`` naming the stack's fields joined with " + "."""
    if not specs:
        return ()
    own = [fit_block(s, sticker=sticker, x=x, y=0.0, width_mm=width_mm) for s in specs]
    gaps = gap_mm * (len(specs) - 1)
    k = 0
    while True:
        sizes = [max(s.min_pt, min(b.size_pt, s.preferred_pt - k * STEP_PT))
                 for s, b in zip(specs, own)]
        # a smaller size never needs more lines (widths scale with the size), so each block that
        # fitted at its own size also fits here
        lines = [b.lines if size == b.size_pt else _try(s, size, width_mm, None) or list(b.lines)
                 for s, b, size in zip(specs, own, sizes)]
        total = sum(block_height(len(ls), size) for ls, size in zip(lines, sizes)) + gaps
        if total <= height_mm + _EPS:
            out, top = [], y
            for s, ls, size in zip(specs, lines, sizes):
                b = _block(s, ls, size, x, top, width_mm)
                out.append(b)
                top += b.box[3] + gap_mm
            return tuple(out)
        if all(size <= s.min_pt + _EPS for s, size in zip(specs, sizes)):
            field = " + ".join(s.field for s in specs)
            raise StickerError.does_not_fit(sticker, field, total, height_mm,
                                            min(s.min_pt for s in specs))
        k += 1
