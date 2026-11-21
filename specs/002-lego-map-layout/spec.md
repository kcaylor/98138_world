# Feature Specification: LEGO Map Layout Generation

**Feature Branch**: `002-lego-map-layout`
**Created**: 2026-01-06
**Status**: Draft
**Input**: User description: "Generate LEGO map layout from color-quantized images"

## Project Vision

This project is an **homage to the official LEGO World Map kit** (set 31203). The goal is to extend the kit's vision to create similar LEGO World Maps that reflect ANY global geographic pattern - plate tectonics, net primary productivity, temperature, ocean currents, population density, etc. - while remaining familiar and consistent with the official kit's aesthetic and format.

**Analogy: Science on a Sphere for LEGO**

Think of NOAA's Science on a Sphere project - a standardized spherical projection surface that allows scientists to visualize ANY global dataset (weather, climate, ocean currents, etc.) on the same physical platform. We're doing the exact same thing, but for LEGO:

- **Science on a Sphere** = Spherical surface (hardware) + Projection software + ANY global dataset
- **98138.world** = LEGO World Map kit 31203 (hardware) + Our CLI tools + ANY global dataset

The LEGO kit is the standardized "canvas." Our tools are the "projection software" that translates any global data into the kit's format. Users bring their own geographic datasets. The result is always recognizable as "a LEGO World Map" - same familiar format, infinite data possibilities.

**Structure vs. Components**:
- **CONSTANT (Structure)**: Every kit has identical physical structure - base plates, frame, 128×80 grid = exactly 10,240 positions (3,062 land bricks + 7,178 ocean tiles based on official kit design)
- **VARIABLE (Components)**: The COLORS of tiles vary based on the data being visualized - each position is a "pixel" in the world map

Every map has the same number of "pixels" (10,240 positions), but they're unique due to color variations. A temperature map, NPP map, and ocean currents map all use the same kit structure with the same positions (land vs ocean), but different colors at different positions.

**Two Tile Types**:
- **Land positions (3,062)**: LEGO part 3062b (Brick Round 1×1 Open Stud) - white bricks that stand taller
- **Ocean positions (7,178)**: LEGO part 98138 (Tile Round 1×1) - colored flat tiles flush with base plate

**Target Audience**: LEGO Geographers - people who appreciate both LEGO building and geographic data visualization.

**Core Principle**: Maintain exact fidelity to the official kit's structure, format, and aesthetic (the "canvas" stays constant). Any features (like shadowing/texture) must replicate the official kit's approach EXACTLY, not introduce creative variations.

## Clarifications

### Session 2026-01-06

- Q: When generating brick placement grids, where should the origin (0,0) be positioned? → A: Top-left corner (matches image pixel coordinates)
- Q: When the input image dimensions don't match standard LEGO World Map kit dimensions (e.g., 100x50 instead of 96x48), what should the tool do? → A: Reject with error and suggest resize command
- Q: How should the system handle a quantized image pixel with a color that's not in the current LEGO palette reference data? → A: Reject with error showing invalid color location
- Q: What brick types and sizes should be used for map layouts? → A: TWO tile types matching official LEGO World Map kit 31203: (1) LEGO part 98138 (Tile Round 1×1) - flat tiles for ocean positions, (2) LEGO part 3062b (Brick Round 1×1 Open Stud) - raised white bricks for land positions. Land/sea classification is constant (3,062 land, 7,178 ocean positions based on official kit design), only colors vary. Base plates and frame elements remain constant from original kit.

**Note on Structure vs. Components**: Every map maintains identical structure (base plates, frame, 128×80 grid = 10,240 positions with constant land/sea classification) but varies in tile color distribution. The kit structure is constant; the tile component colors are variable based on the dataset being visualized. Each position functions as a "pixel" in the global map.

**Note on Land/Sea Classification**: The official LEGO World Map kit 31203 uses a specific land/sea pattern extracted from the instruction manual. Land positions (3,062 cells, 29.9%) use white round bricks (part 3062b), ocean positions (7,178 cells, 70.1%) use colored flat tiles (part 98138). This classification is stored in `cli/tests/fixtures/lego_world_map_land_sea_mask.json` and must be used for all map generation to maintain kit fidelity.

**Note on Shadowing/Texture**: The official LEGO World Map kit uses shadowing tiles (same 1x1 round tiles in shadow color) to add visual depth and prevent flat appearance. If implemented, shadowing MUST exactly replicate the official kit's patterns - this is an homage project requiring exact fidelity to the official kit's aesthetic, not creative interpretation. Documented as future optional enhancement but out of scope for P1 basic color mapping.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Brick Placement Grid Generation (Priority: P1)

