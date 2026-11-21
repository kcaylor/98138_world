# Quick Start Guide: LEGO Image Processor

**Feature**: Satellite Image to LEGO Color Palette Conversion
**Version**: 1.0.0
**Date**: 2026-01-04

## Overview

The LEGO Image Processor is a command-line tool that converts satellite images to LEGO World Map compatible color palettes. It quantizes image colors to match available LEGO brick colors, enabling you to preview and plan custom LEGO maps.

## Installation

### Requirements

- Python 3.11 or higher
- pip (Python package installer)
- 500MB free disk space (for dependencies)
- Modern operating system (Windows 10+, macOS 11+, Linux)

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/98138_world.git
cd 98138_world

# Navigate to CLI directory
cd cli

# Install with Poetry (recommended)
poetry install

# Or install with pip (alternative)
pip install -e .

# Verify installation
lego-image-processor --version
```

### Install from PyPI (Future Release)

```bash
# Once published to PyPI
pip install lego-image-processor

# Verify installation
lego-image-processor --version
```

## Quick Examples

### 1. Basic Image Quantization (P1 - MVP)

Convert a satellite image to LEGO colors:

```bash
# Simplest usage - quantize an image
lego-image-processor quantize my_satellite.png

# Output: my_satellite_quantized.png
```

**What this does:**
- Loads `my_satellite.png`
- Maps each pixel to the closest LEGO brick color
- Saves result as `my_satellite_quantized.png`
- Displays processing time and colors used

**Example output:**
```
✓ Quantized image saved to: my_satellite_quantized.png
  Processing time: 3.45 seconds
  Image size: 1024×1024 (1.05 MP)
  Colors used: 23 of 45 LEGO colors
```

### 2. Custom Output Path

Specify where to save the quantized image:

```bash
lego-image-processor quantize input.jpg --output lego_map.png
```

### 3. Verbose Progress

See detailed progress for large images:

```bash
lego-image-processor quantize large_map.tiff --verbose
```

**Example verbose output:**
```
Loading input image: large_map.tiff
  Image size: 2048×2048 (4.19 MP)
  Original format: TIFF
  Color mode: RGB
Loading LEGO color palette...
  Palette loaded: 45 colors (LEGO World Map Kit 31203)
Converting RGB to LAB color space...
Quantizing colors (finding closest LEGO color for each pixel)...
  [████████████████████████████████] 100% (4194304/4194304) ETA: 0s
Saving quantized image...
✓ Quantized image saved to: large_map_quantized.png
  Processing time: 15.2 seconds
  Colors used: 31 of 45 LEGO colors
```

---

### 4. Color Usage Statistics (P2)

Analyze which LEGO colors are used in your map:

```bash
# Human-readable statistics
lego-image-processor stats my_satellite_quantized.png
```

**Example output:**
```
Color Statistics for my_satellite_quantized.png
=====================================

Image size: 1024×1024 (1,048,576 pixels)
Unique colors: 23 of 45 LEGO colors

Color usage (sorted by frequency):
  1. Bright Blue (ID: 23)         312,456 pixels  (29.81%)
  2. Dark Green (ID: 28)          245,789 pixels  (23.44%)
  3. Brick Yellow (ID: 5)         189,234 pixels  (18.05%)
  4. White (ID: 1)                 98,765 pixels   (9.42%)
  5. Tan (ID: 2)                   67,234 pixels   (6.41%)
  ...

Top 5 colors represent 86.13% of the image.
```

### 5. JSON Statistics Output

Get machine-readable statistics for integration:

```bash
# Output as JSON
lego-image-processor stats map_quantized.png --format json

# Save to file
lego-image-processor stats map_quantized.png -f json -o stats.json
```

**Example JSON:**
```json
{
  "image": {
    "file_path": "map_quantized.png",
    "width": 1024,
    "height": 1024,
    "total_pixels": 1048576
  },
  "summary": {
    "unique_colors": 23,
    "total_palette_colors": 45
  },
  "colors": [
    {
      "id": "23",
      "name": "Bright Blue",
      "rgb": [0, 87, 168],
      "part_number": "3024",
      "pixel_count": 312456,
      "percentage": 29.81
    }
  ]
}
```

---

### 6. Batch Processing (P3)

Process multiple images at once:

```bash
# Process all images in a directory
lego-image-processor batch ./satellite_images/

