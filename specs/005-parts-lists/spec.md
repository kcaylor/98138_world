# Feature Specification: Parts Lists and Ordering

**Feature Branch**: `005-parts-lists`

**Created**: 2026-11-22

**Status**: Planned (reserved decisions carry a recommended answer marked **[PROVISIONAL]**; see
Clarifications and `run-state.md`. Confirm them before implement.)

**Input**: User description: "Feature 005: parts lists and ordering. From any layout (official
design, recipe build, image-derived), produce a parts list using verified part and color IDs
(LEGO, BrickLink, Rebrickable). Export a BrickLink wanted list (XML with MINQTY) and a Rebrickable
CSV. Support kit top-up: only the pieces needed beyond an existing 31203 kit (the kit is retired;
expect secondhand sources), including several kits or a kit plus loose parts. Resolve the land
plate part numbering (LEGO 6141 / element 614101; Rebrickable 6141; BrickLink 4073; tile 98138 on
BrickLink and Rebrickable, LEGO design 35381) from cited sources; wanted lists use each
marketplace's own part number and color ID. Consider spares, price estimates, and the
disclaimer." (scoping from `docs/vision.md` and the coordinating agent's brief of 2026-11-22; see
run-state.md)

## Context

Features 001–004 produce layouts (schema 2.0 JSON, 10,240 positions on the kit mask, land on the
1×1 round plate, ocean on the 1×1 round tile) from three sources: the official design
(`kit_31203_design.json` via `map build official-31203`), recipe builds (`map build`), and images
(`quantize` then `layout`). `validate` already reports colors outside the kit and quantities above
one kit's supply, but nothing turns a layout into something a maker can buy.

Facts that shape this feature (details and sources in `research.md`):