A user has a color-quantized satellite image (output from the image processing tool) and wants to convert it into a buildable LEGO World Map using the official kit's land/sea pattern. They run a command-line tool that reads the quantized image, applies the land/sea classification mask, and generates a brick placement grid showing exactly which color tile/brick goes in which position. Land positions get colored round bricks (part 3062b), ocean positions get colored flat tiles (part 98138). The output includes coordinates, colors, and part types in a machine-readable format (JSON/CSV) that maps directly to the official LEGO World Map kit 31203 structure.

**Why this priority**: This is the core capability that translates color-quantized images into physical LEGO World Map building plans. Every pixel becomes a single 1x1 round tile with the corresponding LEGO color. This story delivers the complete translation layer needed to recreate any map image using the official LEGO World Map kit format.

**Independent Test**: Can be fully tested by providing a color-quantized test image (e.g., 32x32 pixels representing a section of world map), running the layout generation tool, and verifying that the output contains exactly one 1x1 round tile per pixel with colors matching the input pixels and coordinates fitting within LEGO World Map kit dimensions. Delivers standalone value by providing a complete building plan.

**Acceptance Scenarios**:

1. **Given** a color-quantized image file (PNG/JPEG) with only LEGO colors, **When** the user runs the layout generation command, **Then** the tool outputs a brick placement file containing position (x,y), color ID, and part type (brick or tile) for each of the 10,240 positions
2. **Given** a layout generation completes successfully, **When** the user inspects the output file, **Then** every coordinate maps to a valid position on a 128×80 LEGO World Map grid, land positions use round bricks (part 3062b), and ocean positions use flat tiles (part 98138)
3. **Given** a quantized image with specific dimensions (128×80 pixels for the standard world map), **When** layout is generated, **Then** the output grid contains exactly 10,240 positions (3,062 land bricks + 7,178 ocean tiles) matching the official kit pattern
4. **Given** a color in the quantized image at a land position, **When** mapped to the layout, **Then** the round brick assigned to that position uses the same LEGO color from the palette (applied to white brick base)
5. **Given** a color in the quantized image at an ocean position, **When** mapped to the layout, **Then** the flat tile assigned to that position uses the same LEGO color from the palette
6. **Given** the layout generation tool completes, **When** successful, **Then** the tool reports total positions (10,240), land/ocean breakdown (3,062/7,178), unique colors used, and output file path

---

### User Story 2 - LEGO World Map Kit Color Validation (Priority: P2)

A user generates a brick layout and wants assurance that their map can actually be built using the official LEGO World Map kit 1x1 round tile inventory. The tool validates the generated layout against the kit's available tile colors and quantities, warning users if the design requires tile colors that don't exist in the kit or exceed available quantities. The tool suggests color substitutions if needed to make the map buildable with standard kit parts.

**Why this priority**: This is a quality-of-life enhancement that prevents users from discovering color incompatibilities after they've committed to building. While valuable for ensuring buildability with kit colors, users can manually check tile color availability or source additional tiles as needed. The core layout generation (P1) still provides value without this validation.

**Independent Test**: Can be tested by generating layouts that deliberately use rare colors or exceed kit color quantities, and verifying that the validation tool correctly identifies color violations and suggests alternative colors from the kit palette. Delivers value by preventing build failures before users order tiles.

**Acceptance Scenarios**:

1. **Given** a generated brick layout, **When** the user runs kit validation, **Then** the tool compares required tile colors and quantities against LEGO World Map kit inventory and reports any missing or insufficient tile colors
2. **Given** a layout that requires colors not in the standard kit, **When** validation runs, **Then** the tool lists incompatible colors and suggests nearest available alternative colors from the kit palette
3. **Given** a layout that requires more 1x1 round tiles of a specific color than the kit provides, **When** validation runs, **Then** the tool warns about color quantity shortfalls and suggests either scaling down the map or planning to source additional tiles of that color
4. **Given** a fully compatible layout, **When** validation runs, **Then** the tool confirms "Layout is fully buildable with standard LEGO World Map kit" and reports remaining tile quantities by color

---

### User Story 3 - Official Kit Shadowing Replication (Priority: P3)

A user generates a tile layout and wants to apply the official LEGO World Map kit's shadowing pattern to add visual depth and texture, preventing an overly flat or saturated appearance. The tool analyzes the official kit's shadowing pattern (documented from instruction manual analysis) and applies the same shadow tile placement logic to the custom map layout, using the exact shadow color from the official kit.

