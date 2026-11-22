# Contract: CLI (006) [PROVISIONAL: Q7, Q8]

Human output ends with `Not affiliated with or endorsed by The LEGO Group.` No network. Exit codes:
0 ok; 1 input error (layout unreadable, unknown section label, non-Latin-1 title for PDF, output
path problem); 2 Click usage.

## `sheets build LAYOUT -o PATH`

| Option | Meaning |
|---|---|
| `-o, --output PATH` | PDF file (format pdf) or directory (format svg; created if missing) — required |
| `--format pdf\|svg` | default pdf |
| `--paper letter\|a4` | default letter |
| `--sections LIST` | comma-separated labels, e.g. `B2,C2`; default all 40 |
| `--title TEXT` | overview title; default recipe title, else layout file name |
| `-q` | quiet |

Output: title, pages written (overview, legend pages, section pages), lots (verified/unverified),
output path, "Print at 100% (no fit-to-page); check the 100 mm scale bar.", disclaimer.
SVG files: `page-01.svg` … zero-padded to two digits.

## `sheets counts LAYOUT [--format table|json] [-o PATH]`

Table: one line per section: label, ranges, counts as `#n:count` pairs; then the legend. JSON:
contracts/counts-format.md. Disclaimer last.
