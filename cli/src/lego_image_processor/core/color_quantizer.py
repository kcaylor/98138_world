"""Color quantization using Delta E 2000 algorithm."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from ..palette.converter import rgb_to_lab
from ..palette.loader import LegoColor, LegoPalette


def delta_e_2000(
    lab1: NDArray[np.float64],
    lab2: NDArray[np.float64],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0
) -> NDArray[np.float64]:
    """Calculate Delta E 2000 color difference.

    Implementation of the CIEDE2000 color difference formula.

    Args:
        lab1: First LAB color(s) with shape (..., 3)
        lab2: Second LAB color(s) with shape (..., 3)
        kL: Lightness weighting factor (default 1.0)
        kC: Chroma weighting factor (default 1.0)
        kH: Hue weighting factor (default 1.0)

    Returns:
        Delta E 2000 value(s)
    """
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]

    # Calculate C1, C2 (chroma)
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_avg = (C1 + C2) / 2

    # Calculate G
    C_avg_7 = C_avg**7
    G = 0.5 * (1 - np.sqrt(C_avg_7 / (C_avg_7 + 25**7)))

    # Adjusted a values
    a1_prime = (1 + G) * a1
    a2_prime = (1 + G) * a2

    # Calculate C' (adjusted chroma)
    C1_prime = np.sqrt(a1_prime**2 + b1**2)
    C2_prime = np.sqrt(a2_prime**2 + b2**2)

    # Calculate h' (hue angle)
    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360

    # Handle zero chroma cases
    h1_prime = np.where((C1_prime == 0), 0, h1_prime)
    h2_prime = np.where((C2_prime == 0), 0, h2_prime)

    # Delta values
    delta_L_prime = L2 - L1
    delta_C_prime = C2_prime - C1_prime

    # Delta h'
    h_diff = h2_prime - h1_prime
    delta_h_prime = np.where(
        (C1_prime * C2_prime) == 0,
        0,
        np.where(
            np.abs(h_diff) <= 180,
            h_diff,
            np.where(h_diff > 180, h_diff - 360, h_diff + 360)
        )
    )

    # Delta H'
    delta_H_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(delta_h_prime / 2))

    # Average values
    L_prime_avg = (L1 + L2) / 2
    C_prime_avg = (C1_prime + C2_prime) / 2

    # Average h'
    h_sum = h1_prime + h2_prime
    h_prime_avg = np.where(
        (C1_prime * C2_prime) == 0,
        h_sum,
        np.where(
            np.abs(h_diff) <= 180,
            h_sum / 2,
            np.where(h_sum < 360, (h_sum + 360) / 2, (h_sum - 360) / 2)
        )
    )

    # T
    T = (1 - 0.17 * np.cos(np.radians(h_prime_avg - 30)) +
         0.24 * np.cos(np.radians(2 * h_prime_avg)) +
         0.32 * np.cos(np.radians(3 * h_prime_avg + 6)) -
         0.20 * np.cos(np.radians(4 * h_prime_avg - 63)))

    # SL, SC, SH
    L_prime_avg_50_sq = (L_prime_avg - 50)**2
    SL = 1 + (0.015 * L_prime_avg_50_sq) / np.sqrt(20 + L_prime_avg_50_sq)
    SC = 1 + 0.045 * C_prime_avg
    SH = 1 + 0.015 * C_prime_avg * T

    # RT
    delta_theta = 30 * np.exp(-((h_prime_avg - 275) / 25)**2)
    C_prime_avg_7 = C_prime_avg**7
    RC = 2 * np.sqrt(C_prime_avg_7 / (C_prime_avg_7 + 25**7))
    RT = -np.sin(np.radians(2 * delta_theta)) * RC

    # Final Delta E 2000
    delta_E = np.sqrt(
        (delta_L_prime / (kL * SL))**2 +
        (delta_C_prime / (kC * SC))**2 +
        (delta_H_prime / (kH * SH))**2 +
        RT * (delta_C_prime / (kC * SC)) * (delta_H_prime / (kH * SH))
    )

    return delta_E


@dataclass
class QuantizationResult:
    """Result of image quantization."""

    image: Image.Image
    color_mapping: dict[Tuple[int, int, int], LegoColor]
    original_colors: int
    mapped_colors: int


class ColorQuantizer:
    """Quantize images to LEGO color palette using Delta E 2000."""

    def __init__(self, palette: LegoPalette | None = None):
        """Initialize the quantizer.

        Args:
            palette: LEGO color palette to use. If None, loads default.
        """
        self.palette = palette or LegoPalette.load_default()
        self._precompute_palette_lab()

    def _precompute_palette_lab(self) -> None:
        """Precompute LAB values for palette colors."""
        rgb_array = np.array([c.rgb for c in self.palette.colors], dtype=np.float64)
        self._palette_lab = rgb_to_lab(rgb_array)
        self._palette_rgb = rgb_array.astype(np.uint8)

    def find_closest_color(self, rgb: Tuple[int, int, int]) -> LegoColor:
        """Find the closest LEGO color to the given RGB value.

        Args:
            rgb: RGB tuple (r, g, b)

        Returns:
            The closest LegoColor
        """
        # Convert input to LAB
        rgb_array = np.array([[rgb]], dtype=np.float64)
        lab = rgb_to_lab(rgb_array)[0, 0]

        # Calculate distance to all palette colors
        distances = delta_e_2000(
            lab.reshape(1, 3),
            self._palette_lab
        )

        # Find closest
        closest_idx = np.argmin(distances)
        return self.palette.colors[closest_idx]

    def quantize(self, image: Image.Image) -> QuantizationResult:
        """Quantize an image to the LEGO color palette.

        Args:
            image: PIL Image to quantize

        Returns:
            QuantizationResult with the quantized image and mapping info
        """
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Get image data as numpy array
        img_array = np.array(image, dtype=np.float64)
        original_shape = img_array.shape

        # Reshape to list of pixels
        pixels = img_array.reshape(-1, 3)

        # Find unique colors for efficiency
        unique_colors, inverse_indices = np.unique(
            pixels.astype(np.uint8),
            axis=0,
            return_inverse=True
        )

        # Convert unique colors to LAB
        unique_lab = rgb_to_lab(unique_colors.astype(np.float64))

        # Find closest palette color for each unique color
        closest_indices = np.zeros(len(unique_colors), dtype=np.int32)

        # Process in batches for memory efficiency
        batch_size = 1000
        for i in range(0, len(unique_colors), batch_size):
            batch_lab = unique_lab[i:i + batch_size]

            # Calculate distances to all palette colors
            # Shape: (batch_size, num_palette_colors)
            distances = np.zeros((len(batch_lab), len(self._palette_lab)))
            for j, lab_color in enumerate(batch_lab):
                distances[j] = delta_e_2000(
                    lab_color.reshape(1, 3),
                    self._palette_lab
                )

            closest_indices[i:i + batch_size] = np.argmin(distances, axis=1)

        # Map unique colors to palette colors
        mapped_rgb = self._palette_rgb[closest_indices]

        # Build color mapping dict
        color_mapping = {}
        for i, unique_color in enumerate(unique_colors):
            rgb_tuple = tuple(unique_color)
            closest_idx = closest_indices[i]
            color_mapping[rgb_tuple] = self.palette.colors[closest_idx]

        # Apply mapping to all pixels
        quantized_pixels = mapped_rgb[inverse_indices]

        # Reshape back to image
        quantized_array = quantized_pixels.reshape(original_shape).astype(np.uint8)
        quantized_image = Image.fromarray(quantized_array, mode="RGB")

        return QuantizationResult(
            image=quantized_image,
            color_mapping=color_mapping,
            original_colors=len(unique_colors),
            mapped_colors=len(set(closest_indices))
        )
