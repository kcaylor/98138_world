# CLI contract: Pacific-centred Arrangements D and E (010)

- `--arrangement/-a` on `map build`, `map check`, `layout arrange`: `A|B|C|D|E` or
  `europe-africa|americas|asia-australia|pacific|asia-pacific`, any case. Metavar `[A|B|C|D|E]`.
  Unknown value: usage error (exit 2) listing
  `A, B, C, D, E, europe-africa, americas, asia-australia, pacific, asia-pacific`.
- Recipe key `arrangement`: same values; invalid value names the same list.
- Arrangement line (map build/check, sheets build, validate):
  `D (pacific, frames 2b·3·1·2a, the Pacific (date line) in the centre; not in the building instructions)`;
  A–C unchanged, e.g. `B (americas, frames 3·1·2, America in the centre)`.
- `layout arrange` prints frames left to right by group, e.g. `2b Europe & Africa, 3 Asia & Australia,
  1 America, 2a Europe & Africa`.
- `sheets build`: `Wrote out.pdf: 43 pages (1 overview, 1 legend, 40 sections, 1 assembly), Letter`;
  the last page is the assembly page (SVG: last page-NN.svg).
- `sheets counts` JSON: `arrangement` = id (A–E).
- Every command ends human output with "Not affiliated with or endorsed by The LEGO Group."
