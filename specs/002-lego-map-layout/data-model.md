# Data Model: LEGO Map Layout Generation

**Feature**: 002-lego-map-layout
**Date**: 2026-01-07 (Updated)
**Source**: Extracted from spec.md Key Entities section and research.md decisions

## Overview

This data model represents the position layout generation system for LEGO World Maps matching the official LEGO World Map kit 31203 structure. The model maintains exact fidelity to the official kit's structure (constant: 128×80 grid, land/sea pattern, part types) while supporting variable part colors based on visualized datasets (temperature, NPP, ocean currents, population density, etc.).

**Key Principles**:
- 1:1 pixel-to-position mapping (no interpolation or optimization)
- Top-left (0,0) coordinate origin
- TWO part types: round bricks (3062b) for land, flat tiles (98138) for ocean
- Constant structure (128×80 grid, 3,062 land + 7,178 ocean), variable components (part colors)
- Official kit 31203 homage - exact dimensional and structural fidelity

---

## Core Entities

### 1. PositionPlacement

Represents a single LEGO part (round brick or flat tile) at a specific grid position. Land positions use round bricks (part 3062b) that stand taller, ocean positions use flat tiles (part 98138) that sit flush with the base plate.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `x` | integer | Yes | X coordinate (0-based, increases rightward) | 0 ≤ x < 128 |
| `y` | integer | Yes | Y coordinate (0-based, increases downward) | 0 ≤ y < 80 |
| `color_id` | string | Yes | LEGO color identifier (e.g., "lego_blue_medium") | Must exist in palette |
| `color_name` | string | Yes | Human-readable color name (e.g., "Medium Blue") | - |
| `lego_color_code` | string | Yes | Official LEGO color code (e.g., "102") | - |
| `part_type` | enum | Yes | Part type: "brick" (land) or "tile" (ocean) | "brick" or "tile" |
| `lego_part_id` | string | Yes | LEGO part number: "3062b" (brick) or "98138" (tile) | "3062b" or "98138" |

**Invariants**:
- Land positions (mask=true) always use part_type="brick", lego_part_id="3062b"
- Ocean positions (mask=false) always use part_type="tile", lego_part_id="98138"
- Rotation is always 0 degrees - not stored as field since parts are rotationally symmetric
- Each (x, y) coordinate has exactly one position placement
- Part type determined by land/sea mask, not by pixel color

**Example**:
```python
# Ocean position (flat tile)
PositionPlacement(
    x=0,
    y=0,
    color_id="lego_blue_medium",
    color_name="Medium Blue",
    lego_color_code="102",
    part_type="tile",
    lego_part_id="98138"
)

# Land position (round brick)
PositionPlacement(
    x=45,
    y=25,
    color_id="lego_green",
    color_name="Green",
    lego_color_code="28",
    part_type="brick",
    lego_part_id="3062b"
)
```

---

### 2. PositionPlacementGrid

Represents the complete LEGO World Map building plan - a 128×80 grid with 10,240 positions (3,062 land bricks + 7,178 ocean tiles) matching the official kit 31203 structure.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `width` | integer | Yes | Grid width in studs (standard: 128) | > 0 |
| `height` | integer | Yes | Grid height in studs (standard: 80) | > 0 |
| `total_positions` | integer | Yes | Total positions (standard: 10,240) | width × height |
| `land_positions` | integer | Yes | Land positions count (standard: 3,062) | From mask |
| `ocean_positions` | integer | Yes | Ocean positions count (standard: 7,178) | From mask |
| `unique_colors` | integer | Yes | Count of distinct colors used | > 0 |
| `coordinate_system` | string | Yes | Always "top_left_origin" | Fixed value |
| `generated_at` | datetime | Yes | Generation timestamp | ISO 8601 format |
| `source_image` | string | Yes | Input quantized image filename | - |
| `schema_version` | string | Yes | Schema version (current: "1.0") | Semantic versioning |
| `positions` | List[PositionPlacement] | Yes | All position placements | length = 10,240 |

**Derived Properties**:
- `color_frequency`: dict mapping color_id → count across all positions
- `color_frequency_by_part_type`: dict with "brick" and "tile" sub-dicts
- `most_common_color`: color with highest frequency
- `coverage_percentage`: always 100.0% for valid layouts

**Invariants**:
- Every position (x, y) where 0 ≤ x < 128 and 0 ≤ y < 80 has exactly one placement
- total_positions = land_positions + ocean_positions (always 10,240 = 3,062 + 7,178)
- Land count = 3,062 (29.9%), ocean count = 7,178 (70.1%) from official kit mask
- Coordinate system is always top-left origin (0,0)
- Total position count equals width × height (no gaps, no overlaps)

