# Research: Parts Lists and Ordering (005)

All pages below were fetched on 2026-11-22 with `curl` from the Internet Archive's raw (`id_`)
copies, because www.bricklink.com redirected to `maintenance.bricklink.com/recovery.html` that day
and rebrickable.com returns HTTP 402 to automated clients (and its terms forbid scraping live
pages). SHA-256 values are of the decoded HTML. Nothing below is committed; the maintainer tool
(plan) re-fetches and checks these hashes. Working copies: session scratchpad `web005/`.

## R1. Part numbers on each marketplace (resolves the 6141 / 4073 question)

| Source (archived) | Finding |
|---|---|
| BrickLink catalog item P=4073, `web.archive.org/web/20261104074336id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=4073`, SHA-256 `957f23bd90a68006f3cbf7f1f4461a6d5de89f2b9b6ed67b5b14533db0b2c146` | Title "Plate, Round 1 x 1 : Part 4073"; "Item No: 4073 Alternate Item No: 6141, 15570, 30057, 34823, 39799, 44325, 51809, 54003, 113470" |
| BrickLink catalog item P=98138, `web.archive.org/web/20260901170641id_/https://www.bricklink.com/v2/catalog/catalogitem.page?P=98138`, SHA-256 `d1683255e9ecb05ade31884614beb278526aed13efb5725cbc53f74f9e7ffeb0` | "Tile, Round 1 x 1", "Item No: 98138 Alternate Item No: 35380, 35381, 39797, 118864" |
| Rebrickable part 6141, `web.archive.org/web/20260407093646id_/https://rebrickable.com/parts/6141/`, SHA-256 `d7e3a955add1e5080be58ab58bfc5e5719e4499950cdae7a0c186fcfa00e51f7` | "Plate Round 1 x 1 with Solid Stud"; External Sites: "LEGO 30057 113470 15570 34823 39799 44325 51809 6141 BrickLink 4073 BrickOwl 961948 … LDraw 6141 4073"; alternate part 85861 (open stud) is a different Rebrickable part |
| Rebrickable part 98138, `web.archive.org/web/20250303234033id_/https://rebrickable.com/parts/98138/`, SHA-256 `4195c1bd0c0b0b5b01384f397e45be2737739a4b34d13dc942eeb9f1475a2fac` | External Sites: "LEGO 98138 35380 35381 39797 BrickLink 98138 BrickOwl 474589 … LDraw 98138" |
| Rebrickable `elements.csv` (pinned in 004, SHA-256 `dfc8641d…`) | element 614101 and every 1×1 round plate element under `part_num` 6141; no element under 4073 (004 finding) |
| `kit_31203_inventory.json` (003, Brickset) | element 614101 design 6141, `part_ids` ["6141", "4073"]; tile elements design 35381, `part_ids` ["98138", "35381"] |

**Decision**: plate = LEGO design 6141, BrickLink **4073**, Rebrickable **6141**; tile = LEGO
designs 98138/35381 (kit elements use 35381), BrickLink **98138**, Rebrickable **98138**. Stored in
a new `data/part_numbers.json` with the citations above. 003 data is not changed (its
`part_ids` list both numbers and is consistent).

**Per-color check (new join rule 5)**: the color dropdown of each archived BrickLink part page
(the text between "All Colors (Not Applicable)" and the first "Name (count)" entry) lists the
BrickLink color names the part is catalogued in. All 14 plate rows and all 9 tile rows of the
current `part_colors.json` appear there (checked 2026-11-22).

