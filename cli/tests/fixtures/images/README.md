# Test Image Fixtures

This directory contains satellite/map imagery for testing the LEGO World Map generation system.

## Purpose

These test images serve multiple purposes:
1. **Unit/Integration Testing:** Validate color quantization, map generation, and parts calculation
2. **Performance Benchmarking:** Measure processing time for various image sizes
3. **Visual Regression:** Ensure changes don't degrade output quality
4. **Documentation Examples:** Provide real-world examples in README files

## Directory Structure

```
images/
├── DOWNLOAD_GUIDE.md    # Instructions for downloading source images
├── README.md            # This file - documentation of test images
├── simple/              # Low complexity: 3-5 colors, clear boundaries
│   └── (grayscale terrain images)
├── medium/              # Medium complexity: 8-12 colors, varied terrain
│   └── (Natural Earth style maps)
├── complex/             # High complexity: detailed satellite composites
│   └── (Blue Marble style images)
└── projections/         # Different map projections (Mercator, Robinson, etc.)
    └── (projection comparison images)
```

## Test Image Categories

### Simple (Fast Iteration)
**Purpose:** Quick algorithm validation without complex color variations

**Characteristics:**
- 3-5 dominant colors
- Clear land/water boundaries
- Minimal texture or detail
- Grayscale acceptable

**Use Cases:**
- Rapid development iteration
- Basic color quantization validation
- Edge detection testing
- Grayscale-to-RGB conversion testing

**Expected Files:**
- `natural_earth_shaded_relief_512.png` - Quick test (512x512)
- `natural_earth_shaded_relief_1024.png` - Standard test (1024x1024)
- `natural_earth_shaded_relief.tif` - Full resolution source

---

### Medium (Realistic Use Case)
**Purpose:** Representative of actual LEGO World Map user projects

**Characteristics:**
- 8-12 distinct LEGO colors needed
- Varied terrain (forests, deserts, oceans, mountains, ice)
- Recognizable geographic features
- Idealized/stylized Earth representations

**Use Cases:**
- Standard integration testing
- Color palette optimization
- Visual similarity validation
- Documentation examples

**Expected Files:**
- `natural_earth_ii_512.png` - Quick test (512x512)
- `natural_earth_ii_1024.png` - Standard test (1024x1024) **← PRIMARY TEST IMAGE**
- `natural_earth_ii_2048.png` - Performance test (2048x2048)
- `natural_earth_ii_full.tif` - Full resolution source (~185MB, 16200x8100)
- `blue_marble_ng_january_1440.png` - Seasonal variation (optional)
- `blue_marble_ng_july_1440.png` - Seasonal variation (optional)

---

### Complex (Stress Testing)
**Purpose:** Maximum color complexity and performance validation

**Characteristics:**
- Many color variations and gradients
- Clouds, shadows, fine details
- True-color satellite composites
- Large file sizes

**Use Cases:**
- Performance benchmarking
- Color distance algorithm stress testing
- Maximum color palette utilization
- Edge case handling

**Expected Files:**
- `blue_marble_2012_npp_1024.jpg` - Standard complex test (1024x1024)
- `blue_marble_2012_npp_2048.jpg` - High-res complex test (2048x2048)
- `blue_marble_2012_npp_3200.jpg` - Maximum resolution test (optional, large)

---

### Projections (Format Validation)
**Purpose:** Ensure system works with different map projections

**Characteristics:**
- Same geographic content, different projections
- Tests distortion handling
- Validates LEGO World Map kit format compatibility

**Use Cases:**
- Projection-specific testing
- Distortion analysis
- Format compatibility validation

**Expected Files:**
- `mercator_1024.jpg` - Mercator projection (standard cylindrical)
- `robinson_1024.jpg` - Robinson projection (pseudo-cylindrical)

---

## Standard Test Sizes

All test images should be available in these standard sizes:

| Size | Use Case | Processing Time Target |
|------|----------|------------------------|
| 512x512 | Quick iteration | <5 seconds |
| 1024x1024 | Standard testing | <30 seconds |
| 2048x2048 | Performance validation | <120 seconds |
| Full resolution | Production-scale testing | Varies by source |

## Download Instructions

**See `DOWNLOAD_GUIDE.md` for detailed download instructions.**

