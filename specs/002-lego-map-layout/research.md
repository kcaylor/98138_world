# Research: LEGO Map Layout Generation

**Feature**: 002-lego-map-layout
**Date**: 2026-01-07
**Purpose**: Document technical decisions and resolve unknowns for position layout generation

## Research Questions

### 1. LEGO World Map Kit 31203 Exact Specifications

**Question**: What are the exact dimensions, part types, and land/sea pattern of the official LEGO World Map kit?

**Decision**: Use 128×80 grid (10,240 positions) with official land/sea classification pattern

**Rationale**:
- Extracted directly from official LEGO World Map kit 31203 instruction manual (all_plates_in_order.pdf)
- 40 plates (16×16 each) arranged as 8 columns × 5 rows = 128×80 total grid
- Land/sea pattern parsed from instruction diagrams: 3,062 land positions (29.9%), 7,178 ocean positions (70.1%)
- Matches Earth's actual surface coverage (~29% land, 71% ocean)

**Alternatives Considered**:
- **96×48 grid**: Initial assumption from generic world map aspect ratio - REJECTED because actual kit uses 128×80
- **Algorithmic land/sea detection**: Photo analysis of physical kit - REJECTED because instruction PDF provides exact reference data
- **Single tile type**: Assumed all positions use same part - REJECTED after discovering official kit uses two part types

**Implementation Notes**:
- Land/sea mask stored as project fixture: `cli/tests/fixtures/lego_world_map_land_sea_mask.json`
- Complete color map also available: `cli/tests/fixtures/lego_world_map_colormap.json`
- Mask extraction code: `extract_land_sea_mask.py`, `parse_lego_plates.py`, `generate_mask_from_plates.py`
- Both files generated during specification correction phase

---

### 2. LEGO Part Types for Land and Ocean

**Question**: Does the kit use a single part type for all positions, or different parts for land vs ocean?

**Decision**: TWO part types - round bricks for land, flat tiles for ocean

**Rationale**:
- Official LEGO World Map kit 31203 uses distinct part types to create tactile relief:
  - **Land positions**: LEGO part 3062b (Brick Round 1×1 Open Stud) - raised white bricks creating topographic texture
  - **Ocean positions**: LEGO part 98138 (Tile Round 1×1) - flat colored tiles flush with base plate
- This creates both visual and tactile distinction between land and ocean
- Land bricks stand ~3.2mm taller than ocean tiles, mimicking topographic elevation

**Alternatives Considered**:
- **Single part type (98138 only)**: Simpler but loses tactile depth - REJECTED because doesn't match official kit design
- **Algorithmic part selection**: Determine brick vs tile programmatically - REJECTED because kit uses fixed land/sea pattern

**Implementation Notes**:
- Layout generator must apply land/sea classification from mask to determine part type
- Output schema includes both `part_type` (brick/tile) and `lego_part_id` (3062b/98138) fields
- Color applies to both part types (land bricks can be colored, ocean tiles can be colored)

---

### 3. LEGO Color Palette for Both Part Types

**Question**: Which LEGO colors are available for round bricks (3062b) and flat tiles (98138)?

**Decision**: Reuse existing LEGO color palette from spec 001, filtered by part availability

**Rationale**:
- Spec 001 already compiled comprehensive LEGO color reference: `cli/src/lego_image_processor/palette/lego_colors.json`
- Contains official LEGO color IDs, names, RGB values for ~150 colors
- Quantized images (input to this feature) already use only these colors
- Part 98138 (flat tiles) available in ~64+ colors
- Part 3062b (round bricks) available in ~55 colors
- Color intersection provides ample palette for geographic visualization

**Alternatives Considered**:
- **Separate palette per part type**: Would complicate quantization and color matching - REJECTED for P1
- **Kit-specific color subset**: Research which exact colors ship with kit 31203 - DEFERRED to P2 (color validation story)

**Implementation Notes**:
- P1: Accept any LEGO color from existing palette for both part types
- P2: Add part-specific color validation (check if color available for brick vs tile)
- P2: Add kit inventory validation (check quantities available in standard kit)
- Validation logic compares against `lego_world_map_kit.json` color lists

---

### 4. JSON/CSV Output Schema Design

**Question**: What is the optimal structure for position layout output files (JSON and CSV formats)?

**Decision**: Simple tabular format with required fields: x_position, y_position, color_id, color_name, part_type, lego_part_id