**Example**:
```python
PositionPlacementGrid(
    width=128,
    height=80,
    total_positions=10240,
    land_positions=3062,
    ocean_positions=7178,
    unique_colors=12,
    coordinate_system="top_left_origin",
    generated_at=datetime(2026, 1, 7, 12, 0, 0),
    source_image="natural_earth_ii_quantized.png",
    schema_version="1.0",
    positions=[
        PositionPlacement(0, 0, "lego_blue_medium", "Medium Blue", "102", "tile", "98138"),
        PositionPlacement(1, 0, "lego_blue_medium", "Medium Blue", "102", "tile", "98138"),
        # ... 10,238 more positions
    ]
)
```

---

### 3. LandSeaMask

Binary classification of all 10,240 grid positions into land (round bricks) or ocean (flat tiles), extracted from official LEGO World Map kit 31203 instruction manual. This classification is constant across all custom maps - only colors vary.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `width` | integer | Yes | Mask width in positions (128) | 128 |
| `height` | integer | Yes | Mask height in positions (80) | 80 |
| `total_positions` | integer | Yes | Total positions (10,240) | 10,240 |
| `land_count` | integer | Yes | Land positions (3,062) | 3,062 |
| `ocean_count` | integer | Yes | Ocean positions (7,178) | 7,178 |
| `land_percentage` | float | Yes | Land percentage (29.9%) | ~29.9 |
| `ocean_percentage` | float | Yes | Ocean percentage (70.1%) | ~70.1 |
| `mask_2d` | Array[80][128] | Yes | 2D boolean array (true=land, false=ocean) | 80×128 |
| `source` | string | Yes | Extraction source reference | - |
| `extracted_date` | date | Yes | Extraction date | ISO 8601 date |

**Invariants**:
- Dimensions fixed: 80 rows × 128 columns
- land_count + ocean_count = total_positions (10,240)
- Land percentage approximately matches Earth's land coverage (~29%)
- Mask values are boolean only (no partial/intermediate values)
- Mask is immutable - never modified after extraction

**Business Rules**:
- Mask extracted from official LEGO World Map kit 31203 instruction manual
- Same mask used for all custom maps (maintains kit fidelity)
- Land positions (mask[y][x]=true) → round bricks (part 3062b)
- Ocean positions (mask[y][x]=false) → flat tiles (part 98138)
- Stored in: `cli/tests/fixtures/lego_world_map_land_sea_mask.json`

**Example**:
```json
{
  "width": 128,
  "height": 80,
  "total_positions": 10240,
  "land_count": 3062,
  "ocean_count": 7178,
  "land_percentage": 29.9,
  "ocean_percentage": 70.1,
  "mask_2d": [
    [false, false, false, true, false, ...],  // Row 0 (128 values)
    [false, false, true, true, false, ...]    // Row 1
    // ... 78 more rows
  ],
  "source": "LEGO World Map kit 31203 instruction manual",
  "extracted_date": "2026-01-06"
}
```

---

### 4. LEGOWorldMapKitSpecification

Reference data defining the official LEGO World Map kit 31203 structure (constant) and component inventory (variable per kit variant). Used for dimensional validation (P1) and color inventory checking (P2).

**Attributes**:

**Constant Structure** (same for all kits):
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `kit_id` | string | Yes | Official LEGO kit ID (e.g., "31203") | - |
| `kit_name` | string | Yes | Official kit name | - |
| `base_plate_width` | integer | Yes | Total width in studs (128) | 128 |
| `base_plate_height` | integer | Yes | Total height in studs (80) | 80 |
| `total_positions` | integer | Yes | Total positions (10,240) | 10,240 |
| `land_positions` | integer | Yes | Land positions (3,062) | 3,062 |
| `ocean_positions` | integer | Yes | Ocean positions (7,178) | 7,178 |
| `land_part_id` | string | Yes | LEGO part for land ("3062b") | "3062b" |
| `ocean_part_id` | string | Yes | LEGO part for ocean ("98138") | "98138" |

**Variable Components** (differs by kit variant):
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `available_colors_brick` | List[string] | Yes | Colors available for part 3062b | From palette |
| `available_colors_tile` | List[string] | Yes | Colors available for part 98138 | From palette |
| `brick_quantities` | Dict[str, int] | Yes | Round brick color quantities {color_id: count} | Values > 0 |
| `tile_quantities` | Dict[str, int] | Yes | Flat tile color quantities {color_id: count} | Values > 0 |
| `shadowing_pattern` | Array | No | Shadow tile positions (P3 future) | - |