# Output to custom directory
lego-image-processor batch ./input/ --output-dir ./output/

# Process only specific files
lego-image-processor batch ./maps/ --pattern "satellite_*.png"

# Process recursively (include subdirectories)
lego-image-processor batch ./data/ --recursive

# Parallel processing (4 images at once)
lego-image-processor batch ./images/ --parallel 4
```

**Example batch output:**
```
Batch Processing Summary
========================

Input directory: ./satellite_images/
Output directory: ./satellite_images/quantized/
Pattern: *.png

Discovered: 15 images
Processed: 15 images in 47.3 seconds
  Success: 13 (86.7%)
  Failed: 2 (13.3%)
  Skipped: 0

Failed files:
  - corrupted_image.png: Failed to load image (file may be corrupted)
  - too_large.png: Image too large (150.5 MP exceeds 100 MP limit)

Average processing time: 3.15 seconds per image
Total output size: 156.7 MB
```

### 7. Dry Run (Preview)

See what would be processed without actually processing:

```bash
lego-image-processor batch ./images/ --dry-run
```

**Example output:**
```
Dry run mode - no files will be processed

Would process 15 images:
  1. satellite_001.png → quantized/satellite_001_quantized.png
  2. satellite_002.png → quantized/satellite_002_quantized.png
  3. satellite_003.png → quantized/satellite_003_quantized.png
  ...

Run without --dry-run to process these files.
```

---

## Common Workflows

### Workflow 1: Single Image Preview

```bash
# 1. Quantize your satellite image
lego-image-processor quantize my_map.jpg

# 2. View color statistics
lego-image-processor stats my_map_quantized.png

# 3. Open my_map_quantized.png in image viewer to preview
```

### Workflow 2: Batch Processing with Analysis

```bash
# 1. Process all images in directory
lego-image-processor batch ./satellite_collection/ --verbose

