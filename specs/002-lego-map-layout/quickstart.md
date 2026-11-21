# Quickstart Guide: LEGO Map Layout Generation

**Feature**: 002-lego-map-layout
**Date**: 2026-01-07
**Purpose**: Integration scenarios and usage examples for position layout generation

## Overview

This guide provides practical integration scenarios showing how to use the LEGO map layout generation tool to transform color-quantized images into buildable LEGO World Map position placement layouts matching the official kit 31203 structure.

**What this tool does**: Converts a 128×80 pixel quantized image into a complete building plan with 10,240 positions (3,062 land bricks + 7,178 ocean tiles), where each pixel becomes one LEGO part with the corresponding color and part type (brick or tile) determined by the official kit's land/sea mask.

---

## Prerequisites

Before using the layout generation tool, ensure you have:

1. **Quantized image** (output from spec 001 image processing):
   - Dimensions: 128×80 pixels (exactly matches kit 31203 specifications)
   - Colors: Only LEGO palette colors (no arbitrary RGB values)
   - Format: PNG, JPEG, or TIFF

2. **Land/sea mask** (automatically loaded from fixtures):
   - File: `cli/tests/fixtures/lego_world_map_land_sea_mask.json`
   - Contains official kit 31203 land/sea pattern (3,062 land, 7,178 ocean)

3. **LEGO kit configuration** (for P2 validation):
   - File: `cli/src/lego_image_processor/data/lego_world_map_kit.json`
   - Defines available colors and quantities for bricks and tiles

---

## Integration Scenario 1: Basic Position Layout Generation (P1)

### Goal
Convert a color-quantized satellite image into a complete LEGO World Map building plan with position placements for all 10,240 positions.

### Input
- Quantized image: `natural_earth_ii_quantized.png` (128×80 pixels)
- Output format: JSON
- Output file: `layout.json`

### Command
```bash
lego-image-processor layout natural_earth_ii_quantized.png \
  --output layout.json \
  --format json
```

### Expected Output (stdout)
```
Loading quantized image: natural_earth_ii_quantized.png
  Image dimensions: 128×80 pixels
  Total pixels: 10,240

Validating image...
  ✓ Dimensions match kit specifications (128×80)
  ✓ All pixels contain valid LEGO colors

Loading land/sea mask...
  ✓ Mask loaded: 3,062 land positions, 7,178 ocean positions

Generating position placements...
  Progress: [====================] 10,240/10,240 positions

Layout generation complete!
  Total positions: 10,240
  Land bricks (3062b): 3,062 (29.9%)
  Ocean tiles (98138): 7,178 (70.1%)
  Unique colors: 12
  Output: layout.json

Build statistics:
  Most common color: Medium Blue (2,400 positions, 23.4%)
  Land brick colors: 8 distinct colors
  Ocean tile colors: 9 distinct colors
```

### Output File Structure (layout.json)
```json
{
  "metadata": {
    "width": 128,
    "height": 80,
    "total_positions": 10240,
    "land_positions": 3062,
    "ocean_positions": 7178,
    "unique_colors": 12,
    "generated_at": "2026-01-07T14:30:00Z",
    "source_image": "natural_earth_ii_quantized.png",
    "schema_version": "1.0",
    "coordinate_system": "top_left_origin"
  },
  "positions": [
    {
      "x": 0,
      "y": 0,
      "color_id": "lego_blue_medium",
      "color_name": "Medium Blue",
      "lego_color_code": "102",
      "part_type": "tile",
      "lego_part_id": "98138"
    },
    // ... 10,239 more positions
  ],
  "statistics": {
    "total_tile_count": 10240,
    "land_brick_count": 3062,
    "ocean_tile_count": 7178,
    "unique_colors": 12,
    "color_frequency": {
      "lego_blue_medium": 2400,
      "lego_green": 1850,
      // ... other colors
    },
    "color_frequency_by_part_type": {
      "brick": {
        "lego_green": 1500,
        "lego_tan": 800
      },
      "tile": {
        "lego_blue_medium": 2400,
        "lego_blue_dark": 1200
      }
    }
  }
}
```

