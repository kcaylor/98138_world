# Contract: section counts JSON (006)

```json
{
  "format_version": "1",
  "kit": "31203",
  "layout": {"path": "official.json", "sha256": "…", "source_image": "recipe:official-31203"},
  "legend": [{"number": 1, "part_id": "6141", "part_type": "plate", "color_key": "lego_white",
              "name": "White", "verified": true, "total": 3062}],
  "sections": [{"label": "A1", "col": 0, "row": 0, "x": [0, 15], "y": [0, 15], "frame": 1,
                "counts": {"2": 120, "3": 136}, "total": 256}],
  "disclaimer": "Not affiliated with or endorsed by The LEGO Group."
}
```

Rules: sections in A1…H5 order; `counts` keys are lot numbers as strings in ascending numeric
order, zero counts omitted; key order as shown; no timestamps.