# 2. Generate statistics for each output
for file in ./satellite_collection/quantized/*.png; do
  lego-image-processor stats "$file" -f json -o "${file%.png}_stats.json"
done
```

### Workflow 3: Experimenting with Large Images

```bash
# 1. Check what would be processed (dry run)
lego-image-processor batch ./high_res/ --dry-run

# 2. Process with verbose output to monitor progress
lego-image-processor batch ./high_res/ --verbose --parallel 2

# 3. Review any failures
cat batch_processing_log.txt
```

---

## Supported File Formats

### Input Formats
- **PNG** (.png) - Recommended for lossless quality
- **JPEG** (.jpg, .jpeg) - Common for satellite imagery
- **TIFF** (.tif, .tiff) - High-quality uncompressed format

### Output Formats
- **PNG** (default) - Lossless, preserves exact colors
- **JPEG** - Lossy, may affect color accuracy (warning shown)
- **TIFF** - Lossless, larger file size

**Recommendation:** Always use PNG for output to ensure exact color preservation.

---

## Performance Guidelines

### Expected Processing Times

| Image Size | Pixels | Expected Time | Memory Usage |
|------------|--------|---------------|--------------|
| 512×512 | 262K | 1-3 seconds | <100 MB |
| 1024×1024 | 1.0M | 3-10 seconds | <200 MB |
| 2048×2048 | 4.2M | 10-20 seconds | <500 MB |
| 3200×3200 | 10.2M | 20-30 seconds | <800 MB |

**Note:** Times measured on modern consumer hardware (4-core CPU, 8GB RAM)

### Tips for Faster Processing

1. **Use Parallel Processing for Batches:**
   ```bash
   # Process 4 images simultaneously
   lego-image-processor batch ./images/ --parallel 4
   ```

2. **Downsample Very Large Images:**
   - Images >10 megapixels may be slow
   - Consider resizing before processing for faster previews
   - Final maps rarely need >2048×2048 resolution

3. **Use Quiet Mode for Scripts:**
   ```bash
   # Suppress progress bars in automated workflows
   lego-image-processor quantize input.png --quiet
   ```

---

## Troubleshooting

### Error: "Input file not found"

**Problem:** File path is incorrect or file doesn't exist

**Solution:**
```bash
# Check file exists
ls -l my_image.png

# Use absolute path if needed
lego-image-processor quantize /full/path/to/my_image.png
```

### Error: "Not a valid image format"

**Problem:** File is not a supported image format

**Solution:**
- Verify file is PNG, JPEG, or TIFF
- Try opening in image editor to check if corrupted
- Convert to PNG using: `convert input.file output.png` (ImageMagick)

### Warning: "Image too large"

**Problem:** Image exceeds 100 megapixel limit

**Solution:**
```bash
# Downsample using ImageMagick
convert large_image.png -resize 50% smaller_image.png

# Then process the smaller image
lego-image-processor quantize smaller_image.png
```

### Warning: "Input image is grayscale"

**Info:** Tool automatically converts grayscale to RGB

**No action needed** - processing will continue normally

### Slow Processing

**Problem:** Image takes longer than expected

**Solutions:**
1. Check image size: `identify image.png` (ImageMagick)
2. Use `--verbose` to see progress
3. Consider downsampling large images
4. Use `--parallel` for batch processing

---

## Command Reference

### Global Options

```bash
--help, -h          Show help message
--version           Show version information
```

### quantize Command

```bash
lego-image-processor quantize INPUT [OPTIONS]

Arguments:
  INPUT               Path to input satellite image

Options:
  -o, --output PATH   Output file path (default: {input}_quantized.png)
  -f, --format FORMAT Output format: png, jpeg, tiff (default: png)
  -p, --palette PATH  Custom LEGO palette JSON file (default: built-in)
  -v, --verbose       Show detailed progress
  -q, --quiet         Suppress all output except errors
```

### stats Command

```bash
lego-image-processor stats INPUT [OPTIONS]

Arguments:
  INPUT               Path to quantized image

Options:
  -f, --format FORMAT Output format: text, json (default: text)
  -o, --output PATH   Save statistics to file (default: stdout)
  -p, --palette PATH  LEGO palette JSON file (must match quantization)
  -s, --sort-by SORT  Sort order: frequency, name, color_id (default: frequency)
```

### batch Command

```bash
lego-image-processor batch INPUT_DIR [OPTIONS]

Arguments:
  INPUT_DIR             Directory containing images

Options:
  -o, --output-dir PATH Output directory (default: {input_dir}/quantized)
  -f, --format FORMAT   Output format: png, jpeg, tiff (default: png)
  -p, --pattern GLOB    File pattern to match (default: *.{png,jpg,jpeg,tiff,tif})
  -r, --recursive       Process subdirectories recursively
  --parallel N          Process N images in parallel (default: 1)
  -c, --continue-on-error  Continue if one image fails (default: true)
  --fail-fast           Stop on first error
  -n, --dry-run         Preview without processing
  -v, --verbose         Show detailed progress
```

---

## Next Steps

1. **Try the MVP:** Start with `quantize` command to see your first LEGO map preview
2. **Analyze Colors:** Use `stats` command to understand color distribution
3. **Process Multiple Maps:** Use `batch` command for efficiency
4. **Integrate with Workflow:** Use JSON output for automated pipelines
5. **Contribute:** Report issues or contribute at [github.com/yourusername/98138_world](https://github.com/yourusername/98138_world)

---

## Additional Resources

- **LEGO World Map Kit:** [LEGO Set 31203](https://www.lego.com/product/world-map-31203)
- **Project Documentation:** [./README.md](../../cli/README.md)
- **Contributing Guide:** [./CONTRIBUTING.md](../../cli/CONTRIBUTING.md)
- **License:** MIT (see [LICENSE](../../cli/LICENSE))
- **Issue Tracker:** [GitHub Issues](https://github.com/yourusername/98138_world/issues)

---

## Legal Notice

This tool is **not affiliated with or endorsed by The LEGO Group**. LEGO® is a trademark of the LEGO Group of companies which does not sponsor, authorize or endorse this software.

The tool uses the LEGO World Map kit color palette as a reference for educational and personal use. Users are responsible for ensuring their use of generated maps complies with LEGO's intellectual property rights.