### Next Steps
- Use layout.json as input for parts list generation (future spec)
- Use layout.json as input for building instruction generation (future spec)
- Validate layout against kit inventory (Scenario 2, P2)

---

## Integration Scenario 2: CSV Output for Spreadsheet Analysis (P1)

### Goal
Generate position layout in CSV format for manual inspection in spreadsheet tools (Excel, Google Sheets, etc.).

### Input
- Quantized image: `temperature_anomaly_quantized.png` (128×80 pixels)
- Output format: CSV
- Output file: `layout.csv`

### Command
```bash
lego-image-processor layout temperature_anomaly_quantized.png \
  --output layout.csv \
  --format csv
```

### Expected Output (stdout)
```
Loading quantized image: temperature_anomaly_quantized.png
  Image dimensions: 128×80 pixels
  Total pixels: 10,240

Validating image...
  ✓ Dimensions match kit specifications (128×80)
  ✓ All pixels contain valid LEGO colors

Loading land/sea mask...
  ✓ Mask loaded: 3,062 land positions, 7,178 ocean positions

Generating position placements...
  Progress: [====================] 10,240/10,240 positions

Layout generation complete!
  Total positions: 10,240
  Land bricks (3062b): 3,062 (29.9%)
  Ocean tiles (98138): 7,178 (70.1%)
  Unique colors: 8
  Output: layout.csv
```

### Output File Structure (layout.csv)
```csv
x_position,y_position,color_id,color_name,lego_color_code,part_type,lego_part_id
0,0,lego_blue_medium,Medium Blue,102,tile,98138
0,1,lego_blue_medium,Medium Blue,102,tile,98138
1,0,lego_blue_dark,Dark Blue,140,tile,98138
1,1,lego_green,Green,28,brick,3062b
2,0,lego_blue_medium,Medium Blue,102,tile,98138
...
```

### Usage in Spreadsheet
```
1. Open layout.csv in Excel or Google Sheets
2. Apply filters to columns (e.g., filter by part_type="brick" to see land positions)
3. Create pivot tables to analyze color distribution
4. Sort by color_id to group positions by color for parts counting
5. Use conditional formatting to visualize color patterns
```

---

## Integration Scenario 3: Programmatic Layout Generation (P1)

### Goal
Use the layout generation tool as a Python library within a larger workflow (e.g., batch processing multiple datasets).

### Python Code
```python
from lego_image_processor.layout.generator import LayoutGenerator
from lego_image_processor.layout.land_sea_mask import load_land_sea_mask
from lego_image_processor.core.image_loader import ImageLoader
from lego_image_processor.palette.loader import PaletteLoader

# Load dependencies
image_loader = ImageLoader()
palette_loader = PaletteLoader()
land_sea_mask = load_land_sea_mask()

# Initialize generator
generator = LayoutGenerator(
    palette=palette_loader.load(),
    land_sea_mask=land_sea_mask
)

# Load quantized image
image = image_loader.load("ocean_currents_quantized.png")

# Generate layout
layout_grid = generator.generate(image, source_filename="ocean_currents_quantized.png")

# Access layout data programmatically
print(f"Total positions: {layout_grid.total_positions}")
print(f"Land bricks: {layout_grid.land_positions}")
print(f"Ocean tiles: {layout_grid.ocean_positions}")
print(f"Unique colors: {layout_grid.unique_colors}")

# Iterate over positions
for position in layout_grid.positions:
    if position.part_type == "brick":
        print(f"Land brick at ({position.x}, {position.y}): {position.color_name}")

# Export to JSON
layout_grid.to_json("layout.json")

# Export to CSV
layout_grid.to_csv("layout.csv")
```

### Output
```
Total positions: 10240
Land bricks: 3062
Ocean tiles: 7178
Unique colors: 10
Land brick at (45, 25): Green
Land brick at (46, 25): Tan
Land brick at (47, 25): Brown
...
Layout exported to: layout.json
Layout exported to: layout.csv
```

---

## Integration Scenario 4: End-to-End Workflow from Raw Image (P1)