**JSON Schema**:
```json
{
  "metadata": {
    "width": 128,
    "height": 80,
    "total_positions": 10240,
    "land_positions": 3062,
    "ocean_positions": 7178,
    "unique_colors": 12,
    "generated_at": "2026-01-07T12:00:00Z",
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
    ...
  ]
}
```

**CSV Schema**:
```csv
x_position,y_position,color_id,color_name,lego_color_code,part_type,lego_part_id
0,0,lego_blue_medium,Medium Blue,102,tile,98138
0,1,lego_blue_medium,Medium Blue,102,tile,98138
...
```

**Rationale**:
- Simple tabular structure is easy to parse by downstream tools (parts list generators, instruction builders)
- Metadata section in JSON provides context (dimensions, land/ocean breakdown, color counts, generation timestamp)
- CSV format enables spreadsheet analysis and manual inspection
- `part_type` field (brick/tile) enables proper parts counting
- `lego_part_id` field (3062b/98138) enables direct LEGO catalog lookup

**Alternatives Considered**:
- **Nested grid structure** `[[pos, pos, ...], [row2...]]`: Harder to stream, larger file size - REJECTED
- **Separate files for land vs ocean**: Complicates reassembly - REJECTED
- **Omit part_type field**: Assume can be derived from land/sea mask - REJECTED because schema should be self-contained

**Implementation Notes**:
- JSON output via Python's `json` module with pretty printing
- CSV output via Python's `csv` module with header row
- Schema versioning field (`"schema_version": "1.0"`) for future extensions
- Land/ocean counts in metadata enable quick validation

---

### 5. Grid Coordinate System Implementation

**Question**: How should coordinate mapping work from image pixels to grid positions?

**Decision**: Direct 1:1 mapping with top-left origin (0,0), x increases rightward, y increases downward

**Rationale**:
- Matches image pixel coordinate conventions (Pillow, NumPy use top-left origin)
- Specified in spec clarifications: "Top-left corner (matches image pixel coordinates)"
- Simplifies implementation: `position[x][y] = image_pixel[x][y]` with no transformation needed
- Consistent with FR-015: "MUST use top-left corner as coordinate system origin"

**Alternatives Considered**:
- **Bottom-left origin (Cartesian)**: Requires y-axis flip transformation, adds complexity - REJECTED
- **Center origin**: Requires translation math, unclear benefits for grid mapping - REJECTED

**Implementation Notes**:
- NumPy arrays index as `[y, x]` (row-major), so access pattern is `image[y, x]` → `position(x, y)`
- Document coordinate system clearly in output schema and CLI help text
- Include coordinate system field in JSON metadata: `"coordinate_system": "top_left_origin"`

---

### 6. Dimension Validation and Error Handling

**Question**: How should the tool handle images with dimensions that don't match kit specifications?

**Decision**: Reject with clear error message and suggest resize command

**Rationale**:
- Specified in spec clarifications: "Reject with error and suggest resize command"
- Prevents data loss from auto-cropping or unexpected scaling
- Gives users control over how to resize (different algorithms, aspect ratio handling)
- Follows fail-fast principle

**Error Message Template**:
```
Error: Image dimensions (100×50) don't match LEGO World Map kit specifications (128×80).

Suggested resize command using Pillow:
  from PIL import Image
  img = Image.open('input.png')
  img.resize((128, 80), Image.Resampling.LANCZOS).save('output.png')

Or use ImageMagick:
  convert input.png -resize 128x80! output.png
```

**Alternatives Considered**:
- **Auto-scale to fit**: Loses user control, may produce unexpected results - REJECTED
- **Crop/pad**: Data loss or artificial padding, unclear semantics - REJECTED
- **Accept any size**: Works for custom kits but confusing for standard kit users - REJECTED

**Implementation Notes**:
- Validation in `cli/src/lego_image_processor/layout/generator.py` before processing
- Support `--allow-custom-size` flag for advanced users with non-standard kits (future enhancement)
- Default behavior: strict validation against kit config (128×80)

---

### 7. Invalid Color Detection Strategy

**Question**: How should the tool detect and handle pixels with colors not in the LEGO palette?

**Decision**: Reject with error showing invalid RGB value and pixel location

**Rationale**:
- Specified in spec clarifications: "Reject with error showing invalid color location"
- Indicates upstream quantization failure (spec 001 should have produced only LEGO colors)
- Fail-fast prevents propagating bad data to parts lists and instructions
- Diagnostic info (RGB, x,y coordinates) helps users debug