**Alternatives rejected**: BrickLink API (needs an account and OAuth credentials: secrets and a
third-party service, reserved); Rebrickable API (needs a key); live scraping (forbidden by
Rebrickable's terms; BrickLink offline that day).

## R2. BrickLink wanted-list XML

Source: BrickLink Help "Wanted List, Mass Upload" (helpID=207), archived
`web.archive.org/web/20260618045436id_/https://www.bricklink.com/help.asp?helpID=207`, SHA-256
`a3060af15cc4b98458030f025e135256191e66e996e0f6ba7eaf753cdf3d4299` (page "last updated on May 18,
2026"; it carries a "page under construction" banner).

- "A wanted list in BrickLink XML format can not have an XML declaration."
- Opens with `<INVENTORY>`; one or more `<ITEM>` inside it.
- Required in each ITEM: `ITEMTYPE` (P for a part) and `ITEMID` ("the Item No. for this item in
  the BrickLink catalog").
- Optional: `COLOR` ("a color ID from the Color Guide"), `MAXPRICE`, `MINQTY` ("a whole number
  greater than 0"), `QTYFILLED`, `CONDITION` (N or U), `REMARKS` (escape `<`, `>`, `&`), `NOTIFY`,
  `WANTEDSHOW`, `WANTEDLISTID`.
- If an item is already on the wanted list and a quantity is given, "the wanted qty of the item in
  the upload will be added to the qty of the existing item"; an upload that errors is rolled back.

**Decision**: write `ITEMTYPE`, `ITEMID`, `COLOR`, `MINQTY`, and `CONDITION` only on request;
no `REMARKS`, `NOTIFY` or `WANTEDLISTID` (keeps files minimal; the user can choose the list on
upload). Two-space indentation, one element per line, `\n` endings, UTF-8, written with
`xml.sax.saxutils.escape` (standard library). Tell the user about the "adds to existing quantity"
rule in command output.

## R3. Rebrickable parts CSV

Source: Rebrickable Help "Importing Parts", archived
`web.archive.org/web/20260305004106id_/https://rebrickable.com/help/importing-parts/`, SHA-256
`e3af5198349b909bd75187f82d37f71064be29c8525e32a01b5e06b1a2f11f9e` (last modified Feb. 18, 2024).

- "You can manually create your own CSV file for import, as long as you use recognisable field
  headings. The order of the headings don't matter … Additional fields will be ignored."
- Examples: `Part,Color,Quantity` (`3001,15,100`) and `Element,Quantity` (`30101,100`).
- Imports may be appended, replaced or subtracted in a Part List, Custom List or MOC inventory.

**Decision**: export `Part,Color,Quantity` with Rebrickable part numbers and Rebrickable color IDs
(the import's default scheme). Accept the same two shapes as the owned / missing input format
(Q1), so a maker can export their Rebrickable collection or a "lost parts" list and pass it in.

## R4. Wider color coverage (Q3, US4)

Measured with the 004 maintainer tool (`tools/partcolors`) on the pinned snapshots in the session
cache, passing every color Rebrickable `elements.csv` lists for each part:

| Part | Colors listed by Rebrickable | Pass 004 rules 1–4 | Also on BrickLink's part page (rule 5) | Today |
|---|---|---|---|---|
| 6141 plate | 70 | 45 | 44 (Medium Blue excluded: not in 4073's BrickLink colors) | 14 |
| 98138 tile | 69 | 40 | 40 | 9 |

Excluded rows are mostly transparent colors (rule 2) and colors whose LDraw code or name does not
match Rebrickable's (rule 3). With the wider table, the feature-002 image fixture
(`tests/fixtures/images/test_128x80_quantized.png` → `layout`) resolves every lot: Bright Red
plate and tile, White, Nougat and Brick Yellow tiles were the uncited ones today.

**Decision (Q3, user-confirmed)**: replace the hand-reviewed list (`REVIEWED`) with "every color
listed for the part", keep rules 1–4, add rule 5, and keep kit rows authoritative. Existing 23 rows
must come out unchanged (`--check` compares).

## R5. Rebrickable license (closes 004 open question)

Rebrickable downloads page, archived
`web.archive.org/web/20261029125803id_/https://rebrickable.com/downloads/`, SHA-256
`1c514a79f8cb70a0faacccf7174ee4329a307a6d91221b8c318b6982a7b91b75`: "The catalog of official
LEGO sets is available for bulk download below. Free for personal and commercial use, provided you
acknowledge Rebrickable as your data source." and "You may automate downloading these archives at
most once a day. Scraping our web pages is strictly against our Terms".

**Decision**: replace `source.license_note` in `part_colors.json` with these terms and the cited
page; outputs that carry Rebrickable IDs (parts list JSON, `kit part-colors`, `kit part-numbers`,
human output of `parts`) include "Catalog data: Rebrickable" in their citations. Maintainer tools
download the CSV archives at most once a day (already true: they read a pinned local copy).

## R6. Top-up figures (real-data layouts from 004, session scratchpad `e2e/`)

Needed minus N × kit supply (inventory page 159), map pieces only:

| Layout | 1 kit | 2 kits | 3 kits |
|---|---|---|---|
| official-31203 | 0 | 0 | 0 |
| official-31203-bathymetry | 0 | 0 | 0 |
| ocean-sst | 0 | 0 | 0 |
| land-elevation | 11 lots, 6,382 pieces | 10 lots, 4,178 | 9 lots, 2,912 |

`land-elevation` beyond one kit: tiles Bright Bluish Green 3,145 and Earth Blue 325; plates Dark
Green 506, Bright Green 528, Bright Yellowish Green 515, Brick Yellow 350, Sand Yellow 231, Medium
Nougat 311, Reddish Brown 158, Dark Brown 128, Medium Stone Grey 185. (The run-state of 004
described a nine-color ocean background; the committed recipe uses three blues at 70/20/10, which
exceeds one kit's Bright Bluish Green. That is a 004 recipe matter, recorded in run-state, not
changed here.)

## R7. Spares

No pinned source states LEGO's spare-part rate. The kit's own extras are measured facts (003
`counts`: e.g. White plate 3,062 used / 3,064 supplied; Bright Green tile 529 / 601). **Decision**:
spares off by default, `--spares PCT` on request, kit extras shown as surplus. No claim about LEGO
packing rates.

## R8. Prices

BrickLink and Rebrickable both price an uploaded list for the user. Doing it in the CLI needs a
marketplace API account and credentials (constitution IV: environment variables only; run-policy:
new third-party service is reserved) and gives numbers that change daily. **Decision**: out of
scope for 005; human output points to the marketplaces' own pricing of an uploaded list.

## R9. Dependencies

None new. XML via `xml.sax.saxutils` and CSV via `csv` (standard library); HTML page parsing in the
maintainer tool via `html.parser` (standard library), as the 004 BrickLink color-guide parser does.

## R10. Owned-file matching

`Part,Color,Quantity` rows match a lot when `Part` equals the Rebrickable part number of a map part
(6141 or 98138) and `Color` equals the Rebrickable color ID of a cited row for that part.
`Element,Quantity` rows match when the element is in a cited row's `element_ids` (or equals its
`element_id`). Other Rebrickable part numbers (for example frame parts from an exported kit
inventory) are ignored and counted, so a maker can pass a full Rebrickable set inventory export.
Rows for a map part with an uncited color fail with the line number, because silently dropping
owned pieces would overstate what to buy.

## R11. Kit supply must be looked up by part as well as color

`KitInventory.supplied(color_key)` sums every inventory element with that color key, regardless of
role. In 31203 each color key belongs to one role, but a layout can put Bright Green on the plate
(land-elevation does), and `supplied("lego_bright_green")` returns 601, the tile supply. The parts
list must take supply from the element whose role matches the lot's part (land → plate element,
ocean → tile elements): a Bright Green plate lot has 0 kit supply. **Decision**: add
`KitInventory.supplied_for(part_id, color_key)` and test the land-elevation case explicitly;
`supplied()` stays for existing callers.
