# Contract: sticker files (print sheet PDF, SVG, JSON summary)

Same input, same bytes (FR-012): no timestamps; ReportLab `invariant=1`; SVG numbers with two
decimals, fixed attribute order, `\n` line endings. No image, logo, wordmark or LEGO label
artwork anywhere. Not affiliated with or endorsed by The LEGO Group.

## Geometry (mm)

| | Small | Large |
|---|---|---|
| Plaque tile | 6 × 6, part 10202 | 16 × 8 (landscape), part 4974 (smooth) |
| Tile (nominal, studs × 8.0 − 0.2) | 47.8 × 47.8 | 127.8 × 63.8 |
| Cut line (sticker) | 45.8 × 45.8 | 125.8 × 61.8 |
| Bleed past the cut | 2.0 | 2.0 |
| Cut marks | 1.0 gap, 4.0 long, 0.25 wide, 8 per sticker | same |
| Safe area (text) | 2.5 inside the cut: 40.8 × 40.8 | 120.8 × 56.8 |
| Canvas (SVG) | 59.8 × 59.8 | 139.8 × 75.8 |

Tests require every cut line within 0.1 mm of these sizes in the page model, the SVG and the PDF
(SC-001).
The large tile is the smooth 4974, chosen by the project owner on 2026-11-24 in place of the
textured 90498; it has the same 8 × 16 footprint, so every size above is unchanged.

## Sticker content

- Background and bleed: cited sRGB of `lego_black` (5, 19, 29); text White (255, 255, 255).
- Small: title (bold, 11 pt preferred), line (7 pt), disclaimer (5 pt); centred.
- Large: title (bold, 14 pt) and "98138.world" (bold, 7 pt, right); line (7 pt); legend
  (group headings "Land" and "Ocean", 6 pt bold; swatches Ø 2.8 mm in cited sRGB with a 0.15 mm
  outline RGB 210, 210, 210, plates with an inner ring; labels 6 pt); "Data:" credit lines
  (5.5 pt); disclaimer (5.5 pt).
- Minimum text size 5 pt; text wraps, then shrinks; never truncated.
- Item tags (page model and SVG `class`): `sticker-bg`, `bleed`, `title`, `line`, `site`,
  `legend-heading`, `swatch`, `swatch-ring`, `legend-label`, `credit`, `disclaimer`,
  `cut-mark`, `cut-line`; swatches carry `data-layer`, `data-color`, `data-part`.

## Print sheet (PDF)

`stickers-<paper>.pdf` (CLI: the file `-o`), one portrait page, Letter 215.9 × 279.4 or A4
210 × 297, 12 mm margins.