**Usage**:
- **P1 (Basic Layout)**: Use dimensions and part types for validation
- **P2 (Color Validation)**: Use color lists and quantities for buildability checking
- **P3 (Shadowing)**: Use shadowing_pattern to apply official kit shadowing (future)

**Example**:
```json
{
  "kit_id": "31203",
  "kit_name": "LEGO World Map",
  "base_plate_width": 128,
  "base_plate_height": 80,
  "total_positions": 10240,
  "land_positions": 3062,
  "ocean_positions": 7178,
  "land_part_id": "3062b",
  "ocean_part_id": "98138",
  "available_colors_brick": [
    "lego_white",
    "lego_green",
    "lego_tan",
    "lego_brown"
  ],
  "available_colors_tile": [
    "lego_blue_medium",
    "lego_blue_dark",
    "lego_green",
    "lego_tan"
  ],
  "brick_quantities": {
    "lego_white": 500,
    "lego_green": 800,
    "lego_tan": 600
  },
  "tile_quantities": {
    "lego_blue_medium": 1500,
    "lego_blue_dark": 1200,
    "lego_green": 400
  }
}
```

---

### 5. LayoutStatistics

Summary metadata about a generated layout - provides quick overview of composition and part requirements without parsing full position array.

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `total_tile_count` | integer | Yes | Total positions (10,240) | 10,240 |
| `land_brick_count` | integer | Yes | Round bricks (3,062) | 3,062 |
| `ocean_tile_count` | integer | Yes | Flat tiles (7,178) | 7,178 |
| `unique_colors` | integer | Yes | Distinct colors used | > 0 |
| `color_frequency` | Dict[str, int] | Yes | Color → count across all positions | - |
| `color_frequency_by_part_type` | Dict | Yes | Split by part type (brick/tile) | - |
| `most_common_color` | Dict | Yes | Color with highest frequency | - |
| `least_common_color` | Dict | Yes | Color with lowest frequency | - |
| `coverage_percentage` | float | Yes | Percentage of grid filled (100.0%) | 100.0 |

**Derived from PositionPlacementGrid during generation**

**Example**:
```python
LayoutStatistics(
    total_tile_count=10240,
    land_brick_count=3062,
    ocean_tile_count=7178,
    unique_colors=12,
    color_frequency={
        "lego_blue_medium": 2400,
        "lego_green": 1850,
        "lego_tan": 1200,
        # ... other colors
    },
    color_frequency_by_part_type={
        "brick": {
            "lego_green": 1500,
            "lego_tan": 800,
            "lego_brown": 450
        },
        "tile": {
            "lego_blue_medium": 2400,
            "lego_blue_dark": 1200,
            "lego_green": 350
        }
    },
    most_common_color={
        "color_id": "lego_blue_medium",
        "color_name": "Medium Blue",
        "count": 2400
    },
    coverage_percentage=100.0
)
```

---

### 6. ValidationReport (P2)

Result of validating a position layout against LEGO World Map kit specifications. Indicates whether layout can be physically built with standard kit inventory, with part-type-specific validation (bricks vs tiles).

**Attributes**:
| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `buildable` | boolean | Yes | Overall buildability flag | - |
| `buildability_score` | float | Yes | Percentage buildable (0.0-1.0) | 0.0 ≤ score ≤ 1.0 |
| `violations` | List[Violation] | Yes | Compatibility issues (empty if buildable) | - |
| `validated_at` | datetime | Yes | Validation timestamp | ISO 8601 |
| `kit_id` | string | Yes | Kit validated against (e.g., "31203") | - |
| `layout_file` | string | Yes | Validated layout file path | - |

**Buildability Score Calculation**:
```
buildability_score = (positions_buildable_with_kit) / (total_positions_required)
```

**Example**:
```python
ValidationReport(
    buildable=False,
    buildability_score=0.85,
    violations=[
        ColorUnavailableViolation(...),
        QuantityExceededViolation(...)
    ],
    validated_at=datetime(2026, 1, 7, 12, 5, 0),
    kit_id="31203",
    layout_file="/path/to/layout.json"
)
```

---

### 7. Violation (Abstract Base)

Base class for validation violations. Subclasses represent specific violation types with part-type context (brick vs tile).

