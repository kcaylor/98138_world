"""Color statistics analysis."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PIL import Image

from ..palette.loader import LegoColor, LegoPalette


@dataclass
class ColorStatistics:
    """Statistics about colors in an image."""

    total_pixels: int
    unique_colors: int
    color_counts: Counter
    lego_colors_found: int
    lego_coverage_percent: float

    def get_top_colors(self, n: int = 10) -> List[Tuple[Tuple[int, int, int], int]]:
        """Get the top N most common colors."""
        return self.color_counts.most_common(n)

    def is_fully_lego(self) -> bool:
        """Check if all colors in the image are LEGO colors."""
        return self.lego_coverage_percent >= 99.99


def analyze_image(
    image: Image.Image,
    palette: LegoPalette | None = None
) -> ColorStatistics:
    """Analyze color statistics of an image.

    Args:
        image: PIL Image to analyze
        palette: LEGO palette for comparison (loads default if None)

    Returns:
        ColorStatistics with analysis results
    """
    if palette is None:
        palette = LegoPalette.load_default()

    # Convert to RGB if needed
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Get pixel data
    img_array = np.array(image)
    pixels = img_array.reshape(-1, 3)

    # Count colors
    color_tuples = [tuple(p) for p in pixels]
    color_counts = Counter(color_tuples)

    total_pixels = len(color_tuples)
    unique_colors = len(color_counts)

    # Check LEGO colors
    palette_rgb_set = {tuple(c.rgb) for c in palette.colors}
    lego_colors_found = sum(1 for c in color_counts if c in palette_rgb_set)
    lego_pixel_count = sum(
        count for c, count in color_counts.items() if c in palette_rgb_set
    )

    return ColorStatistics(
        total_pixels=total_pixels,
        unique_colors=unique_colors,
        color_counts=color_counts,
        lego_colors_found=lego_colors_found,
        lego_coverage_percent=lego_pixel_count / total_pixels * 100 if total_pixels > 0 else 0
    )
