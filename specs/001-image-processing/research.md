# Research: Satellite Image to LEGO Color Palette Conversion

**Feature**: 001-image-processing
**Phase**: 0 - Technology Research and Decisions
**Date**: 2026-01-04

## Overview

This document captures research findings and technical decisions for implementing the satellite image to LEGO color quantization CLI tool.

## Research Areas

### 1. Color Distance Algorithm Selection

**Decision**: Use CIE Delta E 2000 (CIEDE2000) for color distance calculations

**Rationale**:
- CIEDE2000 is the most perceptually accurate color difference formula available
- Accounts for human perception variations in different hue regions
- Industry standard for color matching applications
- Better than older CIE76 formula, especially for blues and grays (common in satellite imagery)

**Alternatives Considered**:
- **CIE76 (Delta E 1976)**: Simpler Euclidean distance in LAB space. Rejected because it overestimates differences in blue/saturated colors, which are prevalent in satellite images (water, vegetation).
- **CIEDE94**: Intermediate formula. Rejected because CIEDE2000 is more accurate with minimal performance cost difference.
- **RGB Euclidean Distance**: Simplest approach. Rejected because it doesn't match human perception—equal RGB distances don't look equally different to humans.

**Implementation**: Use scikit-image's `color.deltaE_ciede2000()` function, which provides optimized implementation.

---

### 2. Image Processing Library

**Decision**: Use Pillow (PIL) for image I/O, NumPy for array operations, scikit-image for color conversion

**Rationale**:
- **Pillow**: Industry standard for Python image I/O, supports PNG/JPEG/TIFF, cross-platform, well-maintained
- **NumPy**: Efficient array operations for pixel manipulation, vectorized operations for performance
- **scikit-image**: Provides robust RGB ↔ LAB color space conversion and Delta E calculations

**Alternatives Considered**:
- **OpenCV**: More powerful but heavier dependency, overkill for color quantization task. Rejected for simplicity.
- **imageio**: Lighter than Pillow but less feature-complete. Rejected for ecosystem maturity.
- **Pure NumPy**: Would require manual implementation of color space conversions. Rejected to avoid reinventing tested algorithms.

**Trade-offs**:
- Pillow + scikit-image adds ~50MB to install size, but this is acceptable for desktop CLI tool
- Cross-platform compatibility guaranteed with these mature libraries

---

### 3. CLI Framework

**Decision**: Use Click for command-line interface

**Rationale**:
- Most popular Python CLI framework (argparse is built-in but verbose)
- Excellent argument validation and type conversion
- Automatic help text generation
- Supports command groups (future extensibility for `lego-map quantize`, `lego-map stats`, etc.)
- Great developer experience with decorators

**Alternatives Considered**:
- **argparse**: Built-in, no dependencies. Rejected due to verbose boilerplate and less readable code.
- **Typer**: Modern, uses type hints. Rejected because Click has more extensive documentation and ecosystem.
- **docopt**: Minimalist, defines CLI from docstring. Rejected for less validation and error handling support.

**Implementation Note**: Commands will be organized as a Click group for extensibility.

---

### 4. LEGO World Map Color Palette Source

**Decision**: Manually curate LEGO color palette from official LEGO World Map kit documentation and BrickLink data

**Rationale**:
- LEGO World Map kit uses specific subset of LEGO colors optimized for geographic representation
- Need accurate RGB values and official LEGO color numbers for parts list generation
- One-time curation effort, stored as static JSON file in the package

**Color Data Structure**:
```json
{
  "colors": [
    {
      "id": "LEGO_COLOR_ID",
      "name": "Color Name",
      "rgb": [R, G, B],
      "lab": [L, A, B],
      "part_number": "LEGO_PART_NUMBER"
    }
  ]
}
```

**Data Sources**:
1. Official LEGO World Map kit instructions (primary source for color selection)
2. BrickLink color database (for accurate RGB values and part numbers)
3. Rebrickable API (for validation and cross-reference)

**Estimated Palette Size**: 40-50 distinct colors based on LEGO World Map kit composition

**Alternatives Considered**:
- **Full LEGO color catalog**: ~200+ colors. Rejected because World Map kit uses specific subset.
- **Dynamic palette generation**: Analyze actual LEGO bricks. Rejected as too complex and error-prone.
- **Third-party LEGO APIs**: Unreliable for offline operation. Rejected per constitution requirement.

---

### 5. Color Space Conversion Strategy

**Decision**: Pre-compute LAB values for LEGO palette, convert input images on-the-fly

**Rationale**:
- LEGO palette is fixed (~45 colors), so LAB conversion can be done once during package initialization
- Input images vary, but converting once per image is fast with scikit-image
- Avoids repeated conversions of palette colors (45 colors × millions of pixels)

**Performance Optimization**:
- Store both RGB and LAB values in palette JSON to skip runtime conversion
- Use NumPy vectorized operations for batch pixel conversion
- LAB conversion: RGB → XYZ → LAB (scikit-image handles this)

**Memory Trade-off**: Pre-computed LAB values add ~8KB to palette file (negligible).

---

### 6. Performance Optimization Strategies

**Decision**: Use NumPy broadcasting for vectorized color distance calculations

**Approach**:
1. Load image into NumPy array (H × W × 3)
2. Reshape to (H*W, 3) for vectorized operations
3. Broadcast LEGO palette LAB values (N_colors, 3) against image pixels
4. Compute Delta E for all pixel-color pairs using vectorized operations
5. Find minimum distance for each pixel using `np.argmin()`

**Estimated Performance**:
- 1024×1024 image = 1,048,576 pixels
- 45 LEGO colors
- ~47 million distance calculations
- With NumPy vectorization: ~2-5 seconds on modern CPU

