# Contract: CLI (005) [PROVISIONAL: Q1, Q2, Q4, Q5]

All human output ends with `Not affiliated with or endorsed by The LEGO Group.`; JSON files carry
`"disclaimer"`. `-q` suppresses human output (errors still go to stderr). No command uses the
network. Exit codes: 0 ok; 1 input error (unreadable layout, bad owned/missing file, output
directory missing); 2 Click usage; 6 unverified lots in an export without `--allow-partial`.

Shared top-up options (both `parts` commands):

| Option | Meaning |
|---|---|
| `--kit 31203` | template kit (only 31203) |
| `--kits N` | whole kits owned, integer ≥ 0, default 0 |
| `--owned FILE` | loose parts owned, Rebrickable import CSV; repeatable; quantities add |
| `--missing FILE` | pieces missing from the owned kits, same format; repeatable; subtracted from kit supply (floor 0) |
| `--spares PCT` | 0–100, default 0; extra `ceil(shortfall × PCT/100)` per lot with a shortfall |

## `parts list LAYOUT`

| Option | Meaning |
|---|---|
| `--format table\|json` | default table (stdout) |
| `-o, --output PATH` | write JSON (implies json) |
| `--all-columns` | table also shows element ID and Rebrickable IDs (default columns: part, color, BrickLink, needed, owned, to buy) |
| `-q` | quiet |

Human output: layout path and source (recipe id if any); owned inputs; table of lots; totals;
unverified lots with reasons (warning); "Prices: upload the list to BrickLink or Rebrickable to
price it."; citations incl. "Catalog data: Rebrickable"; disclaimer. Exit 0 even with
unverified lots.

## `parts export LAYOUT`

| Option | Meaning |
|---|---|
| `--bricklink PATH` | write BrickLink wanted-list XML |
| `--rebrickable PATH` | write Rebrickable `Part,Color,Quantity` CSV |
| `--condition new\|used` | BrickLink `CONDITION` N/U; omitted by default |
| `--allow-partial` | write verified lots even when some are unverified |
| shared top-up options | as above |
| `-q` | quiet |

At least one of `--bricklink`, `--rebrickable` is required (usage error otherwise). Unverified lots
without `--allow-partial` → exit 6, nothing written, lots named. Nothing to buy → no file, message
"Nothing to buy: the owned parts cover this layout.", exit 0. Output: files written, lots and
pieces exported, omitted lots (if partial), the BrickLink note "Uploading adds these quantities to
items already on the chosen wanted list.", disclaimer.

## `kit part-numbers [--kit 31203] [--format table|json]`

Table: part, name, LEGO design IDs, BrickLink type/item/alternates, Rebrickable part, sources
(URL, SHA-256, accessed). JSON: the file verbatim. Disclaimer last.

## Unchanged

All 001–004 commands. `validate` keeps its own report; `parts list --kits 1` is the ordering view.
