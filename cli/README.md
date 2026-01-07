# LEGO Image Processor

A CLI tool that converts images to LEGO-compatible color palettes using advanced color quantization algorithms.

## Features

- Convert images to use only official LEGO brick colors
- Delta E 2000 (CIEDE2000) color matching algorithm for accurate color reproduction
- Support for PNG, JPEG, and TIFF image formats
- Color statistics and analysis
- Batch processing for multiple images

## Installation

```bash
cd cli
poetry install
```

## Usage

```bash
# Quantize a single image
lego-image-processor quantize input.png -o output.png

# Get color statistics
lego-image-processor stats output.png

# Batch process multiple images
lego-image-processor batch input_dir/ -o output_dir/
```

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/lego_image_processor
```