Quick start:
1. Download Natural Earth II (medium complexity) from naturalearthdata.com
2. Download Blue Marble 2012 from NASA Visible Earth
3. Resize to standard test sizes (512, 1024, 2048) using ImageMagick or Python/Pillow
4. Place in appropriate directories (simple/medium/complex)

## Current Status

**Downloaded Images:** (Update this section as you add images)

- [ ] Simple: Natural Earth Shaded Relief
  - [ ] 512x512
  - [ ] 1024x1024
  - [ ] Full resolution source
- [ ] Medium: Natural Earth II
  - [ ] 512x512
  - [ ] 1024x1024
  - [ ] 2048x2048
  - [ ] Full resolution source
- [ ] Complex: Blue Marble 2012 NPP
  - [ ] 1024x1024
  - [ ] 2048x2048
- [ ] Projections: Mercator/Robinson
  - [ ] Mercator 1024x1024
  - [ ] Robinson 1024x1024

## Image Metadata

**Natural Earth II (Medium)**
- Source: Natural Earth (naturalearthdata.com)
- License: Public Domain (CC0)
- Original Size: 16,200 x 8,100 pixels (184.76 MB)
- Projection: Geographic (WGS84)
- Description: Idealized Earth with restored ecosystems
- Best for: Representative LEGO World Map style testing

**Blue Marble 2012 NPP**
- Source: NASA Visible Earth
- License: Public Domain
- Original Size: Up to 8000 x 8000 pixels
- Projection: Orthographic (approximate)
- Description: True-color satellite composite from NPP satellite
- Best for: Maximum color complexity testing

**Natural Earth Shaded Relief**
- Source: Natural Earth (naturalearthdata.com)
- License: Public Domain (CC0)
- Original Size: 16,200 x 8,100 pixels (24.01 MB)
- Projection: Geographic (WGS84)
- Description: Grayscale terrain elevation with shading
- Best for: Simple baseline testing

## Usage in Tests

### Contract Tests
Use simple images (512x512) to validate CLI input/output contracts quickly.

```python
# Example: cli/tests/contract/test_quantize_contract.py
def test_quantize_basic_contract():
    input_image = "tests/fixtures/images/simple/natural_earth_shaded_relief_512.png"
    # ... validate command accepts input and produces valid output
```

### Integration Tests
Use medium complexity images (1024x1024) for end-to-end workflow testing.

```python
# Example: cli/tests/integration/test_quantization_pipeline.py
def test_full_quantization_pipeline():
    input_image = "tests/fixtures/images/medium/natural_earth_ii_1024.png"
    # ... validate entire pipeline from input to LEGO color output
```

### Performance Benchmarks
Use all size variants to measure processing time scaling.

```python
# Example: cli/tests/unit/test_performance.py
@pytest.mark.benchmark
def test_quantization_performance_scaling():
    sizes = [512, 1024, 2048]
    # ... measure processing time vs. image size
```

## Adding New Test Images

When adding new test images:

1. **Document the source:** Add metadata to this README
2. **Include license info:** Verify public domain/CC0 status
3. **Create standard sizes:** Generate 512, 1024, 2048 versions
4. **Update checklist:** Mark files as downloaded in "Current Status" section
5. **Add to .gitignore:** Large files (>10MB) should not be committed to git
   - Store full-resolution sources externally (Google Drive, S3, etc.)
   - Keep only test-size versions in repo (512, 1024, max 2048)

## .gitignore Recommendations

```gitignore
# Add to cli/tests/fixtures/.gitignore

# Keep only small test images in git (< 5MB each)
images/**/natural_earth_ii_full.tif
images/**/*_full.*
images/**/*_original.*
images/**/*_source.*

# Allow standard test sizes
!images/**/*_512.*
!images/**/*_1024.*
!images/**/*_2048.*

# Keep documentation
!images/**/*.md
!images/**/README.md
!images/**/DOWNLOAD_GUIDE.md
```

## Attribution

When using these test images in documentation or publications:

```
Test imagery:
- Natural Earth by Natural Earth (public domain): naturalearthdata.com
- Blue Marble by NASA/NOAA/GSFC (public domain)
```

## Related Documentation

- `DOWNLOAD_GUIDE.md` - Step-by-step download instructions
- `../../contract/README.md` - Contract test specifications
- `../../integration/README.md` - Integration test specifications
- `../../../README.md` - CLI tool documentation
