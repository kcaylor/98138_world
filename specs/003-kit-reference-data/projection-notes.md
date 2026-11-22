# Projection notes: kit 31203 design grid (FR-017)

**Feature**: 003-kit-reference-data | **Source**: committed `cli/src/lego_image_processor/data/kit_31203_design.json`
(rows `y` = 0 at the top, columns `x` = 0 at the left) | **Research**: R12

Observations only. Determining the projection is out of scope for this feature and is left to
feature 004.

## General shape (research R12)

- 128 columns span the full longitude range (about 2.81° per column). The Americas are at the
  left; the left and right edges are both in the Pacific.
- The three frames split the map at columns 32 and 96 (2 + 4 + 2 sections of 16 columns).
- Rows 0–4 hold no land. The northernmost land is in row 5 (northern Greenland and the Canadian
  Arctic islands).
- Rows 66–71 hold no land. Antarctica begins at row 72 and fills the bottom rows as a continuous
  white band to row 79, so the southern edge is cropped inside Antarctica.
- Greenland and the high-latitude land masses are strongly enlarged compared with an equal-area
  map, consistent with a cylindrical projection.

## Latitudes of identifiable features, measured on the grid

Rows are the row of the feature's extreme land cell (white) on the committed grid; the latitude
is the feature's real latitude.

| Feature | Grid cells | Row | Latitude |
|---|---|---|---|
| Northernmost land (assumed Cape Morris Jesup, Greenland) | x 28–51 | 5 | 83.6° N |
| Northern tip of South America (Punta Gallinas) | x 32–33 | ≈ 37.5 | 12.5° N |
| Southern tip of Africa (Cape Agulhas) | x 67–68 | 56 | 34.8° S |
| Southern tip of South America (Cape Horn) | x 35–36 | 65 | 56.0° S |
| Antarctic coast (first continuous band) | x 51–120 | 73–74 | coast varies (about 65–78° S); not used in the fit |

The row for Punta Gallinas is uncertain by about one row (the coast is ragged at 1-stud
resolution).

## Fit of row against latitude (4 features above, least squares)

| Model | Equator row | Residuals (rows) |
|---|---|---|
| Miller cylindrical | 43.2 | 0.5, −1.4, 0.4, 0.4 |
| Equirectangular | 41.4 | −0.6, 1.4, −0.4, −0.4 |
| Mercator | 45.5 | 1.5, −4.8, 1.0, 2.2 |

Mercator fits clearly worse. Miller and equirectangular fit about equally well at this resolution;
four features at 1-stud precision cannot separate them. The equator sits at roughly row 41–43,
below the grid's middle row (40), so the map shows more of the northern hemisphere than the
southern. Feature 004 should fit more features (for example coastline cells of Africa, Australia
and the Mediterranean) before choosing a projection.

Not affiliated with or endorsed by The LEGO Group.