1. **Each marketplace numbers the land plate differently.** BrickLink's catalog files the 1×1
   round plate as item **4073** and lists 6141 as an alternate number; Rebrickable files it as
   **6141** and records "BrickLink 4073" under external IDs; LEGO's design ID is 6141 (element
   614101 in White). The 1×1 round tile is **98138** on both BrickLink and Rebrickable (LEGO design
   IDs 98138/35381; the kit's elements carry design 35381). A BrickLink wanted list that said 6141
   would point at an alternate number, so each export must use its marketplace's own number.
2. **Color IDs differ by marketplace too** (for example LEGO Brick Yellow = BrickLink Tan 2 =
   Rebrickable Tan 19). `kit_colors.json` and `part_colors.json` already carry cited LEGO,
   BrickLink and Rebrickable color IDs for 10 kit colors and 13 more plate colors.
3. **Layouts from images use colors the cited tables do not cover yet.** The 47-color palette of
   001/002 includes, for example, Bright Red; the current `part_colors.json` lists 14 plate and 9
   tile colors. Measured on the pinned snapshots, the same join rules would verify 44 plate colors
   and 40 tile colors (research R4).
4. **Rebrickable's terms are now confirmed.** Rebrickable's downloads page (archived 2026-10-29)
   says the CSV catalog is "Free for personal and commercial use, provided you acknowledge
   Rebrickable as your data source." This closes 004's open license question.
5. **Top-up arithmetic is small but real.** The three kit-color bundled maps need nothing beyond
   one kit; `land-elevation` needs 11 lots and 6,382 pieces beyond one kit (9 plate colors plus
   3,145 Bright Bluish Green and 325 Earth Blue tiles), 4,178 beyond two kits and 2,912 beyond
   three (research R6).

## Clarifications

### Session 2026-11-22

- Q: Which part number does each output use? → A: Each marketplace's own: BrickLink item 4073
  (plate) and 98138 (tile); Rebrickable part 6141 (plate) and 98138 (tile); LEGO design and element
  IDs shown for reference. Numbers come from a new cited reference file built from pinned archived
  catalog pages (auto-resolved: research R1, constitution V).
- Q: How is a layout position matched to a cited color? → A: By the layout's part ID and
  `color_id` key against `kit_colors.json`/`part_colors.json` (key rule `lego_<snake_case LEGO
  name>`), then the layout's `lego_color_code` must equal the cited LEGO color ID; any other case
  is an unverified lot (auto-resolved: `kit/colors.py`, `layout/generator.py` key rule, 004
  clarification on keys).
- Q: What does one kit supply? → A: The quantities on the instructions' parts inventory page
  (`kit_31203_inventory.json`, page 159) for the land and ocean elements, including the extras LEGO
  packs (for example 3,064 White plates for 3,062 positions) (auto-resolved: 003 data, `KitInventory.supplied`).
- Q: Does the parts list cover the frame, section bases and other non-map kit parts? → A: No; see
  reserved decision Q6 [PROVISIONAL]. Layouts only describe map positions.
- Q: Are prices estimated? → A: No. Prices need a marketplace API with an account and credentials
  (a third-party service and secrets, both reserved) and change daily; the outputs name where to
  price a list (BrickLink and Rebrickable both price an imported list) and carry no prices
  (auto-resolved: constitution IV/VI, run-policy).
- Q: How are spares handled? → A: Optional, off by default: `--spares PCT` adds `ceil(PCT% of the
  shortfall)` to each lot that has a shortfall. No default percentage is claimed, because no cited
  source gives LEGO's spare rate; the official kit's measured extras (used vs supplied, from 003)
  are shown for reference (agent decision within Q5 [PROVISIONAL]: constitution V forbids invented
  reference numbers).
- Q: How does output stay deterministic? → A: Lots sorted by part (plate, then tile) and LEGO color
  ID; JSON keys in fixed order; no timestamps in export files (auto-resolved: 004 FR-006 pattern).
- Q: Where does the BrickLink XML format come from? → A: BrickLink's "Wanted List, Mass Upload"
  help page (archived 2026-06-18): no XML declaration; `<INVENTORY>` holding one or more `<ITEM>`;
  required `ITEMTYPE` and `ITEMID`; optional `COLOR`, `MINQTY`, `CONDITION` (N/U) and others
  (auto-resolved: research R2).
- Q: Where does the Rebrickable CSV format come from? → A: Rebrickable's "Importing Parts" help
  page (archived 2026-03-05): header `Part,Color,Quantity` with Rebrickable part and color
  numbers, or `Element,Quantity`; extra fields are ignored (auto-resolved: research R3).

Reserved decisions (run-policy: product scope, file formats others use, CLI flags), each with a
recommended provisional answer:

- **Q1** [PROVISIONAL] How does a maker describe the parts they already own? → `--kits N` (whole
  kits, default 0) plus repeatable `--owned FILE` (loose parts) and `--missing FILE` (pieces absent
  from a secondhand kit), both in Rebrickable's documented import CSV (`Part,Color,Quantity` with
  Rebrickable numbers, or `Element,Quantity`).
- **Q2** [PROVISIONAL] Colors without a cited row (mostly image-derived layouts) → the parts list
  shows them as unverified with no marketplace IDs; `parts export` exits 6 and writes nothing
  unless `--allow-partial`, which writes the verified lots and lists the omitted ones.