**Error Message Template**:
```
Error: Invalid color detected at pixel (42, 17)
RGB value: (127, 84, 200)
This color is not in the LEGO palette reference data.

Possible causes:
1. Image was not quantized using lego-image-processor quantize command
2. Image file was modified after quantization
3. Image uses custom color palette

Solution: Re-run quantization:
  lego-image-processor quantize input.png -o quantized.png
  lego-image-processor layout quantized.png -o layout.json
```

**Alternatives Considered**:
- **Map to nearest LEGO color automatically**: Masks upstream errors, could produce incorrect maps - REJECTED
- **Skip invalid pixels**: Produces incomplete layouts with gaps - REJECTED
- **Treat as transparent**: No semantic meaning for LEGO positions - REJECTED

**Implementation Notes**:
- Color lookup using existing palette loader from spec 001
- RGB exact match check (quantized images should have exact palette colors)
- Validation runs during grid generation in `cli/src/lego_image_processor/layout/generator.py`

---

### 8. Kit Color Validation Approach (P2)

**Question**: How should kit-specific color validation work to check if a layout is buildable with standard kit?

**Decision**: Compare layout requirements against kit inventory loaded from configuration

**Approach**:
1. Load kit specification from `lego_world_map_kit.json` containing:
   - `available_colors_brick`: List of color IDs available for part 3062b
   - `available_colors_tile`: List of color IDs available for part 98138
   - `color_quantities`: Dict of {(part_type, color_id): count} for inventory
2. Count color usage in generated layout by part type
3. Report violations:
   - Colors not available for specific part type → suggest nearest available alternatives
   - Colors exceeding quantities → warn about shortfall, suggest sourcing more parts

**Validation Output**:
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
      "positions_required": 1200,
      "kit_quantity": 800,
      "shortfall": 400
    }
  ],
  "validated_at": "2026-01-07T12:05:00Z",
  "kit_id": "31203"
}
```

**Rationale**:
- Helps users understand if their custom map needs additional parts
- Provides actionable suggestions (alternative colors, sourcing guidance)
- Buildability score gives quick overview of compatibility
- Part-type-specific validation ensures correct LEGO catalog lookup

**Implementation Notes**:
- Validation logic in `cli/src/lego_image_processor/layout/validator.py`
- Color distance using existing Delta E calculation from spec 001
- Separate CLI command: `lego-image-processor validate layout.json`
- Validation reads kit config AND land/sea mask to properly categorize parts

---

### 9. Land/Sea Mask Loading and Utilities

**Question**: How should the land/sea mask be loaded, cached, and applied during layout generation?

**Decision**: Load mask once at module initialization, provide utilities for classification lookup

**Approach**:
```python
# cli/src/lego_image_processor/layout/land_sea_mask.py

import json
from pathlib import Path
from functools import lru_cache

MASK_PATH = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "lego_world_map_land_sea_mask.json"

@lru_cache(maxsize=1)
def load_land_sea_mask():
    """Load and cache land/sea mask from fixture."""
    with open(MASK_PATH, 'r') as f:
        return json.load(f)

def is_land_position(x: int, y: int) -> bool:
    """Check if position (x, y) is land."""
    mask_data = load_land_sea_mask()
    return mask_data['mask_2d'][y][x]  # Note: [y, x] indexing

def get_part_type(x: int, y: int) -> str:
    """Get part type ('brick' or 'tile') for position."""
    return 'brick' if is_land_position(x, y) else 'tile'

def get_lego_part_id(x: int, y: int) -> str:
    """Get LEGO part ID for position."""
    return '3062b' if is_land_position(x, y) else '98138'