### Goal
Complete workflow: raw satellite image → quantized image → position layout

### Step 1: Quantize Raw Image (Spec 001)
```bash
# Input: raw satellite image (any size, any colors)
# Output: quantized image (128×80 pixels, LEGO colors only)
lego-image-processor quantize raw_image.png \
  --output quantized.png \
  --target-width 128 \
  --target-height 80 \
  --colors 12 \
  --method kmeans
```

### Step 2: Generate Position Layout (Spec 002)
```bash
# Input: quantized image (from step 1)
# Output: position placement layout
lego-image-processor layout quantized.png \
  --output layout.json \
  --format json
```

### Step 3: Inspect Results
```bash
# View layout summary
cat layout.json | jq '.metadata'

# Count positions by part type
cat layout.json | jq '.positions | group_by(.part_type) | map({part_type: .[0].part_type, count: length})'

# List unique colors
cat layout.json | jq '.statistics.color_frequency | keys'
```

### Expected Output (Step 3)
```json
// Metadata
{
  "width": 128,
  "height": 80,
  "total_positions": 10240,
  "land_positions": 3062,
  "ocean_positions": 7178,
  "unique_colors": 12
}

// Positions by part type
[
  {"part_type": "brick", "count": 3062},
  {"part_type": "tile", "count": 7178}
]

// Unique colors
[
  "lego_blue_dark",
  "lego_blue_medium",
  "lego_brown",
  "lego_green",
  "lego_green_dark",
  "lego_orange",
  "lego_red",
  "lego_tan",
  "lego_white",
  "lego_yellow"
]
```

---

## Integration Scenario 5: Kit Color Validation (P2)

### Goal
Validate a generated layout against the official LEGO World Map kit 31203 inventory to ensure buildability with standard kit parts.

### Input
- Layout file: `layout.json` (from Scenario 1)
- Kit specification: `lego_world_map_kit.json` (automatically loaded)

### Command
```bash
lego-image-processor validate layout.json \
  --kit 31203 \
  --output validation_report.json
```

### Expected Output (stdout) - Buildable Layout
```
Loading layout: layout.json
  Total positions: 10,240
  Land bricks: 3,062
  Ocean tiles: 7,178
  Unique colors: 12

Loading kit specification: 31203 (LEGO World Map)
  Available brick colors: 55
  Available tile colors: 64
  Kit inventory loaded

Validating layout against kit...
  Checking brick colors (8 colors)...
    ✓ All brick colors available in kit
  Checking tile colors (9 colors)...
    ✓ All tile colors available in kit
  Checking color quantities...
    ✓ All color quantities within kit limits

Validation complete!
  Buildability: 100% (FULLY BUILDABLE)
  Violations: 0
  Output: validation_report.json

✓ This layout can be built with the standard LEGO World Map kit (31203)
```

### Expected Output (stdout) - Partial Buildability
```
Loading layout: layout.json
  Total positions: 10,240
  Land bricks: 3,062
  Ocean tiles: 7,178
  Unique colors: 15

Loading kit specification: 31203 (LEGO World Map)
  Available brick colors: 55
  Available tile colors: 64
  Kit inventory loaded

Validating layout against kit...
  Checking brick colors (10 colors)...
    ✗ 2 brick colors unavailable in kit
  Checking tile colors (11 colors)...
    ✗ 1 tile color unavailable in kit
  Checking color quantities...
    ✗ 3 colors exceed kit quantities

Validation complete!
  Buildability: 73% (PARTIALLY BUILDABLE)
  Violations: 6
  Output: validation_report.json

⚠ This layout requires additional parts beyond the standard kit.
  See validation_report.json for details and suggested alternatives.
```