| Block | Content |
|---|---|
| Header | "Map stickers: <sticker title>"; "Two stickers for Black tiles: print on white sticker paper at 100%, cut along the marks." |
| Large sticker | cut line at (19.0, 41.0), bleed, marks; caption "Large sticker 125.8 x 61.8 mm, for a Black tile 8 x 16 (about 127.8 x 63.8 mm)" |
| Small sticker | cut line at (19.0, 118.8), bleed, marks (2 mm clear of the large sticker's marks); caption with its sizes |
| Plaque parts | per plaque: 1 tile and, standalone, 1 plate: name, Black, LEGO element and design, BrickLink item and color (id), Rebrickable part and color (id); "The sticker is printed, not a LEGO part." |
| Notes | how to cut and place (about 1 mm of tile shows on every side); "Printed colors only approximate the LEGO colors." |
| Data | per dataset: id, version, title, citation, license (and acknowledgement) |
| Provenance | recipe id and SHA-256; legend values from the build hung as <C>; template line (non-kit, 016's wording); "Made with lego-image-processor <version>. Drawn from the recipe and the map's data; no LEGO artwork, logo or image." |
| Furniture | 100 mm scale bar, "Print at 100% (no fit-to-page)", footer title, "Page 1 of 1", disclaimer (the build sheets' `furniture()`) |

PDF metadata: title "Map stickers: <sticker title>", author "98138.world", subject
"Map stickers for 98138.world. Not affiliated with or endorsed by The LEGO Group.", creator
"lego-image-processor <version>". Fonts Helvetica and Helvetica-Bold, not embedded, Latin-1.
Cut lines are unpainted rectangles (`re n`) of the cut size.

## SVG files

`sticker-small.svg`, `sticker-large.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="139.80mm" height="75.80mm" viewBox="0 0 139.80 75.80" font-family="Helvetica, Arial, sans-serif">
<title>Large sticker: Ocean temperature (98138.world)</title>
<desc>Not affiliated with or endorsed by The LEGO Group.</desc>
<metadata>Recipe ocean-sst (SHA-256 …). Data: ersst-v5-ltm-1991-2020 (v5-ltm-1991-2020): <title>. <citation> License: <license>. … Made with lego-image-processor <version>.</metadata>
<rect x="0" y="0" width="139.80" height="75.80" fill="#ffffff"/>
<rect ... class="bleed"/> … cut marks … sticker content …
<text ... textLength="18.42" lengthAdjust="spacingAndGlyphs" ...>11 to 16 °C</text>
<g id="cut-line"><rect x="7.00" y="7.00" width="125.80" height="61.80" fill="none" stroke="#ff00ff" stroke-width="0.10" class="cut-line"/></g>
</svg>
```

Every `<text>` carries `textLength` (its Helvetica width in mm) and
`lengthAdjust="spacingAndGlyphs"`. Any Unicode text is allowed in SVG.

`<metadata>` (not drawn) carries, as escaped text, the recipe id and SHA-256, each dataset's id,
version, title, full citation and license (and acknowledgement), and the tool version, so the SVG
set meets constitution IV on its own, as the print sheet does. It holds nothing that depends on
the arrangement, so the SVG files of A, B and C builds are byte-identical.

## Same set for A, B and C (SC-003)

The stickers are the same for A, B and C: `to_dict()` without `arrangement` and both SVG files
are identical. `arrangement` in the JSON summary and the print sheet's provenance line "legend
values from the build hung as <C>" record the build the legend values came from, so the JSON and
PDF bytes are identical only within one arrangement.

## JSON summary (format "1")

Written by `map stickers --format json` and used by the web prebuild; `ensure_ascii=False`,
indent 2, keys in this order.

| Field | Type | Notes |
|---|---|---|
| `format_version` | `"1"` | |
| `recipe` | `{id, title, sha256}` | |
| `template` | `{id}` (kit: `"kit-31203"`); after 016 `{id, title, projection, dataset}` | |
| `arrangement` | `"A"｜"B"｜"C"` | the build the legend values come from; the only field that differs between A, B and C sets |
| `text` | `{title, title_source, line, line_source}` | sources: `sticker table`, `recipe title`, `recipe description` |
| `stickers.small`, `stickers.large` | `{plaque, tile_mm, cut_mm, bleed_mm, safe_mm, blocks: [{field, lines, size_pt}]}` | |
| `legend` | `[{layer, part_id, color, lego_name, rgb, meanings: [{kind, label, range?, units?, source?, step?}]}]` | data-model.md Swatch, Meaning |
| `credits` | `[{dataset, version, text, title, doi, publisher, citation, license, acknowledgement?}]` | |
| `plaques` | `[{size, studs, sticker_mm, parts: [{role: "tile"｜"plate", quantity: 1, part_id, name, color: {key, lego{name,id}, bricklink{name,id}, rebrickable{name,id}}, element_id, lego_design_ids, bricklink_item, rebrickable_part, citations}]}]` | small, large |
| `notes` | `{printed, colors}` | "The sticker is printed, not a LEGO part."; "Printed colors only approximate the LEGO colors." |
| `tool_version`, `disclaimer` | string | |
