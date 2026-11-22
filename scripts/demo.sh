#!/usr/bin/env bash
# End-to-end demo of the 98138.world CLI: kit data -> maps -> parts lists -> build sheets.
# Usage: scripts/demo.sh [OUTPUT_DIR]     (default: ./demo-output, git-ignored)
# Needs: uv (https://docs.astral.sh/uv/); it fetches Python 3.11 if missing. Downloads two public datasets (~10.5 MB) once.
# See docs/runbook.md for what each step shows. Not affiliated with or endorsed by The LEGO Group.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(mkdir -p "${1:-$ROOT/demo-output}" && cd "${1:-$ROOT/demo-output}" && pwd)"
VENV="$ROOT/cli/.venv"
LIP="$VENV/bin/lego-image-processor"

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "0. Install the CLI into cli/.venv"
if [[ ! -x "$LIP" ]]; then
  (cd "$ROOT/cli" && uv venv -q --python 3.11 && uv pip install -q -e .)  # scikit-image 0.21 needs 3.11
fi
"$LIP" --version

step "1. Kit 31203 reference data (from the official instructions, cited)"
"$LIP" kit inventory
"$LIP" kit colors

step "2. Bundled map recipes"
"$LIP" map recipes

step "3. Official design, rebuilt exactly from its recipe (offline)"
"$LIP" map build official-31203 -o "$OUT/official.json" --preview "$OUT/official.png"
"$LIP" validate "$OUT/official.json"

step "4. Fetch the pinned datasets (ETOPO 2022 subset, ERSST v5 normals; checksum-verified)"
"$LIP" dataset fetch --recipe ocean-sst
"$LIP" dataset fetch --recipe land-elevation
"$LIP" dataset list

step "5. Data maps: bathymetry, sea surface temperature, land elevation"
for r in official-31203-bathymetry ocean-sst land-elevation; do
  "$LIP" map build "$r" -o "$OUT/$r.json" --preview "$OUT/$r.png" --report "$OUT/$r-report.json"
done
"$LIP" validate "$OUT/land-elevation.json" || true   # beyond-kit colors are expected here

step "6. Parts lists and kit top-up for the elevation map"
"$LIP" parts list "$OUT/land-elevation.json"
"$LIP" parts list "$OUT/land-elevation.json" --kits 1

step "7. Marketplace exports (pieces needed beyond one kit)"
"$LIP" parts export "$OUT/land-elevation.json" --kits 1 \
  --bricklink "$OUT/land-elevation-bricklink.xml" --rebrickable "$OUT/land-elevation-rebrickable.csv"

step "8. Build sheets (PDF, plus SVG pages)"
"$LIP" sheets build "$OUT/official.json" -o "$OUT/official-sheets.pdf"
"$LIP" sheets build "$OUT/land-elevation.json" -o "$OUT/land-elevation-sheets.pdf"
"$LIP" sheets build "$OUT/ocean-sst.json" -o "$OUT/ocean-sst-svg" --format svg
"$LIP" sheets counts "$OUT/official.json" | head -20

step "9. Make your own recipe"
"$LIP" map recipes --copy ocean-sst "$OUT/my-sst.toml" --force
"$LIP" map check "$OUT/my-sst.toml"

step "Done. Outputs in $OUT"
ls -1 "$OUT"
