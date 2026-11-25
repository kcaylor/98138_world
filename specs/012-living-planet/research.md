# Research: Living planet map (012)

## R1. Reading the 385 MB NPP GeoTIFF without a full decode

- File (verified 2026-11-22): 43200 × 16800 uint16, LZW (compression 5), no predictor, one row per
  strip (16,800 strips), ModelTiepoint (0, 0, 0, −180, 80, 0), ModelPixelScale (1/120, 1/120),
  80° N to 60° S, scale 0.1 g C m⁻² yr⁻¹, fill 65535 (the prototype treated ≥ 65500 as non-vegetated).
- A full Pillow decode needs ≈1.4 GB for the pixels alone. Decision: parse the TIFF header and IFD
  ourselves (struct), then decode each band of `block` rows by handing Pillow a minimal in-memory
  TIFF that contains only those strips (same tags, rebased offsets). Pillow's bundled libtiff does
  LZW/Deflate and predictors; memory per band is `block × width × 8` bytes (≈4 MB at block 12).
  No new dependency (tifffile/imagecodecs rejected: new dependencies for one reader).
- Block mean: mean of valid pixels (`valid_min ≤ raw ≤ valid_max`, not `fill`) per block, then
  `scale_factor`/`add_offset`; NaN where a block has no valid pixel. Block centres:
  `lat0 − (i + 0.5)·d·block`, as in the prototype's `prep_npp.py`.

## R2. Pinning ERDDAP chlorophyll

- ERDDAP writes the request time into the global `history` attribute (two requests of the same URL
  on 2026-11-22 differ; ERDDAP caches results for a short while, so back-to-back requests can
  match). File SHA-256 pins are therefore not reproducible. Sizes are stable (fixed-width text).
- Options: (a) file SHA-256 + manual re-pin (breaks every fetch); (b) content checksum over the
  decoded data; (c) maintainer-built derived file (needs hosting; we host nothing).
  Decision: (b). `content_sha256` = SHA-256 over, for the variable and then each of its dimension
  coordinate variables in order: `name`, NUL, dtype string, NUL, shape, NUL, then the raw stored
  (big-endian) bytes. Global and variable attributes are excluded. Size stays pinned. A mismatch
  means the data changed: re-verify (compare with the previous cache), re-pin with a new `version`.
- One request for 2013-01..2024-12 at stride 12 in latitude and longitude (≈0.5°, 360 × 720)
  replaces the prototype's 12 yearly requests; it returns the same 142 months.
- Climatology mean: per pixel, linear mean over valid months (high-latitude summers count), then
  log10 (`transform`). The existing `annual-mean` needs all 12 months and stays as it is.

## R3. HTTP-only NTSG host

- `https://files.ntsg.umt.edu/...` times out; `http://` serves the file (Last-Modified
  2016-07-02, 384,939,658 bytes, SHA-256 `cba00628…ffef`). Decision: registry rule "download URLs
  use https unless the entry has `http_only` (a non-empty reason); such entries need `sha256`".
  The SHA-256 makes tampering detectable; the cost is confidentiality of a public file (none).
  Logged for owner review (security-adjacent).

## R4. Land/ocean split for NPP

- The NTSG file stores ocean, barren land, ice and urban all as 65535. The prototype took land
  pixels from ETOPO 2022 (z > 0) at 10′. Decision: `class_rule.land_from = {"dataset":
  "etopo2022-surface-10m", "variable": "z", "split_at": 0}`; the reader looks up the nearest mask
  cell for each source pixel (regular grids: index arithmetic; else searchsorted). Before
  masking, the source grid is extended to the mask's latitude range at the same spacing (missing
  rows), so Antarctica becomes land with no value (NPP 0, unvegetated → ice), as in the prototype.

## R5. No-data rules versus the prototype

- Land (prototype `proto.py`): missing land pixels → 0; ice if the mean over the cell's land pixels
  of `missing ∧ |pixel lat| > 55` exceeds 0.5 → `rule = "share"`, `min_lat = 55`,
  `min_share = 0.5`, `value = 0`.
- Ocean (prototype `proto2.py`, `proto5.py`): White if the cell had no valid value and |cell lat| >
  60, or |cell lat| > 70 and the largest valid-month count among its source pixels < 12 → `rule =
  "unobserved"`, `min_lat = 60`, `sparse_lat = 70`, `min_steps = 12`. Shadow cells stay Black.
- Differences to expect: the prototype reprojected each field over all cells of the class
  (shadow and ice included) and nearest-filled from those; the build fills only from the layer's
  own data cells. The ETOPO lookup in the prototype used `searchsorted` (the next mask row/column),
  the reader uses the nearest cell. Both affect only coastal or filled cells; SC-001 measures it.

## R6. Fixtures

- `mod17a3_npp_1deg.tif`: the real file's 120×120 block means (raw ×10 codes, fill 65535), 1°
  (360 × 140), uint16 LZW strips written by Pillow, with the GeoTIFF tags; read with `block = 2`
  in tests (2°).
- `modis_chla_4deg_6mo.nc`: six months (2023-01, -03, -05, -07, -09, -11) of the pinned request at
  every 8th row/column (4°, 45 × 90), float32 `chlor_a(time, latitude, longitude)` with NaN fill,
  as ERDDAP writes it. Content checksum computed by the conftest.
- Budget raised from 300 kB to 450 kB (test rule in `test_no_large_data.py`).

Not affiliated with or endorsed by The LEGO Group.
