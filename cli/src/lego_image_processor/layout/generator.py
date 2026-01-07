"""Layout generator for LEGO World Map position placements."""

from __future__ import annotations

from typing import Dict, Tuple, Optional, Callable

from PIL import Image

from .position import PositionPlacement
from .grid import PositionPlacementGrid
from .land_sea_mask import LandSeaMask
from ..palette.loader import LegoPalette, LegoColor


class LayoutGenerator:
    """Generate LEGO World Map position placement layouts from quantized images.

    Takes a color-quantized image (128x80 pixels with LEGO palette colors) and
    generates a complete building plan with 10,240 positions (3,062 land bricks
    + 7,178 ocean tiles).

    Attributes:
        palette: LEGO color palette for color lookup
        land_sea_mask: Binary land/sea classification mask
    """

    # Expected image dimensions
    EXPECTED_WIDTH = 128
    EXPECTED_HEIGHT = 80

    def __init__(self, palette: LegoPalette, land_sea_mask: LandSeaMask):
        """Initialize layout generator.

        Args:
            palette: LEGO color palette for color lookup
            land_sea_mask: Land/sea mask for part type classification
        """
        self._palette = palette
        self._land_sea_mask = land_sea_mask

        # Build RGB to color lookup for fast validation
        self._rgb_to_color: Dict[Tuple[int, int, int], LegoColor] = {}
        for color in palette.colors:
            self._rgb_to_color[color.rgb] = color

    def generate(
        self,
        image: Image.Image,
        source_filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> PositionPlacementGrid:
        """Generate position placement layout from quantized image.

        Args:
            image: Quantized image (128x80 pixels with LEGO colors)
            source_filename: Original image filename for metadata
            progress_callback: Optional callback(current, total) for progress

        Returns:
            PositionPlacementGrid with all position placements

        Raises:
            ValueError: If image dimensions or colors are invalid
        """
        # Validate image
        self._validate_dimensions(image)
        self._validate_colors(image)

        # Convert image to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Generate positions
        positions = []
        total = self.EXPECTED_WIDTH * self.EXPECTED_HEIGHT

        for y in range(self.EXPECTED_HEIGHT):
            for x in range(self.EXPECTED_WIDTH):
                # Get pixel color
                rgb = image.getpixel((x, y))
                if isinstance(rgb, int):  # Grayscale
                    rgb = (rgb, rgb, rgb)

                # Look up LEGO color
                color = self._rgb_to_color.get(tuple(rgb))
                if color is None:
                    # This shouldn't happen after validation, but handle it
                    raise ValueError(
                        f"Color lookup failed at ({x}, {y}): RGB{rgb}"
                    )

                # Get part type from land/sea mask
                is_land = self._land_sea_mask.is_land(x, y)
                part_type = "brick" if is_land else "tile"
                lego_part_id = "3062b" if is_land else "98138"

                # Create position placement
                position = PositionPlacement(
                    x=x,
                    y=y,
                    color_id=self._make_color_id(color.name),
                    color_name=color.name,
                    lego_color_code=str(color.id),
                    part_type=part_type,
                    lego_part_id=lego_part_id
                )
                positions.append(position)

                # Report progress
                if progress_callback:
                    current = y * self.EXPECTED_WIDTH + x + 1
                    progress_callback(current, total)

        # Create grid
        return PositionPlacementGrid(
            width=self.EXPECTED_WIDTH,
            height=self.EXPECTED_HEIGHT,
            positions=positions,
            source_image=source_filename
        )

    def _validate_dimensions(self, image: Image.Image) -> None:
        """Validate image dimensions match kit specifications.

        Args:
            image: Image to validate

        Raises:
            ValueError: If dimensions don't match 128x80
        """
        if image.width != self.EXPECTED_WIDTH or image.height != self.EXPECTED_HEIGHT:
            raise ValueError(
                f"Image dimensions ({image.width}x{image.height}) don't match "
                f"LEGO World Map kit specifications ({self.EXPECTED_WIDTH}x{self.EXPECTED_HEIGHT}).\n\n"
                f"Suggested fix:\n"
                f"  Resize the image to {self.EXPECTED_WIDTH}x{self.EXPECTED_HEIGHT} pixels using:\n\n"
                f"  lego-image-processor quantize input.png \\\n"
                f"    --output resized.png \\\n"
                f"    --target-width {self.EXPECTED_WIDTH} \\\n"
                f"    --target-height {self.EXPECTED_HEIGHT}"
            )

    def _validate_colors(self, image: Image.Image) -> None:
        """Validate all pixels have valid LEGO palette colors.

        Args:
            image: Image to validate

        Raises:
            ValueError: If any pixel has a non-LEGO color
        """
        # Convert to RGB if needed
        if image.mode != "RGB":
            check_image = image.convert("RGB")
        else:
            check_image = image

        for y in range(image.height):
            for x in range(image.width):
                rgb = check_image.getpixel((x, y))
                if isinstance(rgb, int):  # Grayscale
                    rgb = (rgb, rgb, rgb)

                if tuple(rgb) not in self._rgb_to_color:
                    raise ValueError(
                        f"Invalid color at pixel ({x}, {y})\n"
                        f"RGB value: {rgb}\n"
                        f"This color is not in the LEGO palette reference data.\n\n"
                        f"Possible causes:\n"
                        f"  1. Image was not quantized using lego-image-processor quantize command\n"
                        f"  2. Image file was modified after quantization\n"
                        f"  3. Image uses a custom color palette\n\n"
                        f"Solution:\n"
                        f"  Re-run quantization to convert all colors to LEGO palette:\n\n"
                        f"  lego-image-processor quantize input.png \\\n"
                        f"    --output quantized.png \\\n"
                        f"    --target-width 128 \\\n"
                        f"    --target-height 80"
                    )

    @staticmethod
    def _make_color_id(color_name: str) -> str:
        """Convert color name to color_id format.

        Args:
            color_name: Human-readable color name (e.g., "Medium Blue")

        Returns:
            Color ID string (e.g., "lego_medium_blue")
        """
        # Convert to lowercase and replace spaces with underscores
        normalized = color_name.lower().replace(" ", "_").replace("-", "_")
        return f"lego_{normalized}"