### Output File Structure (validation_report.json)
```json
{
  "buildable": false,
  "buildability_score": 0.73,
  "violations": [
    {
      "type": "color_unavailable",
      "part_type": "brick",
      "part_id": "3062b",
      "color_id": "lego_purple_bright",
      "color_name": "Bright Purple",
      "positions_required": 47,
      "suggested_alternative": {
        "color_id": "lego_magenta",
        "color_name": "Magenta",
        "color_distance": 12.4
      }
    },
    {
      "type": "quantity_exceeded",
      "part_type": "tile",
      "part_id": "98138",
      "color_id": "lego_blue_medium",
      "color_name": "Medium Blue",
      "positions_required": 2400,
      "kit_quantity": 1500,
      "shortfall": 900
    }
  ],
  "validated_at": "2026-01-07T15:00:00Z",
  "kit_id": "31203",
  "layout_file": "layout.json"
}
```

### Interpreting Validation Results

**Color Unavailable Violation**:
- Meaning: Layout requires a color that doesn't exist in the kit for the specified part type
- Action: Use suggested alternative color, or source additional parts from LEGO/BrickLink
- Example: Layout needs Bright Purple bricks, but kit only has Magenta bricks (Delta E distance: 12.4)

**Quantity Exceeded Violation**:
- Meaning: Layout requires more parts of a color than the kit provides
- Action: Source additional parts, or modify quantization to use fewer tiles of that color
- Example: Layout needs 2,400 Medium Blue tiles, but kit only includes 1,500 (shortfall: 900)

**Buildability Score**:
- Calculation: (buildable positions) / (total positions)
- 100%: Fully buildable with standard kit
- 50-99%: Partially buildable, requires additional parts
- 0-49%: Significantly incompatible with standard kit

---

## Integration Scenario 6: Batch Processing Multiple Datasets (P1)

### Goal
Process multiple satellite datasets in a batch workflow to generate layouts for different global phenomena (temperature, precipitation, NPP, etc.).

### Bash Script
```bash
#!/bin/bash
# batch_generate_layouts.sh

datasets=(
  "temperature_anomaly"
  "net_primary_productivity"
  "ocean_currents"
  "population_density"
  "plate_tectonics"
)

for dataset in "${datasets[@]}"; do
  echo "Processing dataset: $dataset"

  # Step 1: Quantize raw image
  lego-image-processor quantize "raw/${dataset}.png" \
    --output "quantized/${dataset}_quantized.png" \
    --target-width 128 \
    --target-height 80 \
    --colors 12 \
    --method kmeans

  # Step 2: Generate layout
  lego-image-processor layout "quantized/${dataset}_quantized.png" \
    --output "layouts/${dataset}_layout.json" \
    --format json

  # Step 3: Validate against kit
  lego-image-processor validate "layouts/${dataset}_layout.json" \
    --kit 31203 \
    --output "validation/${dataset}_validation.json"

  echo "✓ Completed: $dataset"
  echo ""
done

echo "Batch processing complete!"
echo "Generated layouts: $(ls layouts/*.json | wc -l)"
echo "Validation reports: $(ls validation/*.json | wc -l)"
```

### Output
```
Processing dataset: temperature_anomaly
  ✓ Quantized: quantized/temperature_anomaly_quantized.png
  ✓ Layout generated: layouts/temperature_anomaly_layout.json
  ✓ Validation complete: validation/temperature_anomaly_validation.json
✓ Completed: temperature_anomaly

Processing dataset: net_primary_productivity
  ✓ Quantized: quantized/net_primary_productivity_quantized.png
  ✓ Layout generated: layouts/net_primary_productivity_layout.json
  ✓ Validation complete: validation/net_primary_productivity_validation.json
✓ Completed: net_primary_productivity

...

Batch processing complete!
Generated layouts: 5
Validation reports: 5
```

---

## Integration Scenario 7: Error Handling - Dimension Mismatch (P1)

### Goal
Understand how the tool handles images with incorrect dimensions and how to fix them.

### Input
- Quantized image: `wrong_size.png` (100×50 pixels - incorrect dimensions)

### Command
```bash
lego-image-processor layout wrong_size.png \
  --output layout.json \
  --format json
```

