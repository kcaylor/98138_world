# Test Image Download Guide

This guide shows you how to download global map test images for the LEGO World Map project.

## Quick Start (Recommended Downloads)

Download these 3-4 images to get a good test coverage:

### 1. Natural Earth II (Medium Complexity) - RECOMMENDED
**Best representative of LEGO World Map style**

1. Go to: https://www.naturalearthdata.com/downloads/10m-raster-data/10m-natural-earth-2/
2. Download **"Medium size"** (16,200 x 8,100 pixels)
   - File: `NE2_LR_LC_SR_W.zip` (184.76 MB)
   - Click the download link on the page
3. Extract the `.tif` file from the zip
4. Save to: `cli/tests/fixtures/images/medium/natural_earth_ii_full.tif`

**What it shows:** Idealized Earth with restored ecosystems - forests, deserts, oceans, ice caps
**Why useful:** Represents the typical LEGO World Map aesthetic with clear biomes and terrain

---

### 2. Blue Marble 2012 NPP (High Complexity)
**Most detailed single-shot Earth image**

1. Go to: https://visibleearth.nasa.gov/images/57723/the-blue-marble-land-surface-ocean-color-and-sea-ice
2. Scroll to "Download Options"
3. Download **"1024 x 1024"** JPEG (smallest for quick testing)
   - Or download **"3200 x 3200"** for high-res testing
4. Save to: `cli/tests/fixtures/images/complex/blue_marble_2012_npp_1024.jpg`

**Alternative download:**
- NASA SVS: https://svs.gsfc.nasa.gov/30002
- Look for "Blue Marble Next Generation" images

**What it shows:** True-color satellite composite with clouds, ice, terrain detail
**Why useful:** Stress test for color quantization with maximum color complexity

---

### 3. Natural Earth Shaded Relief (Simple - Grayscale)
**Basic land/ocean boundaries**

1. Go to: https://www.naturalearthdata.com/downloads/10m-raster-data/10m-shaded-relief/
2. Download **"Medium size"** (16,200 x 8,100 pixels)
   - File: `SR_LR.zip` (24.01 MB)
3. Extract the `.tif` file
4. Save to: `cli/tests/fixtures/images/simple/natural_earth_shaded_relief.tif`

**What it shows:** Grayscale elevation/terrain with simple shading
**Why useful:** Tests grayscale-to-RGB conversion and basic quantization without color complexity

---

### 4. Blue Marble Monthly Variation (Optional)
**Seasonal testing**

1. Go to: https://neo.gsfc.nasa.gov/view.php?datasetId=BlueMarbleNG-TB
2. Click on a month (January or July recommended for max contrast)
3. Select resolution: **1440 x 720** or **3600 x 1800**
4. Click "Download" and choose PNG format
5. Save to: `cli/tests/fixtures/images/medium/blue_marble_ng_january_1440.png`

**What it shows:** Seasonal variation (snow cover, vegetation cycles, dry/wet seasons)
**Why useful:** Tests how well quantization handles seasonal color changes

---

## Alternative: Script-Based Download

If you prefer automation, here's a download script approach:

### Using Natural Earth Direct URLs

Natural Earth files are available through their direct hosting. You can download via command line:

```bash
# Navigate to the project root
cd /Users/kellycaylor/dev/98138_world

# Download Natural Earth II (Medium)
curl -o cli/tests/fixtures/images/medium/NE2_LR_LC_SR_W.zip \
  "https://naturalearth.s3.amazonaws.com/10m_raster/NE2_LR_LC_SR_W.zip"
unzip cli/tests/fixtures/images/medium/NE2_LR_LC_SR_W.zip -d cli/tests/fixtures/images/medium/
mv cli/tests/fixtures/images/medium/NE2_LR_LC_SR_W/NE2_LR_LC_SR_W.tif cli/tests/fixtures/images/medium/natural_earth_ii_full.tif
rm -rf cli/tests/fixtures/images/medium/NE2_LR_LC_SR_W cli/tests/fixtures/images/medium/NE2_LR_LC_SR_W.zip

# Download Natural Earth Shaded Relief (Simple)
curl -o cli/tests/fixtures/images/simple/SR_LR.zip \
  "https://naturalearth.s3.amazonaws.com/10m_raster/SR_LR.zip"
unzip cli/tests/fixtures/images/simple/SR_LR.zip -d cli/tests/fixtures/images/simple/
mv cli/tests/fixtures/images/simple/SR_LR/SR_LR.tif cli/tests/fixtures/images/simple/natural_earth_shaded_relief.tif
rm -rf cli/tests/fixtures/images/simple/SR_LR cli/tests/fixtures/images/simple/SR_LR.zip
```

**Note:** AWS S3 URLs may change. Check https://www.naturalearthdata.com if these fail.

---

## Creating Test Sizes

Once you have the full-resolution images, create smaller versions for faster testing:

