"""Data credits for a sticker set (feature 017, FR-007; research R9; data-model.md Credit).

One credit per dataset the map uses, in ``Recipe.datasets()`` order (layer datasets, a
``land_from`` mask dataset, override datasets), then, on a non-kit template, the template's
dataset; each dataset once. The large sticker prints one "Data:" line per credit, "<registry
title>, doi:<doi>" or "<registry title>, <publisher>" without a DOI, unless the recipe's
``[sticker] credit`` replaces those lines; the print sheet (and the SVG metadata) always keeps
every credit's full citation, license and acknowledgement (constitution IV).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from ..datasets.registry import DatasetEntry
from ..maps.recipe import Recipe


@dataclass(frozen=True)
class Credit:
    dataset: str
    version: str
    text: str
    title: str
    doi: Optional[str]
    publisher: str
    citation: str
    license: str
    acknowledgement: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"dataset": self.dataset, "version": self.version, "text": self.text,
                               "title": self.title, "doi": self.doi, "publisher": self.publisher,
                               "citation": self.citation, "license": self.license}
        if self.acknowledgement:
            out["acknowledgement"] = self.acknowledgement
        return out


def credit_text(entry: DatasetEntry) -> str:
    """"<title>, doi:<doi>", else "<title>, <publisher>" (the id when an entry has no title)."""
    title = entry.title or entry.id
    if entry.doi:
        return f"{title}, doi:{entry.doi}"
    return f"{title}, {entry.publisher}" if entry.publisher else title


def credit(entry: DatasetEntry) -> Credit:
    return Credit(dataset=entry.id, version=entry.version, text=credit_text(entry),
                  title=entry.title or entry.id, doi=entry.doi or None, publisher=entry.publisher,
                  citation=entry.citation, license=entry.license,
                  acknowledgement=entry.acknowledgement or None)


def credits_for(recipe: Recipe, template_dataset: Optional[DatasetEntry] = None) -> Tuple[Credit, ...]:
    """The credits of ``recipe``'s datasets, then ``template_dataset`` (non-kit templates), each
    dataset once."""
    entries = list(recipe.datasets())
    if template_dataset is not None:
        entries.append(template_dataset)
    out, seen = [], set()
    for e in entries:
        if e.id in seen:
            continue
        seen.add(e.id)
        out.append(credit(e))
    return tuple(out)


def credit_lines(recipe: Recipe, credits: Sequence[Credit]) -> Tuple[str, ...]:
    """The large sticker's "Data:" lines: the ``[sticker] credit`` when set, else one line per
    credit. The print sheet does not use these; it lists every credit in full."""
    if recipe.sticker is not None and recipe.sticker.credit:
        return (recipe.sticker.credit,)
    return tuple(c.text for c in credits)