#### 7a. ColorUnavailableViolation

Color required by layout is not available in the kit for the specified part type.

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Always "color_unavailable" |
| `part_type` | string | Yes | Affected part type ("brick" or "tile") |
| `part_id` | string | Yes | LEGO part ID ("3062b" or "98138") |
| `color_id` | string | Yes | Required color not in kit |
| `color_name` | string | Yes | Human-readable color name |
| `positions_required` | integer | Yes | Number of positions needing this color |
| `suggested_alternative` | ColorSuggestion | No | Nearest available color in kit |

**Example**:
```python
ColorUnavailableViolation(
    type="color_unavailable",
    part_type="brick",
    part_id="3062b",
    color_id="lego_purple_bright",
    color_name="Bright Purple",
    positions_required=47,
    suggested_alternative=ColorSuggestion(
        color_id="lego_magenta",
        color_name="Magenta",
        color_distance=12.4
    )
)
```

#### 7b. QuantityExceededViolation

Layout requires more parts of a color/type than kit provides.

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Always "quantity_exceeded" |
| `part_type` | string | Yes | Affected part type ("brick" or "tile") |
| `part_id` | string | Yes | LEGO part ID ("3062b" or "98138") |
| `color_id` | string | Yes | Color with insufficient quantity |
| `color_name` | string | Yes | Human-readable color name |
| `positions_required` | integer | Yes | Number of positions needed |
| `kit_quantity` | integer | Yes | Number available in kit |
| `shortfall` | integer | Yes | positions_required - kit_quantity |

**Example**:
```python
QuantityExceededViolation(
    type="quantity_exceeded",
    part_type="tile",
    part_id="98138",
    color_id="lego_blue_medium",
    color_name="Medium Blue",
    positions_required=2400,
    kit_quantity=1500,
    shortfall=900
)
```

---

### 8. ColorSuggestion

Suggested alternative color for unavailable colors.

**Attributes**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `color_id` | string | Yes | Suggested color ID |
| `color_name` | string | Yes | Human-readable name |
| `color_distance` | float | Yes | Delta E distance from required color |

**Note**: Color distance calculated using Delta E 2000 algorithm (same as spec 001 quantization).

---

## Entity Relationships

```
┌────────────────────────────────────┐
│ LEGOWorldMapKitSpecification       │
│ ────────────────────────────       │
│ kit_id: "31203"                    │
│ base_plate_width: 128              │
│ base_plate_height: 80              │
│ total_positions: 10240             │
│ land_part_id: "3062b"              │
│ ocean_part_id: "98138"             │
│ available_colors_brick[]           │
│ available_colors_tile[]            │
│ brick_quantities{}                 │
│ tile_quantities{}                  │
└──────────┬─────────────────────────┘
           │ validates against
           │
           ▼
┌────────────────────────────────────┐
│ PositionPlacementGrid              │
│ ────────────────────────────       │
│ width: 128                         │
│ height: 80                         │
│ total_positions: 10240             │
│ land_positions: 3062               │
│ ocean_positions: 7178              │
│ unique_colors: int                 │
│ coordinate_system: "top_left..."   │
│ generated_at: timestamp            │
│ source_image: string               │
│ schema_version: "1.0"              │
│ positions: PositionPlacement[]     │
└──────────┬─────────────────────────┘
           │ contains 10,240 ×
           │
           ▼
┌────────────────────────────────────┐
│ PositionPlacement                  │
│ ────────────────────────────       │
│ x: int (0-127)                     │
│ y: int (0-79)                      │
│ color_id: string                   │
│ color_name: string                 │
│ lego_color_code: string            │
│ part_type: "brick"|"tile"          │
│ lego_part_id: "3062b"|"98138"      │
└──────────┬─────────────────────────┘
           │ part_type determined by
           │
           ▼
┌────────────────────────────────────┐
│ LandSeaMask                        │
│ ────────────────────────────       │
│ width: 128                         │
│ height: 80                         │
│ total_positions: 10240             │
│ land_count: 3062 (29.9%)           │
│ ocean_count: 7178 (70.1%)          │
│ mask_2d: boolean[80][128]          │
│ source: "kit 31203 manual"         │
│ extracted_date: date               │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ LayoutStatistics                   │
│ ────────────────────────────       │
│ total_tile_count: 10240            │
│ land_brick_count: 3062             │
│ ocean_tile_count: 7178             │
│ unique_colors: int                 │
│ color_frequency: {}                │
│ color_frequency_by_part_type: {}   │
│ most_common_color: {}              │
│ coverage_percentage: 100.0         │
└────────────────────────────────────┘
           ↑ computed from
           │
  PositionPlacementGrid

           │ produces (P2)
           ▼
┌────────────────────────────────────┐
│ ValidationReport                   │
│ ────────────────────────────       │
│ buildable: boolean                 │
│ buildability_score: float          │
│ violations: Violation[]            │
│ validated_at: timestamp            │
│ kit_id: string                     │
│ layout_file: string                │
└──────────┬─────────────────────────┘
           │ contains
           ▼
┌────────────────────────────────────┐
│ Violation (abstract)               │
├────────────────────────────────────┤
│ ColorUnavailableViolation          │
│ - part_type: "brick"|"tile"        │
│ - part_id: "3062b"|"98138"         │
│ - color_id                         │
│ - positions_required               │
│ - suggested_alternative            │
├────────────────────────────────────┤
│ QuantityExceededViolation          │
│ - part_type: "brick"|"tile"        │
│ - part_id: "3062b"|"98138"         │
│ - color_id                         │
│ - positions_required               │
│ - shortfall                        │
└────────────────────────────────────┘
```