**Why this priority**: This is an aesthetic enhancement that replicates the official kit's visual polish. While valuable for achieving authentic "LEGO World Map" appearance, the core layout generation (P1) and color validation (P2) deliver buildable maps without shadowing. This requires research into the official kit's exact shadowing patterns before implementation.

**Independent Test**: Can be tested by comparing shadowing output against the official LEGO World Map kit's instruction manual, verifying that shadow tiles are placed in identical positions and patterns. Delivers value by making custom maps visually indistinguishable from official kit aesthetic.

**Acceptance Scenarios**:

1. **Given** a generated tile layout without shadowing, **When** the user enables shadowing option, **Then** the tool applies shadow tiles in positions that exactly match the official LEGO World Map kit's shadowing pattern for equivalent geographic features
2. **Given** the official kit uses a specific shadow tile color (e.g., dark gray), **When** shadowing is applied, **Then** all shadow tiles use that exact LEGO color ID
3. **Given** a custom map with geographic features (oceans, continents), **When** shadowing is applied, **Then** the shadowing logic replicates how the official kit handles those feature types (e.g., ocean depths, mountain ranges)
4. **Given** shadowing is enabled, **When** the user reviews the layout, **Then** the output includes both base color tiles and shadow overlay tiles with clear differentiation in the schema
5. **Given** shadowing patterns from the official kit, **When** applied to custom data, **Then** the result maintains the official kit's aesthetic of subtle depth without obscuring the underlying geographic pattern

---

### Edge Cases

- **Dimension mismatch**: When input image dimensions don't match standard LEGO World Map kit dimensions (e.g., 100×50 instead of 128×80), the tool rejects the input with a clear error message and suggests a resize command to scale the image to 128×80 pixels.
- **Invalid color detection**: When a pixel contains a color not in the LEGO palette reference data (indicates upstream quantization failure), the tool rejects the image with an error message showing the invalid color's RGB value and pixel location (x,y coordinates), and suggests re-running the quantization tool.
- How does the tool handle very small images (e.g., 10x10 pixels) that don't represent realistic map layouts but are technically valid?
- What happens when a user requests an extremely large layout (e.g., 1000x1000) that would require one million 1x1 round tiles beyond any reasonable kit size?
- How does the system handle aspect ratios that don't match standard base plate configurations when mapping to rectangular base plates?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Tool MUST accept color-quantized image files (PNG, JPEG, TIFF) as input with validation that all pixels contain only valid LEGO colors, rejecting images with an error that specifies the invalid color's RGB value and pixel coordinates when non-LEGO colors are detected
- **FR-002**: Tool MUST generate a brick placement grid mapping each pixel to exactly one tile or brick at a base plate coordinate with format: position (x,y), LEGO color ID, and part type (brick for land, tile for ocean)
- **FR-003**: Tool MUST output brick layouts in machine-readable formats (JSON, CSV) with schema defining required fields: x_position, y_position, color_id, color_name, part_type (brick=3062b or tile=98138)
- **FR-004**: Tool MUST validate that layout dimensions match LEGO World Map kit base plate specifications exactly (standard dimensions: 128 studs × 80 studs = 10,240 positions)
- **FR-004a**: Tool MUST apply land/sea classification from official kit mask (cli/tests/fixtures/lego_world_map_land_sea_mask.json) to determine part type for each position
- **FR-005**: Tool MUST preserve exact pixel-to-tile color mapping from quantized input to layout output with zero color drift (one-to-one pixel-to-tile correspondence)
- **FR-006**: Tool MUST support command-line arguments for input file path, output file path, and output format selection
- **FR-007**: Tool MUST provide progress feedback for layouts with more than 1000 tiles (can be suppressed with --quiet flag)
- **FR-008**: Tool MUST validate input images before processing and report clear error messages for invalid inputs (non-quantized images, unsupported formats, dimension mismatches with kit specifications), including specific resize suggestions when dimensions don't match supported base plate sizes
- **FR-009**: Tool MUST calculate and report layout statistics (total tile count, unique colors, color frequency distribution) in output metadata
- **FR-010**: Tool MUST work offline without requiring internet connectivity or external API calls
- **FR-011**: Tool MUST read LEGO World Map kit reference data (available tile colors, base plate dimensions, color quantities) from local configuration files (JSON/YAML)
- **FR-012**: Validation feature MUST compare generated layouts against LEGO World Map kit tile color inventory (colors and quantities) and report compatibility issues
- **FR-013**: Validation MUST suggest color alternatives when layouts use colors not available in the kit or exceed available tile quantities for specific colors
- **FR-014**: Tool MUST support the official LEGO World Map kit 31203 dimensions (128×80 = 10,240 positions) as the primary standard size
- **FR-015**: Tool MUST use top-left corner as coordinate system origin (0,0), matching image pixel coordinate conventions, with x increasing rightward and y increasing downward, documented in output schema
- **FR-016**: Tool MUST maintain exact compatibility with official LEGO World Map kit 31203 structure - using round bricks (part 3062b) for land positions and flat tiles (part 98138) for ocean positions, matching base plate dimensions (128×80 = 10,240 positions) and land/sea classification pattern, ensuring generated layouts preserve constant physical structure and land/sea pattern while varying tile/brick colors based on the dataset being visualized
- **FR-017**: Shadowing feature (if implemented) MUST replicate the exact shadowing pattern from the official LEGO World Map kit instruction manual, using the same shadow tile color and placement positions, not algorithmic or creative variations