```bash
# Install ImageMagick (if not already installed)
# macOS: brew install imagemagick
# Ubuntu: sudo apt-get install imagemagick

# Create 512x512 versions (fast testing)
convert cli/tests/fixtures/images/medium/natural_earth_ii_full.tif \
  -resize 512x512 \
  cli/tests/fixtures/images/medium/natural_earth_ii_512.png

# Create 1024x1024 versions (standard testing)
convert cli/tests/fixtures/images/medium/natural_earth_ii_full.tif \
  -resize 1024x1024 \
  cli/tests/fixtures/images/medium/natural_earth_ii_1024.png

# Create 2048x2048 versions (performance testing)
convert cli/tests/fixtures/images/medium/natural_earth_ii_full.tif \
  -resize 2048x2048 \
  cli/tests/fixtures/images/medium/natural_earth_ii_2048.png
```

Or using Python with Pillow:

```python
from PIL import Image

# Open full-resolution image
img = Image.open("cli/tests/fixtures/images/medium/natural_earth_ii_full.tif")

# Create test sizes
sizes = [(512, 512), (1024, 1024), (2048, 2048)]
for width, height in sizes:
    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    resized.save(f"cli/tests/fixtures/images/medium/natural_earth_ii_{width}.png")
```

---

## Expected Directory Structure

After downloading and resizing, your fixtures directory should look like:

```
cli/tests/fixtures/images/
├── DOWNLOAD_GUIDE.md (this file)
├── README.md (documentation of what each image contains)
├── simple/
│   ├── natural_earth_shaded_relief.tif (full resolution)
│   ├── natural_earth_shaded_relief_512.png
│   └── natural_earth_shaded_relief_1024.png
├── medium/
│   ├── natural_earth_ii_full.tif (full resolution ~185MB)
│   ├── natural_earth_ii_512.png
│   ├── natural_earth_ii_1024.png
│   ├── natural_earth_ii_2048.png
│   ├── blue_marble_ng_january_1440.png (optional)
│   └── blue_marble_ng_july_1440.png (optional)
├── complex/
│   ├── blue_marble_2012_npp_1024.jpg
│   ├── blue_marble_2012_npp_2048.jpg (optional)
│   └── blue_marble_2012_npp_3200.jpg (optional - large file)
└── projections/
    ├── mercator_1024.jpg (to be added later)
    └── robinson_1024.jpg (to be added later)
```

---

## All Sources Reference

### Natural Earth Data
- **Website:** https://www.naturalearthdata.com
- **Raster Downloads:** https://www.naturalearthdata.com/downloads/10m-raster-data/
- **License:** Public Domain (CC0)
- **Best for:** Idealized Earth representations, clean biome boundaries

### NASA Visible Earth
- **Website:** https://visibleearth.nasa.gov
- **Blue Marble Collection:** https://visibleearth.nasa.gov/collection/1484/blue-marble
- **License:** Public Domain (unless otherwise noted)
- **Best for:** High-resolution true-color satellite composites

### NASA Earth Observatory
- **Website:** https://earthobservatory.nasa.gov
- **Blue Marble NG:** https://neo.gsfc.nasa.gov/view.php?datasetId=BlueMarbleNG-TB
- **License:** Public Domain
- **Best for:** Monthly variations, topography/bathymetry overlays

### NOAA Science On a Sphere
- **Website:** https://sos.noaa.gov
- **Blue Marble Dataset:** https://sos.noaa.gov/catalog/datasets/blue-marble/
- **License:** Public Domain
- **Best for:** Simplified global composites

---

## Troubleshooting

### Downloads failing?
- Natural Earth: Check their GitHub mirror: https://github.com/nvkelso/natural-earth-vector
- NASA images: Try right-click → "Save Image As" in your browser
- Use a download manager for large files (>100MB)

### Images too large?
- Start with smaller versions (512x512 or 1024x1024)
- Use ImageMagick or Python/Pillow to resize
- GeoTIFF files can be converted to PNG/JPEG to reduce size

### Format issues?
- All images should work as PNG, JPEG, or TIFF
- If you get GeoTIFF errors, convert to regular TIFF or PNG
- Use GDAL tools for advanced format conversion: `gdal_translate -of PNG input.tif output.png`

---

## License & Attribution

All recommended test images are **Public Domain** or **CC0 licensed**:

- **Natural Earth:** Public domain, no attribution required (but appreciated)
- **NASA imagery:** Public domain, suggest attribution: "NASA/NOAA"
- **NOAA data:** Public domain, suggest attribution: "NOAA"

**Recommended attribution for project documentation:**
```
Test imagery sources:
- Natural Earth (public domain): naturalearthdata.com
- NASA Blue Marble (public domain): NASA/NOAA/GSFC
```

---

## Next Steps

1. Download at least one image from each category (simple, medium, complex)
2. Create resized versions (512, 1024, 2048) using the scripts above
3. Update `cli/tests/fixtures/images/README.md` with details of what you downloaded
4. Run your first quantization test: `lego-image-processor quantize <test-image> -o output.png`
5. Verify output contains only LEGO colors

**Minimum viable test set:** Natural Earth II (medium) at 1024x1024 is sufficient to start development.
