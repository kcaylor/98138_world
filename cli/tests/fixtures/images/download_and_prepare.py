#!/usr/bin/env python3
"""
Download and prepare test images for LEGO World Map testing.

This script downloads public domain global map imagery from Natural Earth
and NASA, then creates standardized test sizes (512x512, 1024x1024, 2048x2048).

Usage:
    python download_and_prepare.py [--all] [--simple] [--medium] [--complex]

    --all      Download all test images (default)
    --simple   Download only simple test images
    --medium   Download only medium complexity images
    --complex  Download only complex test images
"""

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple, List

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


# Base directory for test fixtures
FIXTURES_DIR = Path(__file__).parent
SIMPLE_DIR = FIXTURES_DIR / "simple"
MEDIUM_DIR = FIXTURES_DIR / "medium"
COMPLEX_DIR = FIXTURES_DIR / "complex"

# Test image sizes to generate
TEST_SIZES: List[Tuple[int, int]] = [
    (512, 512),
    (1024, 1024),
    (2048, 2048),
]


def download_file(url: str, destination: Path) -> bool:
    """Download a file from URL to destination path."""
    print(f"Downloading: {url}")
    print(f"         to: {destination}")

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, destination)
        print(f"✓ Downloaded ({destination.stat().st_size / 1024 / 1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def extract_zip(zip_path: Path, extract_dir: Path) -> bool:
    """Extract a zip file to a directory."""
    print(f"Extracting: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"✓ Extracted to {extract_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def create_test_sizes(source_image: Path, output_prefix: str, output_dir: Path) -> None:
    """Create standardized test size versions of an image."""
    print(f"\nCreating test sizes from: {source_image.name}")

    try:
        img = Image.open(source_image)
        print(f"  Original size: {img.size[0]} x {img.size[1]}")

        for width, height in TEST_SIZES:
            output_path = output_dir / f"{output_prefix}_{width}.png"

            # Skip if already exists
            if output_path.exists():
                print(f"  ✓ {width}x{height} already exists, skipping")
                continue

            # Resize with high-quality resampling
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            resized.save(output_path, "PNG", optimize=True)

            size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"  ✓ Created {width}x{height} ({size_mb:.2f} MB)")

        print(f"✓ All test sizes created for {output_prefix}")

    except Exception as e:
        print(f"✗ Failed to create test sizes: {e}")


def download_natural_earth_shaded_relief() -> None:
    """Download Natural Earth Shaded Relief (simple, grayscale)."""
    print("\n" + "="*60)
    print("SIMPLE: Natural Earth Shaded Relief (Grayscale)")
    print("="*60)

    url = "https://naturalearth.s3.amazonaws.com/10m_raster/SR_LR.zip"
    zip_path = SIMPLE_DIR / "SR_LR.zip"

    # Download
    if not download_file(url, zip_path):
        print("⚠ Manual download required - see DOWNLOAD_GUIDE.md")
        return

    # Extract
    extract_dir = SIMPLE_DIR / "SR_LR"
    if extract_zip(zip_path, extract_dir):
        # Find the .tif file
        tif_files = list(extract_dir.glob("**/*.tif"))
        if tif_files:
            source_tif = tif_files[0]
            # Move to fixtures directory
            destination = SIMPLE_DIR / "natural_earth_shaded_relief.tif"
            source_tif.rename(destination)
            print(f"✓ Moved source file to {destination.name}")

            # Create test sizes
            create_test_sizes(destination, "natural_earth_shaded_relief", SIMPLE_DIR)

        # Cleanup
        import shutil
        shutil.rmtree(extract_dir)
        zip_path.unlink()
        print("✓ Cleaned up temporary files")


def download_natural_earth_ii() -> None:
    """Download Natural Earth II (medium complexity, natural colors)."""
    print("\n" + "="*60)
    print("MEDIUM: Natural Earth II (Natural Colors)")
    print("="*60)

    url = "https://naturalearth.s3.amazonaws.com/10m_raster/NE2_LR_LC_SR_W.zip"
    zip_path = MEDIUM_DIR / "NE2_LR_LC_SR_W.zip"

    # Download (large file - 185MB)
    print("⚠ This is a large file (185 MB) - may take a few minutes...")
    if not download_file(url, zip_path):
        print("⚠ Manual download required - see DOWNLOAD_GUIDE.md")
        return

    # Extract
    extract_dir = MEDIUM_DIR / "NE2_LR_LC_SR_W"
    if extract_zip(zip_path, extract_dir):
        # Find the .tif file
        tif_files = list(extract_dir.glob("**/*.tif"))
        if tif_files:
            source_tif = tif_files[0]
            destination = MEDIUM_DIR / "natural_earth_ii_full.tif"
            source_tif.rename(destination)
            print(f"✓ Moved source file to {destination.name}")

            # Create test sizes
            create_test_sizes(destination, "natural_earth_ii", MEDIUM_DIR)

        # Cleanup
        import shutil
        shutil.rmtree(extract_dir)
        zip_path.unlink()
        print("✓ Cleaned up temporary files")


def download_blue_marble_2012() -> None:
    """Download Blue Marble 2012 NPP (complex, high detail)."""
    print("\n" + "="*60)
    print("COMPLEX: Blue Marble 2012 NPP")
    print("="*60)

    # NASA URLs for different sizes
    urls = {
        1024: "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57723/bluemarble-2012-1024.jpg",
        2048: "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57723/bluemarble-2012-2048.jpg",
        3200: "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57723/bluemarble-2012-3200.jpg",
    }

    print("⚠ NASA direct URLs may not work - trying alternative approach...")
    print("⚠ If download fails, manual download required from:")
    print("   https://visibleearth.nasa.gov/images/57723")
    print()

    # Try downloading the 1024 version
    for size, url in urls.items():
        if size > 2048:  # Skip very large files
            continue

        destination = COMPLEX_DIR / f"blue_marble_2012_npp_{size}.jpg"
        if destination.exists():
            print(f"✓ {size}px version already exists")
            continue

        if download_file(url, destination):
            print(f"✓ Downloaded {size}px version")
            # Create 512 version from this
            if size == 1024:
                create_test_sizes(destination, "blue_marble_2012_npp", COMPLEX_DIR)
        else:
            print(f"⚠ Could not download {size}px version automatically")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and prepare test images for LEGO World Map testing"
    )
    parser.add_argument("--all", action="store_true", help="Download all test images (default)")
    parser.add_argument("--simple", action="store_true", help="Download simple test images")
    parser.add_argument("--medium", action="store_true", help="Download medium complexity images")
    parser.add_argument("--complex", action="store_true", help="Download complex test images")

    args = parser.parse_args()

    # Default to --all if no specific category selected
    download_all = args.all or not (args.simple or args.medium or args.complex)

    print("="*60)
    print("LEGO World Map Test Image Downloader")
    print("="*60)
    print()
    print("This script will download public domain satellite imagery")
    print("from Natural Earth and NASA for testing purposes.")
    print()
    print(f"Download directory: {FIXTURES_DIR}")
    print()

    # Create directories
    SIMPLE_DIR.mkdir(parents=True, exist_ok=True)
    MEDIUM_DIR.mkdir(parents=True, exist_ok=True)
    COMPLEX_DIR.mkdir(parents=True, exist_ok=True)

    # Download requested categories
    if download_all or args.simple:
        download_natural_earth_shaded_relief()

    if download_all or args.medium:
        download_natural_earth_ii()

    if download_all or args.complex:
        download_blue_marble_2012()

    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Verify images downloaded correctly in:")
    print(f"   {FIXTURES_DIR}")
    print("2. Update README.md checklist to mark downloaded images")
    print("3. Run your first test:")
    print("   lego-image-processor quantize tests/fixtures/images/medium/natural_earth_ii_1024.png -o output.png")
    print()
    print("For manual downloads (if automated downloads failed):")
    print("   See DOWNLOAD_GUIDE.md for detailed instructions")
    print()


if __name__ == "__main__":
    main()
