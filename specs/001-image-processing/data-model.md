# Data Model: Satellite Image to LEGO Color Quantization

**Feature**: 001-image-processing
**Phase**: 1 - Data Structures and Models
**Date**: 2026-01-04

## Overview

This document defines the core data structures and models for the LEGO image processing CLI tool. These models represent the entities identified in the feature specification.

---

## 1. LEGO Color Palette Model

### Purpose
Represents the fixed set of LEGO brick colors available in the LEGO World Map kit, used as the target color space for quantization.

### Structure

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class LegoColor:
    """Represents a single LEGO brick color."""

    id: str                      # LEGO color ID (e.g., "221" for Bright Red)
    name: str                    # Human-readable name (e.g., "Bright Red")
    rgb: Tuple[int, int, int]    # RGB values (0-255)
    lab: Tuple[float, float, float]  # LAB color space (pre-computed)
    part_number: str             # LEGO part number reference (e.g., "3024")

    def __str__(self) -> str:
        return f"{self.name} (ID: {self.id})"

@dataclass
class LegoPalette:
    """Collection of all LEGO colors available for quantization."""

    colors: list[LegoColor]
    version: str                 # Palette version for tracking
    source: str                  # Data source (e.g., "LEGO World Map Kit 2024")

    def __len__(self) -> int:
        return len(self.colors)

    def get_by_id(self, color_id: str) -> LegoColor | None:
        """Retrieve color by LEGO ID."""
        for color in self.colors:
            if color.id == color_id:
                return color
        return None

    def get_by_name(self, name: str) -> LegoColor | None:
        """Retrieve color by name (case-insensitive)."""
        name_lower = name.lower()
        for color in self.colors:
            if color.name.lower() == name_lower:
                return color
        return None
```

### JSON Representation

**File**: `cli/src/lego_image_processor/palette/lego_colors.json`

```json
{
  "version": "1.0",
  "source": "LEGO World Map Kit 31203",
  "colors": [
    {
      "id": "1",
      "name": "White",
      "rgb": [242, 243, 242],
      "lab": [96.54, -0.42, 0.58],
      "part_number": "3024"
    },
    {
      "id": "5",
      "name": "Brick Yellow",
      "rgb": [215, 197, 153],
      "lab": [80.12, 0.85, 16.32],
      "part_number": "3024"
    },
    {
      "id": "23",
      "name": "Bright Blue",
      "rgb": [0, 87, 168],
      "lab": [37.54, 18.62, -48.31],
      "part_number": "3024"
    }
  ]
}
```

**Notes**:
- LAB values are pre-computed from RGB using scikit-image's RGB→LAB conversion
- Part number references the specific LEGO brick type used in World Map kit
- Estimated 40-50 colors total in full palette

### Validation Rules
- Each color MUST have unique ID
- RGB values MUST be in range [0, 255]
- LAB values MUST correspond mathematically to RGB values
- Name SHOULD be unique (warn on duplicates, but allow)

---

## 2. Input Image Model

### Purpose
Represents a satellite image file loaded from disk, containing pixel data and metadata.

### Structure

```python
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image as PILImage

@dataclass
class InputImage:
    """Represents a loaded satellite image."""

    file_path: Path              # Original file path
    width: int                   # Image width in pixels
    height: int                  # Image height in pixels
    pixels: np.ndarray           # Pixel data (H × W × 3) as uint8 RGB
    format: str                  # Original format (PNG, JPEG, TIFF)
    color_mode: str              # Original color mode (RGB, RGBA, L, etc.)

    @classmethod
    def from_file(cls, file_path: Path) -> "InputImage":
        """Load image from file path."""
        pil_image = PILImage.open(file_path)

        # Convert to RGB if necessary
        original_mode = pil_image.mode
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Convert to NumPy array
        pixels = np.array(pil_image, dtype=np.uint8)

        return cls(
            file_path=file_path,
            width=pil_image.width,
            height=pil_image.height,
            pixels=pixels,
            format=pil_image.format or "UNKNOWN",
            color_mode=original_mode
        )

    @property
    def megapixels(self) -> float:
        """Calculate megapixels."""
        return (self.width * self.height) / 1_000_000

    @property
    def total_pixels(self) -> int:
        """Total number of pixels."""
        return self.width * self.height

    def __str__(self) -> str:
        return f"{self.file_path.name} ({self.width}×{self.height}, {self.format})"
```

### Validation Rules
- File MUST exist and be readable
- Image dimensions MUST be > 0
- Image size SHOULD be ≤ 100 megapixels (warn/reject for larger)
- Color mode will be converted to RGB if not already
- File format MUST be supported by Pillow (PNG, JPEG, TIFF, etc.)

---

## 3. Quantized Image Model

### Purpose
Represents the output image after color quantization, where all pixels have been mapped to LEGO colors.

### Structure

```python
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image as PILImage