### Expected Output (error)
```
Loading quantized image: wrong_size.png
  Image dimensions: 100×50 pixels
  Total pixels: 5,000

Validating image...
  ✗ Dimension mismatch!

ERROR: Image dimensions (100×50) don't match LEGO World Map kit specifications.

Expected dimensions: 128×80 pixels (official kit 31203)
Received dimensions: 100×50 pixels

Suggested fix:
  Resize the image to 128×80 pixels using one of these methods:

  Method 1: Using lego-image-processor (recommended)
    lego-image-processor quantize wrong_size.png \
      --output resized.png \
      --target-width 128 \
      --target-height 80

  Method 2: Using Pillow (Python)
    from PIL import Image
    img = Image.open('wrong_size.png')
    img.resize((128, 80), Image.Resampling.LANCZOS).save('resized.png')

  Method 3: Using ImageMagick (command line)
    convert wrong_size.png -resize 128x80! resized.png

Layout generation aborted.
```

### Resolution
```bash
# Resize the image
lego-image-processor quantize wrong_size.png \
  --output correct_size.png \
  --target-width 128 \
  --target-height 80

# Retry layout generation
lego-image-processor layout correct_size.png \
  --output layout.json \
  --format json
```

---

## Integration Scenario 8: Error Handling - Invalid Colors (P1)

### Goal
Understand how the tool handles images with non-LEGO colors (indicating upstream quantization failure).

### Input
- Image: `not_quantized.png` (128×80 pixels, but contains arbitrary RGB colors)

### Command
```bash
lego-image-processor layout not_quantized.png \
  --output layout.json \
  --format json
```

### Expected Output (error)
```
Loading quantized image: not_quantized.png
  Image dimensions: 128×80 pixels
  Total pixels: 10,240

Validating image...
  ✓ Dimensions match kit specifications (128×80)
  ✗ Invalid color detected!

ERROR: Invalid color at pixel (42, 17)
RGB value: (127, 84, 200)
This color is not in the LEGO palette reference data.

Possible causes:
  1. Image was not quantized using lego-image-processor quantize command
  2. Image file was modified after quantization
  3. Image uses a custom color palette

Solution:
  Re-run quantization to convert all colors to LEGO palette:

  lego-image-processor quantize not_quantized.png \
    --output quantized.png \
    --target-width 128 \
    --target-height 80 \
    --colors 12

  Then generate layout from quantized image:

  lego-image-processor layout quantized.png \
    --output layout.json

Layout generation aborted.
```

### Resolution
```bash
# Quantize the image first
lego-image-processor quantize not_quantized.png \
  --output quantized.png \
  --target-width 128 \
  --target-height 80 \
  --colors 12

# Generate layout from quantized image
lego-image-processor layout quantized.png \
  --output layout.json \
  --format json
```

---

## Integration with Downstream Tools (Future Specs)

The position layout files generated by this tool serve as input for downstream tools:

### 1. Parts List Generator (Future Spec 003)
```bash
# Input: layout.json
# Output: parts_list.json (grouped by part type and color)
lego-image-processor parts layout.json \
  --output parts_list.json
```

Expected parts list structure:
```json
{
  "kit_id": "31203",
  "total_parts": 10240,
  "parts_by_type": {
    "brick_3062b": [
      {"color_id": "lego_green", "color_name": "Green", "quantity": 1500},
      {"color_id": "lego_tan", "color_name": "Tan", "quantity": 800}
    ],
    "tile_98138": [
      {"color_id": "lego_blue_medium", "color_name": "Medium Blue", "quantity": 2400},
      {"color_id": "lego_blue_dark", "color_name": "Dark Blue", "quantity": 1200}
    ]
  }
}
```

### 2. Building Instructions Generator (Future Spec 004)
```bash
# Input: layout.json
# Output: instructions.pdf (step-by-step building guide)
lego-image-processor instructions layout.json \
  --output instructions.pdf \
  --format pdf
```

Expected instructions structure:
```
Step 1: Place base plates (40 plates in 8×5 grid)
Step 2: Build ocean tiles row by row (rows 0-9)
Step 3: Build land/ocean mix (rows 10-39)
Step 4: Build northern region (rows 40-79)
Step 5: Add frame elements
```