---

## Data Flow

### Layout Generation (P1)

```
Quantized Image (PNG/JPEG) [128×80 pixels]
    │
    ↓ Load & Validate
Image Pixel Array [80][128]
    │
    ├──→ Validate dimensions (must be 128×80)
    └──→ Validate colors (all in LEGO palette)
    │
    ↓ Load LandSeaMask
    │
    ↓ For each pixel (x, y):
    ├──→ Read pixel color → color_id, color_name, lego_color_code
    ├──→ Query LandSeaMask[y][x] → is_land (boolean)
    ├──→ Determine part_type: "brick" if is_land else "tile"
    └──→ Determine lego_part_id: "3062b" if is_land else "98138"
    │
    ↓ Generate
PositionPlacement objects (10,240×)
    │
    ↓ Aggregate
PositionPlacementGrid
    │
    ├──→ Compute LayoutStatistics (color frequencies, part counts)
    └──→ Add metadata (timestamp, source, dimensions, land/ocean breakdown)
    │
    ↓ Serialize
Output Files (JSON/CSV)
```

### Kit Validation (P2)

```
Layout File (JSON/CSV)
    │
    ↓ Load
PositionPlacementGrid
    │
    ↓ Count colors by part type
Color Requirements {
    "brick": {color_id: count, ...},
    "tile": {color_id: count, ...}
}
    │
    ↓ Load LEGOWorldMapKitSpecification
    │
    ├──→ available_colors_brick[]
    ├──→ available_colors_tile[]
    ├──→ brick_quantities{}
    └──→ tile_quantities{}
    │
    ↓ Validate by part type
    │
    ├──→ For brick colors:
    │     ├──→ Color not in available_colors_brick → ColorUnavailableViolation
    │     │     └──→ Find nearest alternative from brick palette (Delta E)
    │     └──→ Count > brick_quantities[color] → QuantityExceededViolation
    │
    └──→ For tile colors:
          ├──→ Color not in available_colors_tile → ColorUnavailableViolation
          │     └──→ Find nearest alternative from tile palette (Delta E)
          └──→ Count > tile_quantities[color] → QuantityExceededViolation
    │
    ↓ Compute buildability score
Percentage = (buildable_positions) / (total_positions)
    │
    ↓ Generate
ValidationReport
    │
    ↓ Output
Validation Results (JSON/stdout)
```

---

## Summary

This data model defines eight core entities for LEGO World Map layout generation:

1. **PositionPlacement**: Individual part (brick or tile) with location, color, and type
2. **PositionPlacementGrid**: Complete building plan (128×80 grid, 10,240 positions)
3. **LandSeaMask**: Binary classification (3,062 land, 7,178 ocean) from official kit
4. **LEGOWorldMapKitSpecification**: Reference data for validation and buildability
5. **LayoutStatistics**: Summary metadata for layout composition
6. **ValidationReport**: Compatibility analysis against kit inventory (P2)
7. **Violation**: Abstract base with part-type-specific subclasses
8. **ColorSuggestion**: Alternative color recommendations

The model maintains exact fidelity to official LEGO World Map kit 31203 structure (constant: dimensions 128×80, land/sea pattern 3,062/7,178, part types 3062b/98138) while supporting variable part colors for infinite dataset visualizations. All entities support serialization to JSON/CSV formats with clear schemas for downstream tools.