@dataclass
class QuantizedImage:
    """Represents a color-quantized image."""

    width: int                   # Image width (same as input)
    height: int                  # Image height (same as input)
    pixels: np.ndarray           # Quantized pixel data (H × W × 3) as uint8 RGB
    color_indices: np.ndarray    # LEGO color indices for each pixel (H × W)
    source_file: Path            # Original input file path

    @classmethod
    def from_quantization(
        cls,
        input_image: InputImage,
        quantized_pixels: np.ndarray,
        color_indices: np.ndarray
    ) -> "QuantizedImage":
        """Create from quantization process."""
        return cls(
            width=input_image.width,
            height=input_image.height,
            pixels=quantized_pixels,
            color_indices=color_indices,
            source_file=input_image.file_path
        )

    def save(self, output_path: Path, format: str = "PNG") -> None:
        """Save quantized image to file."""
        pil_image = PILImage.fromarray(self.pixels, mode="RGB")
        pil_image.save(output_path, format=format)

    @property
    def total_pixels(self) -> int:
        """Total number of pixels."""
        return self.width * self.height

    def get_unique_colors(self) -> set[int]:
        """Get set of unique LEGO color indices used."""
        return set(self.color_indices.flatten())
```

### Key Properties
- Dimensions MUST match input image exactly (1:1 pixel correspondence)
- Each pixel RGB value MUST exactly match a LEGO color from palette
- Color indices array stores which LEGO color was used for each pixel (for statistics)

---

## 4. Color Statistics Model

### Purpose
Analytical data about color usage in the quantized image, used for P2 user story.

### Structure

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class ColorUsage:
    """Statistics for a single LEGO color's usage."""

    color: LegoColor             # The LEGO color
    pixel_count: int             # Number of pixels using this color
    percentage: float            # Percentage of total pixels (0-100)

    def __str__(self) -> str:
        return f"{self.color.name}: {self.pixel_count:,} pixels ({self.percentage:.2f}%)"

@dataclass
class ColorStatistics:
    """Complete color usage statistics for a quantized image."""

    total_pixels: int            # Total pixels in image
    unique_colors: int           # Number of distinct LEGO colors used
    color_usage: list[ColorUsage]  # Usage stats per color (sorted by frequency)

    @classmethod
    def from_quantized_image(
        cls,
        quantized_image: QuantizedImage,
        palette: LegoPalette
    ) -> "ColorStatistics":
        """Calculate statistics from quantized image."""
        total_pixels = quantized_image.total_pixels

        # Count occurrences of each color index
        color_counts: Dict[int, int] = {}
        for idx in quantized_image.color_indices.flatten():
            color_counts[idx] = color_counts.get(idx, 0) + 1

        # Create ColorUsage entries
        color_usage = []
        for color_idx, count in color_counts.items():
            percentage = (count / total_pixels) * 100
            color_usage.append(ColorUsage(
                color=palette.colors[color_idx],
                pixel_count=count,
                percentage=percentage
            ))

        # Sort by frequency (most common first)
        color_usage.sort(key=lambda cu: cu.pixel_count, reverse=True)

        return cls(
            total_pixels=total_pixels,
            unique_colors=len(color_counts),
            color_usage=color_usage
        )

    def to_json(self) -> dict:
        """Export to JSON-serializable dict."""
        return {
            "total_pixels": self.total_pixels,
            "unique_colors": self.unique_colors,
            "colors": [
                {
                    "id": cu.color.id,
                    "name": cu.color.name,
                    "rgb": list(cu.color.rgb),
                    "part_number": cu.color.part_number,
                    "pixel_count": cu.pixel_count,
                    "percentage": round(cu.percentage, 2)
                }
                for cu in self.color_usage
            ]
        }

    def to_human_readable(self) -> str:
        """Format as human-readable text."""
        lines = [
            f"Total pixels: {self.total_pixels:,}",
            f"Unique colors: {self.unique_colors}",
            "",
            "Color usage (most common first):"
        ]
        for cu in self.color_usage:
            lines.append(f"  - {cu}")
        return "\n".join(lines)
```

### Output Format Examples

**JSON Format** (for `--format json`):
```json
{
  "total_pixels": 1048576,
  "unique_colors": 23,
  "colors": [
    {
      "id": "23",
      "name": "Bright Blue",
      "rgb": [0, 87, 168],
      "part_number": "3024",
      "pixel_count": 312456,
      "percentage": 29.81
    },
    {
      "id": "28",
      "name": "Dark Green",
      "rgb": [40, 127, 70],
      "part_number": "3024",
      "pixel_count": 245789,
      "percentage": 23.44
    }
  ]
}
```