**Alternatives Considered**:
- **Pixel-by-pixel loop**: Rejected, would be 100-1000× slower in Python
- **GPU acceleration (CUDA/OpenCL)**: Rejected as overkill for target performance and adds complex dependencies
- **Cython/Numba JIT**: Considered for future optimization if NumPy performance insufficient

**Benchmark Target**: Process 1024×1024 image in <10 seconds (spec allows 30 seconds, targeting 3× headroom)

---

### 7. Output Image Format

**Decision**: Default to PNG for quantized output, allow user to specify format via CLI flag

**Rationale**:
- PNG is lossless, essential for preserving exact quantized colors
- JPEG would introduce compression artifacts that corrupt color accuracy
- TIFF is lossless but larger file size, less common for end users

**CLI Design**:
```bash
lego-image-processor quantize input.jpg --output output.png
lego-image-processor quantize input.jpg --output output.jpg --format jpeg  # Allow but warn
```

**Warning for Lossy Formats**: Tool will warn users if they choose JPEG output that color accuracy may be affected.

---

### 8. Error Handling and Validation

**Decision**: Fail fast with clear error messages, validate inputs before processing

**Validation Checks**:
1. **File exists**: Check input file path before loading
2. **Valid image format**: Attempt Pillow load, catch format errors
3. **Image size limits**: Check dimensions, reject if >100 megapixels (memory safety)
4. **Color mode**: Convert grayscale to RGB, warn user
5. **Output path writable**: Check output directory exists and is writable

**Error Message Examples**:
- ❌ `Error: Input file 'image.png' not found`
- ❌ `Error: 'image.txt' is not a valid image format (supported: PNG, JPEG, TIFF)`
- ❌ `Error: Image too large (150MP exceeds 100MP limit). Consider downsampling.`
- ⚠️ `Warning: Input image is grayscale, converting to RGB for processing`

---

### 9. Progress Feedback for Long Operations

**Decision**: Use `tqdm` progress bar for operations >2 seconds

**Rationale**:
- `tqdm` is lightweight, widely used, integrates with CLI
- Shows ETA, iteration speed, progress percentage
- Automatically hides for fast operations

**Implementation**:
```python
from tqdm import tqdm

for row in tqdm(image_rows, desc="Quantizing image"):
    # Process each row
```

**Alternatives Considered**:
- **Manual print statements**: Rejected, less informative and harder to maintain
- **Rich console library**: Rejected as heavier dependency for just progress bars
- **No progress feedback**: Rejected per spec requirement (FR-006)

---

### 10. Testing Strategy

**Decision**: Three-tier testing approach (contract, integration, unit)

**Contract Tests** (CLI interface validation):
- Test command-line argument parsing
- Validate JSON and human-readable output formats
- Verify exit codes for success/failure scenarios
- Check help text completeness

**Integration Tests** (end-to-end workflows):
- Test complete image → quantized output pipeline
- Validate output images contain only LEGO colors
- Test batch processing with multiple files
- Use real sample satellite images as fixtures

**Unit Tests** (algorithm correctness):
- Test Delta E calculations against known color pairs
- Validate RGB → LAB conversion accuracy
- Test color quantizer logic with synthetic data
- Validate palette loader with test palette files

**Test Data Requirements**:
- 5-10 sample satellite images (various sizes, color profiles)
- Hand-validated expected outputs for regression testing
- LEGO color palette test fixture
- Synthetic test cases for edge cases (grayscale, single-color, corrupted)

---

## Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Core language (per constitution) |
| Image I/O | Pillow | 10.x | Load/save PNG, JPEG, TIFF |
| Array Ops | NumPy | 1.24+ | Efficient pixel manipulation |
| Color Science | scikit-image | 0.22+ | RGB↔LAB conversion, Delta E |
| CLI Framework | Click | 8.x | Command-line interface |
| Progress Bars | tqdm | 4.x | User feedback for long operations |
| Testing | pytest | 7.x | Unit and integration tests |
| Benchmarking | pytest-benchmark | 4.x | Performance validation |
| Packaging | Poetry | 1.7+ | Dependency management, publishing |

---

## Open Questions Resolved

**Q1: Should we support RAW satellite image formats?**
**A**: No, not in P1. RAW formats (GeoTIFF, HDF, NetCDF) require specialized libraries and are uncommon for hobbyist use. Users can convert to PNG/JPEG/TIFF using standard GIS tools. May revisit in future feature if user demand exists.

**Q2: Should color quantization be lossy or preserve original dimensions exactly?**
**A**: Preserve exact dimensions (lossless resize). Each output pixel corresponds 1:1 with LEGO brick position in final map. Resizing would complicate brick-to-pixel mapping.

**Q3: How to handle alpha channel (transparency) in input images?**
**A**: Composite transparent pixels onto white background before quantization. Satellite images rarely have transparency; this handles edge case of PNG with alpha.

**Q4: Should palette be user-configurable or fixed?**
**A**: Fixed LEGO World Map palette for P1 (MVP). Custom palettes may be added in future feature if users want to work with different LEGO sets. Keeps P1 scope focused.

---

## Performance Benchmarks (Target)

| Image Size | Pixels | Target Time | Memory |
|------------|--------|-------------|--------|
| 512×512 | 262K | <3 seconds | <100MB |
| 1024×1024 | 1.0M | <10 seconds | <200MB |
| 2048×2048 | 4.2M | <20 seconds | <500MB |
| 3200×3200 | 10.2M | <30 seconds | <800MB |

These targets provide 2-3× headroom over spec requirements (30 seconds for 10MP).

---

## Next Steps

With research complete, proceed to Phase 1:
1. Create data-model.md (LEGO color palette structure, image data model)
2. Generate CLI contracts (quantize.json, stats.json, batch.json)
3. Write quickstart.md (installation and usage examples)
