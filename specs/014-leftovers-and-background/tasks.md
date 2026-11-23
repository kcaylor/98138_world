# Tasks: 014 leftovers and background

- [x] T001 Unit tests: leftovers for official (one kit, total 890, White 2), unused colors at full
      supply, kits 0 all zero, kits 2, missing pieces, plate in ocean color does not consume tiles
      (`cli/tests/unit/parts/test_leftovers.py`)
- [x] T002 Contract tests: `parts list --kits 1` table and JSON carry leftovers; `--kits 0` table
      has none; exports unchanged (`cli/tests/contract/test_parts_contract.py`)
- [x] T003 Implement `Leftover`, `PartsList.leftovers`, totals and JSON (`parts/partslist.py`)
- [x] T004 Table output (`cli/parts.py`)
- [x] T005 Web prebuild + map page leftovers; web tests (`web/`)
- [x] T006 Gray background, stud mat, swatch border (`static/style.css`); web test for the token
- [x] T007 Verify every recipe's needed/to-buy unchanged vs main; full CLI + web suites; prebuild
      official-31203 and rainfall; screenshot
- [x] T008 Docs: CLAUDE.md/AGENTS.md project sections, 005 contract note
