# Quickstart: Living planet map (012)

```bash
cd cli
lego-image-processor map build living-planet --fetch -o living.json --preview living.png
lego-image-processor parts list living.json --kits 1
lego-image-processor map build living-planet --arrangement B -o living-B.json
lego-image-processor dataset info modis-aqua-chla-2013-2024    # content sha256
lego-image-processor dataset info mod17a3-npp-mean-2000-2015   # http only: <reason>
```

Expected on real data (2026-11-22): land 702 White (ice), ocean 738 White (sea ice), 392 Black
shadow tiles, about 6,589 pieces beyond one kit; peak memory about 580 MB.

Web: `cd web && python -m web98138.prebuild --out site --maps living-planet` then
`WEB98138_SITE_DIR=site uvicorn web98138.app:app` and open `/maps/living-planet/A`.

Not affiliated with or endorsed by The LEGO Group.
