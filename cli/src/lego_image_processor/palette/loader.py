"""LEGO color palette loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class LegoColor:
    """Represents a single LEGO color."""

    id: int
    name: str
    rgb: Tuple[int, int, int]
    hex: str

    @classmethod
    def from_dict(cls, data: dict) -> LegoColor:
        """Create a LegoColor from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            rgb=tuple(data["rgb"]),
            hex=data["hex"]
        )


class LegoPalette:
    """LEGO color palette manager."""

    def __init__(self, colors: List[LegoColor]):
        """Initialize with a list of LEGO colors."""
        self._colors = colors
        self._color_by_id = {c.id: c for c in colors}
        self._color_by_name = {c.name.lower(): c for c in colors}

    @classmethod
    def load_default(cls) -> LegoPalette:
        """Load the default LEGO color palette."""
        palette_path = Path(__file__).parent / "lego_colors.json"
        return cls.load_from_file(palette_path)

    @classmethod
    def load_from_file(cls, path: Path) -> LegoPalette:
        """Load a LEGO color palette from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        colors = [LegoColor.from_dict(c) for c in data["colors"]]
        return cls(colors)

    @property
    def colors(self) -> List[LegoColor]:
        """Get all colors in the palette."""
        return list(self._colors)

    def __len__(self) -> int:
        """Return the number of colors in the palette."""
        return len(self._colors)

    def __iter__(self):
        """Iterate over colors."""
        return iter(self._colors)

    def get_by_id(self, color_id: int) -> LegoColor | None:
        """Get a color by its ID."""
        return self._color_by_id.get(color_id)

    def get_by_name(self, name: str) -> LegoColor | None:
        """Get a color by its name (case-insensitive)."""
        return self._color_by_name.get(name.lower())

    def get_rgb_array(self) -> List[Tuple[int, int, int]]:
        """Get all RGB values as a list of tuples."""
        return [c.rgb for c in self._colors]
