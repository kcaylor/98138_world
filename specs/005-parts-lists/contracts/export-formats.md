# Contract: marketplace files (005) [PROVISIONAL: Q1, Q4]

Sources: research R2 (BrickLink help 207, archived 2026-06-18) and R3 (Rebrickable "Importing
Parts", archived 2026-03-05). Neither file carries a disclaimer or timestamp (Q4); bytes are
deterministic.

## BrickLink wanted list (XML)

```xml
<INVENTORY>
  <ITEM>
    <ITEMTYPE>P</ITEMTYPE>
    <ITEMID>4073</ITEMID>
    <COLOR>2</COLOR>
    <MINQTY>350</MINQTY>
  </ITEM>
  <ITEM>
    <ITEMTYPE>P</ITEMTYPE>
    <ITEMID>98138</ITEMID>
    <COLOR>39</COLOR>
    <MINQTY>3145</MINQTY>
    <CONDITION>U</CONDITION>
  </ITEM>
</INVENTORY>
```

Rules: no `<?xml ...?>` declaration; UTF-8; `\n`; two-space indent; one `ITEM` per verified lot with
`to_buy > 0`; element order ITEMTYPE, ITEMID, COLOR, MINQTY, CONDITION; `CONDITION` only with
`--condition`; values escaped (`&amp;`, `&lt;`, `&gt;`). (The example's second item shows the
optional CONDITION; the real export uses it on all items or none.)

## Rebrickable parts CSV

```text
Part,Color,Quantity
6141,19,350
98138,3,3145
```

Rules: header exactly `Part,Color,Quantity`; Rebrickable part number and Rebrickable color ID;
quantity = to buy; rows in lot order; UTF-8 without BOM; `\n`.

## Owned / missing input CSV (Q1)

Rebrickable's documented import shapes, so a Rebrickable export can be passed in:

```text
Part,Color,Quantity          Element,Quantity
6141,15,40                   614101,40
98138,322,12                 6322819,12
```

Headers case-insensitive, any order, extra columns ignored (e.g. Rebrickable's `Is Spare`), BOM and
CRLF accepted, blank lines skipped, duplicates summed. Errors (exit 1, file:line): unknown header
set; quantity not an integer ≥ 0; a map part (6141/98138) with a color not in the cited table; an
element not in any cited row's `element_ids`. Rows for other parts are ignored and counted.