### 3. Web UI Integration (Future Backend Spec)
```python
# FastAPI endpoint example
@app.post("/api/generate-layout")
async def generate_layout(quantized_image: UploadFile):
    # Save uploaded image
    image_path = save_temp_file(quantized_image)

    # Call CLI tool as subprocess
    result = subprocess.run([
        "lego-image-processor", "layout", image_path,
        "--output", "layout.json",
        "--format", "json"
    ], capture_output=True)

    # Load and return layout
    with open("layout.json") as f:
        layout_data = json.load(f)

    return {"layout": layout_data, "status": "success"}
```

---

## Performance Benchmarks

Based on SC-001 and SC-003 from spec.md:

| Image Size | Total Positions | Processing Time | Memory Usage |
|------------|----------------|-----------------|--------------|
| 128×80     | 10,240         | <1 second       | <10 MB       |
| 256×160    | 40,960         | <3 seconds      | <30 MB       |
| 512×320    | 163,840        | <10 seconds     | <100 MB      |

**Expected performance** (standard 128×80 map):
- Image loading: <0.1s
- Dimension validation: <0.01s
- Land/sea mask loading: <0.01s (cached)
- Position generation: <0.5s (linear time, O(n) where n=10,240)
- Statistics computation: <0.1s
- JSON serialization: <0.2s
- **Total**: <1 second (well under 5-second target from SC-001)

---

## Troubleshooting

### Issue: "Layout generation is slow"
**Cause**: Large image size or inefficient color lookup
**Solution**:
```bash
# Profile the tool
python -m cProfile -o profile.stats lego_image_processor/cli/layout.py input.png

# Analyze profile
python -m pstats profile.stats
> sort cumtime
> stats 20
```

### Issue: "Validation reports too many violations"
**Cause**: Quantization used too many colors or colors unavailable in kit
**Solution**:
```bash
# Re-quantize with fewer colors and palette restriction
lego-image-processor quantize raw.png \
  --output quantized.png \
  --colors 8 \
  --restrict-to-kit 31203 \
  --target-width 128 \
  --target-height 80
```

### Issue: "CSV output is too large to open in Excel"
**Cause**: Excel has row limit (~1 million rows), layout has 10,240 rows (well within limit)
**Solution**: This shouldn't happen for standard layouts. If it does, use JSON format instead:
```bash
lego-image-processor layout input.png --output layout.json --format json
```

---

## Additional Resources

**Official LEGO World Map Kit**:
- Kit number: 31203
- LEGO website: https://www.lego.com/product/world-map-31203
- Instruction manual: https://www.lego.com/service/buildinginstructions/31203

**LEGO Part Reference**:
- Part 3062b (Brick Round 1×1 Open Stud): https://www.bricklink.com/v2/catalog/catalogitem.page?P=3062b
- Part 98138 (Tile Round 1×1): https://www.bricklink.com/v2/catalog/catalogitem.page?P=98138

**Community Resources**:
- Rebrickable: https://rebrickable.com/sets/31203-1/world-map/
- BrickLink: https://www.bricklink.com/v2/catalog/catalogitem.page?S=31203-1

---

## Summary

This quickstart guide covered eight integration scenarios:

1. **Basic layout generation** (JSON output)
2. **CSV output** (spreadsheet analysis)
3. **Programmatic usage** (Python library)
4. **End-to-end workflow** (raw image → layout)
5. **Kit validation** (buildability checking, P2)
6. **Batch processing** (multiple datasets)
7. **Error handling** (dimension mismatch)
8. **Error handling** (invalid colors)

**Key Takeaways**:
- Always quantize images before layout generation (spec 001 → spec 002)
- Standard layouts are 128×80 pixels = 10,240 positions (3,062 land + 7,178 ocean)
- Land positions use round bricks (3062b), ocean positions use flat tiles (98138)
- Validation (P2) checks buildability against official kit 31203 inventory
- Output formats: JSON (machine-readable) or CSV (human-readable)

**Next Steps**:
- Generate parts lists (future spec 003)
- Create building instructions (future spec 004)
- Integrate into web application (future backend spec)
