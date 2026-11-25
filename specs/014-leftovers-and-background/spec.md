# Feature Specification: Leftovers in the box, and a light gray page background

**Feature Branch**: `014-leftovers-and-background`

**Created**: 2026-11-22

**Status**: Clarified (owner decisions relayed; autonomous mode)

**Input**: Two owner-approved changes relayed by the coordinating session on 2026-11-22:
(1) a light gray web page background so White studs show; (2) "left over in the box" counts for
every parts list.

## Context

- Every map uses all 10,240 positions (3,062 plates and 7,178 tiles), but one 31203 kit ships more
  pieces of each kit color than the official design uses, and a data-driven map usually leaves
  whole kit colors unused. Makers want to know what stays in the box.
- White studs (sea ice, ice sheets, the official map's land plates) disappear on the site's
  near-white page and white panels.

## User Scenarios & Testing

### User Story 1 — See what is left over in the box (Priority: P1)

A maker lists the parts for a layout with one or more kits and sees, for every map part and color
the kit supplies, how many pieces stay in the box after building, and the total.

**Acceptance**:
1. Given the official layout and `--kits 1`, the leftovers are the kit's extras (White plates 2,
   Dark Turquoise tiles and so on), each equal to kit supply − pieces used.
2. Given a data map that uses no Coral tiles, Coral appears with its whole supply (601) left over.
3. Given `--kits 0`, every leftover is 0 and the text output shows no leftover table.
4. JSON carries the leftovers and a total; marketplace files (BrickLink XML, Rebrickable CSV) are
   byte-for-byte unchanged.

### User Story 2 — Leftovers on the web map page (Priority: P2)

The map page's parts section shows "Left over in the box" per kit color (one kit), beside the
existing "beyond one kit" count, computed by the CLI library at prebuild time.

### User Story 3 — White studs visible on the site (Priority: P2)

The page background is a neutral light gray; every stud preview (map page, index cards, about page
figures) sits on a gray mat, and legend/lot swatches have a visible border, so White studs and the
dark ocean colors both read.

## Requirements

- **FR-001**: For each map element of the kit inventory (land plate and the nine ocean tiles),
  leftover = max(0, kit supply − pieces used), where kit supply = kits × inventory quantity −
  missing pieces (as for the existing `kit_supply`), and pieces used counts layout positions of
  that part in that cited color. Supplies are read from `kit_31203_inventory.json`, never
  hard-coded.
- **FR-002**: Kit colors the layout does not use are listed with their whole supply left over.
- **FR-003**: Totals include the leftover total.
- **FR-004**: `parts list` JSON gains a `leftovers` array and `totals.leftover`; the table output
  shows a "Left over in the box" table and total when kits ≥ 1 (with `--all-columns` or not).
  Existing fields and lot arithmetic are unchanged.
- **FR-005**: Marketplace exports are unchanged (leftovers are not purchases).
- **FR-006**: The web prebuild writes the one-kit leftovers and total into each variant of
  `manifest.json`; the map page shows them. The service does not import `lego_image_processor`.
- **FR-007**: The page background is a neutral light gray in #e9e9e9–#efefef; body, muted and link
  text keep WCAG AA (≥ 4.5:1) on it.
- **FR-008**: Stud previews have a gray surround; swatches have a visible border. Generated
  preview PNGs and build files are unchanged.

## Success Criteria

- **SC-001**: Official layout, one kit: leftover total = 11,130 − 10,240 = 890 pieces (kit map
  pieces 3,064 + 8,066 = 11,130).
- **SC-002**: For every bundled recipe, needed/to-buy counts are identical to before.
- **SC-003**: Muted text contrast on the new background ≥ 4.5:1.

## Clarifications

### Session 2026-11-22 (owner decisions, relayed)

- Q: Which gray? → A: Neutral light gray around #e9e9e9–#efefef with AA text (user).
- Q: Leftover formula? → A: max(0, kit supply − pieces used) per part+color, kit colors the map
  does not use included, plus a total; marketplace files unchanged (user).
- Q: Does "kit supply" include loose parts (`--owned`)? → A: No; "in the box" is the kits only
  (minus `--missing`). The existing `surplus` keeps counting loose parts. (agent decision: the
  name says box; `kit_supply` already excludes loose parts.)
- Q: Does a plate in an ocean color count against the tile supply? → A: No; supply is per part
  (`supplied_for`, feature 005 R11), so a Bright Green plate does not use Bright Green tiles.
  (auto-resolved: `kit/inventory.py`)
- Q: Text output with `--kits 0`? → A: No leftover table (all would be 0); JSON still lists the ten
  rows with zeros so the format is stable. (agent decision)
- Q: Is there a parts-list CSV? → A: No; the parts list has table and JSON outputs only; the
  Rebrickable CSV is a marketplace export and stays unchanged. (auto-resolved: `cli/parts.py`)
- Q: Palette chooser canvas (palette.js)? → A: Not on main (branch `012-palette-chooser` is not
  merged); nothing to change here. Recorded as an open question. (agent decision)
- Q: Dark mode? → A: Page colors stay dark; the stud mat is the same light gray, which also keeps
  dark ocean edges visible. (agent decision)

## Out of scope

Prices, BrickLink/Rebrickable files, preview PNG colors, build sheets, new CLI flags.
