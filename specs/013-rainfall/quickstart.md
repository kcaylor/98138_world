# Quickstart: Rainfall map (013)

Not affiliated with or endorsed by The LEGO Group.

```bash
cd cli
lego-image-processor map build rainfall --fetch -o rain.json --preview rain.png --report rain-report.json
lego-image-processor parts list rain.json --kits 1
lego-image-processor dataset info nsidc-cdr-v6-seaice-minimum-1991-2020
```

Expect: overrides Antarctica 595, Greenland 116 (land, White), sea ice 759 (ocean, White), shadow
392 (Black); `Legend (mm/day; mm/yr):`; 0 cells filled from neighbours; about 8,160 pieces beyond
one kit. Web: `python -m web98138.prebuild --out site --maps rainfall` builds A, B and C.

Regenerate the fixtures (after `dataset fetch --recipe rainfall`):
`PYTHONPATH=tools python -m fixtures004.make_fixtures --only gpcp-v23-ltm-1991-2020 --only nsidc-cdr-v6-seaice-minimum-1991-2020`.