- **Q3** [PROVISIONAL] Widen the cited color tables → yes: rebuild `part_colors.json` from the
  same pinned snapshots for every opaque color of both parts that passes the 004 join rules plus a
  new rule (the color appears on BrickLink's archived catalog page for that part): 44 plate and 40
  tile colors (US4).
- **Q4** [PROVISIONAL] Disclaimer in marketplace files → BrickLink XML and Rebrickable CSV carry
  no disclaimer (fixed third-party import formats, as decided for layout CSV in 003); the command's
  output and the parts list JSON carry it.
- **Q5** [PROVISIONAL] CLI surface → new group `parts` with `parts list` and `parts export`, and
  `kit part-numbers`; options in `contracts/cli.md`; spares off by default; no `CONDITION` unless
  `--condition new|used`.
- **Q6** [PROVISIONAL] Scope of a list → map pieces only (plates and tiles at layout positions);
  frame, section bases and other kit parts are out of scope for 005.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parts list with verified IDs from any layout (Priority: P1)

A maker points the tool at a layout file (the official design, a recipe build or an image-derived
layout) and gets a parts list: one line ("lot") per part and color, with the quantity the layout
needs and, for each lot, the LEGO color name and ID, element ID, BrickLink item number, color name
and ID, and Rebrickable part number, color name and ID, each from a cited source. Lots the tool
cannot verify are listed as unverified, with the reason, and no IDs are invented for them.

**Why this priority**: every later story (exports, top-up) is a view of this list, and constitution
V requires verified IDs before anything is ordered.

**Independent Test**: run it on the official layout (built offline) and on a small image-derived
fixture; check counts against the layout, IDs against the cited tables, and that unverified lots
carry no marketplace IDs.

**Acceptance Scenarios**:

1. **Given** the official layout, **When** the maker lists its parts, **Then** there are 10 lots
   (1 plate, 9 tile colors) whose quantities sum to 10,240 and equal the official design's color
   counts, and every lot shows LEGO, BrickLink and Rebrickable IDs with their sources.
2. **Given** any lot on the plate, **When** it is shown, **Then** its BrickLink item number is 4073
   and its Rebrickable part number is 6141; for the tile both are 98138.
3. **Given** a layout with a color that has no cited row for its part (for example Bright Red on
   the plate before US4), **When** the list is produced, **Then** that lot is marked unverified,
   shows the layout's own color name and code, has no marketplace IDs, and the list ends with a
   warning naming it.
4. **Given** a layout whose `lego_color_code` disagrees with the cited LEGO ID for its color key,
   **When** the list is produced, **Then** that lot is unverified with the reason "color code
   mismatch".
5. **Given** the same layout twice, **When** listed as JSON, **Then** the two files are identical.
6. **Given** a layout that is not schema 2.0, has positions outside 128×80 or is unreadable,
   **When** the list is requested, **Then** the command fails with the reason and writes nothing.
7. **Given** a recipe-built layout, **When** listed as JSON, **Then** the list records the layout
   file's SHA-256, its `metadata.map` recipe id and dataset citations, and the disclaimer.

---

### User Story 2 - BrickLink wanted list and Rebrickable CSV (Priority: P2)

A maker exports the list as a BrickLink wanted list (XML with `MINQTY`) and as a Rebrickable
parts CSV, and uploads either one to the marketplace without editing it.

**Why this priority**: it is the step that turns a map into an order; it depends only on US1.

**Independent Test**: export the official layout's list and a fixture's list; check the XML and
CSV against the documented formats (research R2, R3) and the cited IDs; parse them back and
compare quantities.

**Acceptance Scenarios**:

1. **Given** a parts list, **When** the maker exports BrickLink XML, **Then** the file has no XML
   declaration, one `<INVENTORY>` element and one `<ITEM>` per lot to buy, each with
   `ITEMTYPE` `P`, `ITEMID` the BrickLink item number, `COLOR` the BrickLink color ID and `MINQTY`
   the quantity to buy (a whole number greater than 0).
2. **Given** a parts list, **When** the maker exports Rebrickable CSV, **Then** the file's header is
   `Part,Color,Quantity` and each row has the Rebrickable part number, Rebrickable color ID and the
   quantity to buy.
3. **Given** `--condition used` (or `new`), **When** BrickLink XML is exported, **Then** each item
   has `CONDITION` `U` (or `N`); without the option no `CONDITION` element is written.
4. **Given** unverified lots, **When** the maker exports without `--allow-partial`, **Then** the
   command exits 6, writes no file and names the lots; **with** `--allow-partial` it writes the
   verified lots and prints the omitted ones (Q2).
5. **Given** a list with nothing to buy (for example the official layout with `--kits 1`), **When**
   exported, **Then** no file is written and the command says there is nothing to buy (BrickLink
   requires at least one item).
6. **Given** an export, **When** the maker reads the command output, **Then** it ends with the
   disclaimer and says that quantities uploaded to an existing BrickLink wanted list add to items
   already on it.

---

### User Story 3 - Kit top-up: only what you do not already have (Priority: P3)

A maker who owns one or more 31203 kits (often secondhand and incomplete) and maybe some loose
parts gets a list of only the pieces still needed, with an optional allowance for spares.

**Why this priority**: the kit is retired and most makers start from one secondhand kit; this is
the most common real order. It builds on US1 and feeds US2.

**Independent Test**: on the `land-elevation` fixture layout and synthetic layouts, check
shortfalls for 0, 1, 2 and 3 kits, loose parts and missing pieces against hand-computed values.

**Acceptance Scenarios**:

1. **Given** a layout and `--kits N`, **When** the list is produced, **Then** each lot's owned
   quantity is N times the kit's supply of that element (0 for colors not in the kit), and its
   shortfall is `max(0, needed − owned)`.
2. **Given** `--owned FILE` in Rebrickable CSV (`Part,Color,Quantity` or `Element,Quantity`),
   **When** the list is produced, **Then** those quantities add to the owned column of matching
   lots; rows for parts other than the two map parts are ignored and counted (so a full set
   inventory export can be passed in); rows for a map part in a color with no cited row fail with
   the line number.
3. **Given** `--missing FILE`, **When** the list is produced, **Then** those quantities are
   subtracted from the kits' supply (never below 0) for matching lots.
4. **Given** `--spares PCT`, **When** the list is produced, **Then** every lot with a shortfall
   gets `ceil(shortfall × PCT / 100)` extra pieces to buy, and lots with no shortfall get none.
5. **Given** the official layout and `--kits 1`, **When** listed, **Then** nothing is to buy, and
   the surplus per lot equals the official design's extras (for example 2 White plates).
6. **Given** a top-up list, **When** exported (US2), **Then** only lots with something to buy
   appear, with the quantity to buy (shortfall plus spares).

---

### User Story 4 - Verified colors for every layout source (Priority: P4)

A maker with an image-derived layout (or a recipe author) finds that every opaque color the two
map parts are made in has cited LEGO, BrickLink and Rebrickable IDs, so most image layouts can be
ordered without unverified lots.

**Why this priority**: image layouts use colors outside the 23 rows cited today; widening the
table removes most unverified lots. It is independent of US2–US3 and changes reference data, so it
comes after the core flow (Q3).

**Independent Test**: run the maintainer tool with `--check` on the pinned snapshots; confirm row
counts, join-rule exclusions and that all 23 existing rows are unchanged.

**Acceptance Scenarios**:

1. **Given** the pinned snapshots, **When** the maintainer rebuilds the table, **Then** it holds
   every opaque color of 6141 and 98138 that passes the join rules, each row citing its sources,
   and every existing row is unchanged.
2. **Given** a color that Rebrickable lists for the part but BrickLink's archived catalog page for
   that part does not (for example Medium Blue on 4073), **When** the table is rebuilt, **Then** the
   color is excluded and reported with the reason.
3. **Given** the rebuilt table, **When** the maintainer runs the build again with `--check`, **Then**
   it reports "no differences".
4. **Given** the rebuilt table, **When** `kit part-colors` runs, **Then** it lists the new colors
   with their IDs and sources, and recipes may use them (004 FR-016 unchanged).

### Edge Cases

- A layout with zero positions of one class (not possible for valid layouts, which always cover
  the mask): rejected by the layout loader as today.
- `--kits` negative or not an integer: usage error. Very large N: allowed; nothing to buy.
- An owned CSV with a header the tool does not recognise, an empty file, duplicate rows (summed),
  negative or non-integer quantities (error with line number), a BOM or Windows line endings
  (accepted).
- An owned CSV row uses BrickLink numbering (part 4073): not recognised, error names the line and
  says the file must use Rebrickable numbers (Rebrickable's own import accepts several schemes; this
  tool accepts the documented one).
- An `Element,Quantity` row for an element listed in `element_ids` of a cited row: matched to that
  row; an element not listed: error with the line number.
- The output path exists: overwritten (as `map build` does); the output directory is missing:
  error.
- A layout with both cited and uncited colors: list shows both; exports follow Q2.
- Two kit elements map to one color key (not the case in 31203): supply is summed.

## Requirements *(mandatory)*

### Functional Requirements

**Reference data**

- **FR-001**: The package MUST ship a cited marketplace part-number file for the two map parts:
  for each, LEGO design IDs, BrickLink item type and item number with its alternate numbers,
  Rebrickable part number, and the BrickLink color names listed on the part's catalog page, each
  with a citation (URL, SHA-256 of the pinned page, access date). It is built by a maintainer tool
  from pinned archived pages and checked with `--check` (research R1).
- **FR-002**: `part_colors.json` MUST record Rebrickable's confirmed terms ("free for personal and
  commercial use, provided you acknowledge Rebrickable as your data source", with its cited page)
  in place of the open license note, and every output that uses Rebrickable data MUST acknowledge
  Rebrickable as a data source.
- **FR-003**: (US4, Q3) The maintainer tool MUST be able to rebuild `part_colors.json` for every
  opaque color of 6141 and 98138 that passes the 004 join rules and a fifth rule: the color's
  BrickLink name appears in the color list of BrickLink's pinned catalog page for that part. Rows
  that fail are excluded and reported. Existing rows MUST NOT change.

**Parts list**

- **FR-004**: The tool MUST read any schema 2.0 layout and group its positions into lots by part
  and color key, counting the quantity needed per lot.
- **FR-005**: Each lot MUST be resolved against the cited tables: kit colors and part colors for
  the lot's part, with the layout's `lego_color_code` equal to the cited LEGO color ID. A resolved
  lot carries LEGO color name and ID, element ID, BrickLink item number, color name and ID,
  Rebrickable part number, color name and ID, RGB and citation IDs. Any other lot is unverified,
  carries only the layout's color name and code and the reason, and MUST NOT carry marketplace IDs.
- **FR-006**: Each lot MUST show: needed, owned, shortfall (`max(0, needed − owned)`), spares, to
  buy (shortfall + spares) and surplus (`max(0, owned − needed)`).
- **FR-007**: Owned quantities MUST come only from what the maker states: `--kits N` (N × the
  kit's supply of the lot's element from the cited inventory), `--owned FILE` (added) and
  `--missing FILE` (subtracted from kit supply, floor 0). Files use Rebrickable's documented import
  CSV (Q1).
- **FR-008**: Spares MUST be off by default; `--spares PCT` (0–100) adds
  `ceil(shortfall × PCT / 100)` to each lot with a shortfall. The list MUST NOT state a LEGO spare
  rate.
- **FR-009**: The list MUST be available as a human-readable table and as JSON (contract
  `contracts/parts-list-format.md`). The JSON carries format version, the layout's path, SHA-256,
  source and `metadata.map` provenance (recipe id, dataset ids, citations, licenses), the owned
  inputs (kits, files with SHA-256), spares, lots, totals, unverified lots, citations, a
  Rebrickable acknowledgement and the disclaimer. It carries no timestamp, so the same inputs give
  identical bytes.
- **FR-010**: Totals MUST report lots and pieces needed, owned, to buy, verified and unverified.

**Exports**

- **FR-011**: BrickLink export MUST follow BrickLink's documented wanted-list XML: no XML
  declaration; `<INVENTORY>` with one `<ITEM>` per lot with to-buy > 0, each with `ITEMTYPE` `P`,
  `ITEMID` (BrickLink item number), `COLOR` (BrickLink color ID) and `MINQTY` (to buy); `CONDITION`
  `N` or `U` only when asked; text escaped as the format requires.
- **FR-012**: Rebrickable export MUST be a CSV with header `Part,Color,Quantity` and one row per
  lot with to-buy > 0 (Rebrickable part number, Rebrickable color ID, to buy), UTF-8, `\n` line
  endings.
- **FR-013**: Exports MUST contain only verified lots. With unverified lots and no
  `--allow-partial`, `parts export` MUST exit 6, write nothing and list them (Q2).
- **FR-014**: When no lot has anything to buy, exports MUST write no file and say so (exit 0).
- **FR-015**: Exports MUST be deterministic: same inputs, identical bytes; lots in a fixed order.

**Commands and outputs**

- **FR-016**: All capabilities MUST be library functions and CLI commands on local files:
  `parts list`, `parts export`, `kit part-numbers` (Q5). No command uses the network.
- **FR-017**: All human output MUST end with "Not affiliated with or endorsed by The LEGO Group."
  and JSON outputs MUST carry it in `disclaimer`. BrickLink XML and Rebrickable CSV files carry no
  disclaimer (Q4); the command that writes them prints it.
- **FR-018**: Prices MUST NOT be estimated or shown. Human output MAY say that both marketplaces
  price an uploaded list.
- **FR-019**: Tests MUST NOT use the network; committed fixtures are small derived files, never the
  archived pages or catalog downloads.

### Key Entities

- **Marketplace part numbers**: per map part, LEGO design IDs, BrickLink item type, number,
  alternates and known colors, Rebrickable part number, citations.
- **Lot**: part, color key, verified flag and reason, catalog IDs (LEGO, element, BrickLink,
  Rebrickable), RGB, needed, owned, shortfall, spares, to buy, surplus.
- **Owned inputs**: number of kits, loose-part files, missing-part files (each with SHA-256).
- **Parts list**: layout reference and provenance, owned inputs, spares, lots, totals, unverified
  lots, citations, disclaimer.
- **Wanted list (BrickLink)** and **parts CSV (Rebrickable)**: marketplace views of the lots to buy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For the official layout, the parts list has 10 verified lots totalling 10,240 pieces;
  with `--kits 1` nothing is to buy.
- **SC-002**: For every bundled recipe's layout, every lot is verified (all their colors are cited).
- **SC-003**: For `land-elevation` built from the real datasets, the top-up beyond 1, 2 and 3 kits
  is 11 lots / 6,382 pieces, 10 / 4,178 and 9 / 2,912 (research R6).
- **SC-004**: Every exported BrickLink and Rebrickable file parses under the documented formats in
  tests, uses BrickLink 4073 / Rebrickable 6141 for plates and 98138 for tiles, and round-trips to
  the same quantities.
- **SC-005**: After US4, the image-derived fixture layout of feature 002 has no unverified lots.
- **SC-006**: `parts list` and `parts export` finish in under 2 seconds for a 10,240-position
  layout.
- **SC-007**: Every human output ends with the disclaimer and every JSON output carries it.
- **SC-008**: The full test suite passes with no network access.

## Assumptions

- The coordinating agent's brief of 2026-11-22 and `docs/vision.md` answer the scoping questions;
  no separate four-question round was held (recorded in run-state.md).
- Only kit 31203 is supported, as in 003/004 (`--kit 31203`).
- Layouts carry only the two map parts; `PositionPlacement` already rejects others.
- The cited catalog equivalences (LEGO ↔ BrickLink ↔ Rebrickable) are asserted by those catalogs,
  not by a LEGO-published crosswalk (as recorded in 003's `kit_colors.json`).
- Archived catalog pages are the pinned sources because BrickLink's site redirected to a
  maintenance page on 2026-11-22 and Rebrickable's terms forbid scraping its live pages.
- Marketplace availability and prices are not checked; a color can be in the catalog and still be
  scarce or absent from sellers' stock.
- Build sheets are feature 006.
- Not affiliated with or endorsed by The LEGO Group.