```

**Rationale**:
- `@lru_cache` ensures mask loaded once per process
- Utilities provide clear, type-safe API for mask queries
- Centralized mask path management (single source of truth)
- Easy to mock/patch for testing

**Implementation Notes**:
- Mask validation on load: check dimensions (80×128), land count (3062), ocean count (7178)
- Utilities handle coordinate system correctly (y, x array indexing)
- Generator uses utilities to populate `part_type` and `lego_part_id` fields

---

## Technology Stack Decisions

### Core Libraries

**Selected**:
- **Pillow (PIL)**: Image I/O and pixel access - already used in spec 001
- **NumPy**: Array operations for grid manipulation - already used in spec 001
- **Click**: CLI framework for command structure - already used in spec 001
- **json (stdlib)**: JSON serialization for layouts and configs
- **csv (stdlib)**: CSV serialization for tabular layouts

**Rationale**: Reuse existing dependencies from spec 001 to maintain consistency and avoid dependency bloat. Use standard library modules where possible (json, csv) to minimize external dependencies.

### Data Formats

**Selected**:
- **JSON**: Structured layouts with metadata (primary format)
- **CSV**: Tabular exports for spreadsheet analysis (secondary format)
- **Configuration**: JSON for kit specifications (dimensions, colors, quantities)

**Rationale**: Standard formats, widely supported by downstream tools, no external dependencies

### Testing Framework

**Selected**:
- **pytest**: Already established in spec 001
- **pytest-mock**: For mocking filesystem and palette lookups
- **Contract testing**: I/O validation for CLI commands
- **Integration testing**: End-to-end workflow validation
- **Unit testing**: Core logic validation (grid, position, mask utilities)

**Rationale**: Consistency with existing test infrastructure, comprehensive coverage of all test levels

---

## Implementation Patterns

### Grid Representation

**Pattern**: Use NumPy 2D array for internal grid representation, convert to list of position objects for output

**Rationale**:
- NumPy provides efficient 2D array operations for large grids
- Memory-efficient for 128×80 = 10,240 positions
- Convert to list of PositionPlacement objects for JSON/CSV output

**Example**:
```python
import numpy as np

# Internal representation (colors only, part types from mask)
grid = np.zeros((80, 128), dtype=object)  # Stores color IDs

for y in range(80):
    for x in range(128):
        pixel_color = image[y, x]
        grid[y, x] = pixel_color

# Output conversion
positions = []
for y in range(80):
    for x in range(128):
        positions.append(PositionPlacement(
            x=x,
            y=y,
            color_id=grid[y, x],
            part_type=get_part_type(x, y),
            lego_part_id=get_lego_part_id(x, y)
        ))
```

### CLI Command Structure

**Pattern**: Follow Click command group structure from spec 001

```python
@click.group()
def cli():
    """LEGO Image Processor - Transform images into LEGO World Maps"""
    pass

@cli.command()
@click.argument('input_image', type=click.Path(exists=True))
@click.option('--output', '-o', required=True, help='Output layout file path')
@click.option('--format', type=click.Choice(['json', 'csv']), default='json')
def layout(input_image, output, format):
    """Generate LEGO position placement layout from quantized image"""
    pass

@cli.command()
@click.argument('layout_file', type=click.Path(exists=True))
@click.option('--kit', default='31203', help='LEGO kit ID for validation')
def validate(layout_file, kit):
    """Validate layout against LEGO World Map kit inventory"""
    pass
```

**Rationale**: Consistent with spec 001 CLI structure, familiar to users, leverages Click's built-in validation

---

## Performance Considerations

### Optimization Strategy

**Approach**: Optimize for clarity first, then profile if needed

**Expected Performance**:
- Reading 128×80 image: <0.1 seconds (Pillow is fast for small images)
- Grid generation: O(n) where n = pixels, 10,240 iterations ~0.01 seconds
- Land/sea lookup: O(1) with cached mask (array access)
- JSON serialization: <0.1 seconds for 10,240 position objects
- **Total**: <1 second for standard map (well under 5-second target)

**Potential Bottlenecks** (if performance issues arise):
1. **Color lookup**: Could cache palette as dict {RGB: color_id} for O(1) lookup
2. **JSON output**: For very large grids, consider streaming output
3. **Mask loading**: Already cached via `@lru_cache`

**No Premature Optimization**: Start with straightforward implementation, profile if SC-001 (<5s) or SC-003 (linear time) targets aren't met

---

## Summary

All technical unknowns resolved. Key decisions:

1. **Dimensions**: 128×80 grid (10,240 positions) from official kit 31203 instruction manual
2. **Part Types**: Round bricks (3062b) for land, flat tiles (98138) for ocean
3. **Land/Sea Pattern**: 3,062 land (29.9%), 7,178 ocean (70.1%) from extracted mask
4. **Colors**: Reuse spec 001 palette, filter to part-specific colors in P2 validation
5. **Schema**: Simple tabular format (JSON/CSV) with metadata, includes part_type and lego_part_id
6. **Coordinates**: Top-left (0,0) origin matching image pixels
7. **Validation**: Fail-fast on dimension/color mismatches with helpful errors
8. **Kit Config**: JSON file with dimensions, colors by part type, quantities
9. **Mask Utilities**: Cached loading with clear API for land/sea classification

Ready to proceed to Phase 1 (data model and contracts design).
