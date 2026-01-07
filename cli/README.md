# LEGO Image Processor

A CLI tool that converts images to LEGO-compatible color palettes and generates buildable LEGO World Map layouts.

## Features

- Convert images to use only official LEGO brick colors
- Delta E 2000 (CIEDE2000) color matching algorithm for accurate color reproduction
- Support for PNG, JPEG, and TIFF image formats
- Color statistics and analysis
- Batch processing for multiple images
- **LEGO World Map Layout Generation** (128×80 grid = 10,240 positions)
- **Kit Inventory Validation** against LEGO World Map kit 31203

## Installation

```bash
cd cli
poetry install
```

## Usage

### Image Quantization

```bash
# Quantize a single image to LEGO colors
lego-image-processor quantize input.png -o output.png

# Get color statistics
lego-image-processor stats output.png

# Batch process multiple images
lego-image-processor batch input_dir/ -o output_dir/
```

### Layout Generation

Generate LEGO World Map layouts from quantized images:

```bash
# Generate JSON layout from quantized image
lego-image-processor layout quantized.png -o layout.json

# Generate CSV layout
lego-image-processor layout quantized.png -o layout.csv -f csv

# Quiet mode (minimal output)
lego-image-processor layout quantized.png -o layout.json -q
```

The layout command:
- Requires a 128×80 pixel quantized image
- Uses the official LEGO World Map land/sea mask
- Outputs position-by-position placement instructions
- Distinguishes land positions (round 1×1 bricks, part 3062b) from ocean positions (flat 1×1 tiles, part 98138)

### Layout Validation

Validate layouts against LEGO World Map kit inventory:

```bash
# Validate a layout
lego-image-processor validate layout.json

# Save validation report to file
lego-image-processor validate layout.json -o report.json

# Validate against specific kit
lego-image-processor validate layout.json --kit 31203
```

The validate command checks:
- Color availability (whether colors are available for bricks/tiles in the kit)
- Quantity limits (whether color quantities exceed kit inventory)
- Provides buildability score (percentage of positions buildable)
- Suggests alternative colors for unavailable ones

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/lego_image_processor
```