### Assumptions

- **LEGO World Map Kit Structure**: The official LEGO World Map kit 31203 uses a standard rectangular base plate with a stud grid pattern. The standard size is 128 studs wide by 80 studs tall (matching common world map proportions of 1.6:1 aspect ratio, total 10,240 stud positions). Dimensions extracted from official kit instruction manual.

- **Two Part Types for Land and Ocean**: The LEGO World Map kit uses TWO part types: (1) Round bricks (part 3062b) for land positions - these stand taller creating tactile relief, (2) Flat round tiles (part 98138) for ocean positions - these sit flush with the base plate. The land/sea classification is constant across all maps (3,062 land, 7,178 ocean positions from official kit pattern), only colors vary. Base plates and frame elements are constant structural components.

- **One Part Per Stud Position**: Each base plate stud position holds exactly one part (either a round brick or flat tile). There is a perfect 1:1 correspondence between stud positions and parts, with no gaps or overlaps.

- **Pixel-to-Position Mapping**: There is a direct 1:1 mapping between image pixels and grid positions. A 128×80 pixel quantized image maps to exactly 10,240 positions (3,062 land bricks + 7,178 ocean tiles). Each pixel becomes one part with the corresponding LEGO color, and part type determined by land/sea mask.

- **JSON/CSV Output Schema**: A simple tabular format is sufficient for tile layout representation. JSON format will use an array of position objects; CSV will use rows with columns: x_position, y_position, color_id, color_name, part_type (brick or tile), lego_part_id (3062b or 98138). Schema will be versioned for future extensions.

- **No Rotation or Orientation**: Round bricks and round tiles are both rotationally symmetric, so orientation/rotation is not a meaningful attribute. All parts are placed identically with only color and type (brick vs tile) varying between positions.

- **Kit Color Inventory Availability**: LEGO World Map kit color inventory data (which tile colors exist, quantities per color) can be compiled from official LEGO documentation, instruction manuals, or community-maintained databases like Rebrickable or BrickLink.

- **Shadowing and Texture (Future Enhancement)**: The official LEGO World Map kit uses shadowing tiles (same 1x1 round tiles in a specific shadow color) applied in a specific pattern to add texture and visual depth, preventing overly flat or saturated appearance. If shadowing is implemented in future iterations, it MUST exactly replicate the official kit's shadowing patterns through analysis of the official kit's instruction manual and physical build. This is not an algorithmic or creative feature - it's a faithful reproduction of the official kit's aesthetic approach. Considered out of scope for P1 but documented as User Story 3 (P3) requiring prerequisite research into official patterns.

- **Constant Structure, Variable Components**: Every generated map maintains identical physical structure (base plates, frame, 128×80 grid = 10,240 positions with constant land/sea classification) but varies in part color distribution based on the visualized dataset. The total piece count and part types are constant (3,062 land bricks + 7,178 ocean tiles + structural elements), but which colors appear at which positions is unique to each dataset. Each position functions as a "pixel" in the global map image.

- **Land/Sea Mask**: The official LEGO World Map kit 31203 uses a specific land/sea pattern extracted from the instruction manual and stored in `cli/tests/fixtures/lego_world_map_land_sea_mask.json`. This mask defines which of the 10,240 positions are land (3,062 = 29.9%) vs ocean (7,178 = 70.1%). This classification is constant across all custom maps to maintain kit fidelity - only colors vary, not the land/sea structure.