**Human-Readable Format** (default):
```
Total pixels: 1,048,576
Unique colors: 23

Color usage (most common first):
  - Bright Blue: 312,456 pixels (29.81%)
  - Dark Green: 245,789 pixels (23.44%)
  - Brick Yellow: 189,234 pixels (18.05%)
  ...
```

---

## 5. Batch Processing Result Model

### Purpose
Represents the results of processing multiple images (P3 user story).

### Structure

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum

class ProcessingStatus(Enum):
    """Status of individual image processing."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ImageProcessingResult:
    """Result of processing a single image."""

    input_path: Path
    status: ProcessingStatus
    output_path: Optional[Path]  # None if failed
    error_message: Optional[str]  # None if successful
    processing_time: float       # Seconds

    @property
    def succeeded(self) -> bool:
        return self.status == ProcessingStatus.SUCCESS

@dataclass
class BatchProcessingResult:
    """Results of batch processing multiple images."""

    total_images: int
    successful: int
    failed: int
    skipped: int
    results: list[ImageProcessingResult]
    total_time: float            # Total processing time in seconds

    @property
    def success_rate(self) -> float:
        """Percentage of successful processing."""
        if self.total_images == 0:
            return 0.0
        return (self.successful / self.total_images) * 100

    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Processed {self.total_images} images in {self.total_time:.2f}s\n"
            f"Success: {self.successful}, Failed: {self.failed}, Skipped: {self.skipped}\n"
            f"Success rate: {self.success_rate:.1f}%"
        )

    def failed_files(self) -> list[ImageProcessingResult]:
        """Get list of failed processing results."""
        return [r for r in self.results if r.status == ProcessingStatus.FAILED]
```

---

## Data Flow Diagram

```
┌─────────────────┐
│  Input Image    │  ← Load from disk (PNG/JPEG/TIFF)
│  (satellite)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ RGB Pixel Array │  ← NumPy array (H × W × 3)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LAB Pixel Array │  ← Convert RGB → LAB (scikit-image)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LEGO Palette   │  ← Load from JSON (pre-computed LAB)
│  (45 colors)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Color Matching  │  ← Delta E 2000 distance calculation
│ (vectorized)    │     Find closest LEGO color per pixel
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Color Indices   │  ← Array of LEGO color indices (H × W)
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ Quantized Image │  │ Color Stats     │
│ (LEGO colors)   │  │ (usage counts)  │
└────────┬────────┘  └────────┬────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│  Save to PNG    │  │  JSON / Text    │
└─────────────────┘  └─────────────────┘
```

---

## File Format Standards

### LEGO Color Palette JSON
- **Location**: `cli/src/lego_image_processor/palette/lego_colors.json`
- **Encoding**: UTF-8
- **Format**: JSON with indentation (human-readable)
- **Validation**: JSON schema enforced on load

### Output Images
- **Default Format**: PNG (lossless, exact color preservation)
- **Alternative Formats**: JPEG (allowed but warned), TIFF (allowed)
- **Color Mode**: RGB (8-bit per channel)
- **Compression**: PNG default compression (level 6)

### Statistics Output
- **JSON Format**: UTF-8 encoded, indented
- **Text Format**: Plain text, UTF-8, newline-separated

---

## Relationships

```
LegoPalette (1) ──────> (N) LegoColor
     │
     │ used by
     ▼
ColorQuantizer
     │
     │ processes
     ▼
InputImage (1) ──────> (1) QuantizedImage
                             │
                             │ analyzed by
                             ▼
                        ColorStatistics (1) ──────> (N) ColorUsage
```

---

## Memory Considerations

### Estimated Memory Usage

| Image Size | Pixels | Input Array | LAB Array | Indices Array | Total |
|------------|--------|-------------|-----------|---------------|-------|
| 512×512 | 262K | 0.75 MB | 2.0 MB | 0.25 MB | ~3 MB |
| 1024×1024 | 1.0M | 3 MB | 8 MB | 1 MB | ~12 MB |
| 2048×2048 | 4.2M | 12 MB | 32 MB | 4 MB | ~48 MB |
| 3200×3200 | 10.2M | 29 MB | 77 MB | 10 MB | ~116 MB |

**Notes**:
- Input array: H × W × 3 × 1 byte (uint8 RGB)
- LAB array: H × W × 3 × 8 bytes (float64)
- Indices array: H × W × 1 byte (uint8 color index)
- Actual usage will be higher due to Python overhead and intermediate arrays
- Target: <500MB for 10MP images (well within limits)

---

## Validation and Error Handling

### Input Validation
- File existence and readability
- Image format support
- Size limits (warn at 50MP, reject at 100MP)
- Color mode compatibility (auto-convert to RGB)

### Runtime Validation
- Array shape consistency
- Color index bounds checking (index < palette size)
- Output path writability

### Error Recovery
- Graceful handling of corrupted images (skip with error message)
- Batch processing continues on individual failures
- Clear error messages with actionable guidance