- **Homage Philosophy**: This project extends the official LEGO World Map kit's vision to support any global geographic dataset (plate tectonics, NPP, temperature, ocean currents, population density, etc.) while maintaining exact fidelity to the official kit's format, structure, and aesthetic. Any deviations from the official kit's approach must be explicitly justified and documented. The goal is familiarity and consistency with the official kit, not creative reinterpretation.

### Key Entities

- **Position Placement Grid**: A two-dimensional array representing the base plate layout, where each cell contains either a round brick (land) or flat tile (ocean) specification. Attributes include grid dimensions (width, height in studs: 128×80 = 10,240 positions), coordinate system origin (top-left at 0,0 with x rightward, y downward), land/sea classification mask (3,062 land, 7,178 ocean), and collection of position placements. Represents the complete building plan for a LEGO World Map.

- **Position Placement**: An individual part (brick or tile) positioned on the grid. Attributes include position (x, y coordinates in studs), LEGO color (ID and name from official palette), part type (brick for land, tile for ocean), and LEGO part ID (3062b for round bricks, 98138 for flat tiles). Represents a single part to be placed during construction.

- **Land/Sea Mask**: Binary classification of all 10,240 grid positions into land (3,062 positions = 29.9%) or ocean (7,178 positions = 70.1%). Extracted from official LEGO World Map kit 31203 instruction manual and stored in `cli/tests/fixtures/lego_world_map_land_sea_mask.json`. This classification is constant across all custom maps - determines part type (brick vs tile) for each position.

- **LEGO World Map Kit Specification**: Reference data defining the physical kit structure (constant) and component requirements (variable per dataset). **Constant attributes**: base plate dimensions (128×80 studs = 10,240 positions), land/sea classification pattern (3,062 land + 7,178 ocean), frame elements, structural components, shadowing pattern specification (if implemented). **Variable attributes**: part color distribution (which colors at which positions), part quantities per color (depends on dataset being visualized). Total part count is always 10,240 (3,062 bricks + 7,178 tiles), but color composition varies. Represents both the unchanging hardware platform and the variable component requirements for each unique map.

- **Layout Statistics**: Summary metadata about a generated layout. Attributes include total tile count (equals pixel count, e.g., 4608 for standard 96×48 map), unique colors used, color frequency distribution (tiles per color), and coverage metrics (percentage of grid filled). Helps users understand layout composition and tile requirements.

- **Validation Report**: Output from kit color compatibility validation. Attributes include compatibility status (pass/fail), list of color violations (missing colors, quantity shortfalls for specific colors), suggested color substitutions, and buildability score (percentage of layout achievable with standard kit tile colors and quantities). Helps users understand feasibility of building their design with available kit tiles.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can convert a standard world map image (128×80 pixels, quantized to LEGO colors) into a complete position placement layout in under 5 seconds on consumer hardware
- **SC-002**: Generated layouts preserve 100% color accuracy - every part color in the output matches the corresponding pixel color from the quantized input image with zero discrepancies (perfect one-to-one pixel-to-position mapping)
- **SC-003**: Layout generation completes in linear time relative to pixel count, processing the standard 10,240 position map (128×80) in under 10 seconds
- **SC-004**: Kit color validation correctly identifies incompatibilities in 95% of test cases when layouts use colors or quantities not available in the LEGO World Map kit reference data
- **SC-005**: Users can successfully build a physical LEGO World Map from generated layouts without encountering missing tiles or placement errors, achieving 90% first-attempt build success rate in user testing
- **SC-006**: Layout output files are machine-readable and parseable by downstream tools (parts list generators, instruction builders) with 100% schema validation success rate
- **SC-007**: The tool works consistently across major operating systems (Windows, macOS, Linux) without platform-specific failures or output differences
- **SC-008**: Tool provides clear, actionable error messages for all common failure scenarios (invalid input format, dimension mismatch, corrupted files, invalid colors) enabling users to resolve issues without external help in 95% of cases
- **SC-009**: Generated layouts produce exactly the same position count as input pixel count with no positions missing or duplicated (128×80 image = 10,240 positions: 3,062 bricks + 7,178 tiles) - constant structure and land/sea classification, variable color distribution
- **SC-010**: Generated layouts maintain aesthetic fidelity to the official LEGO World Map kit 31203 format - using identical part types (round bricks for land, flat tiles for ocean), base plate structure, land/sea pattern, and coordinate system, enabling users to recognize the homage to the official kit while displaying custom geographic data
