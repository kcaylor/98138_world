# Quickstart: Pacific-centred Arrangements D and E (010)

```bash
cd cli
lego-image-processor map build official-31203 --arrangement D -o official-D.json --preview official-D.png
lego-image-processor layout arrange official-D.json --arrangement asia-pacific -o official-E.json
lego-image-processor sheets build official-D.json -o official-D.pdf   # last page: assembly
lego-image-processor map build ocean-el-nino --cache-dir <cache> -o el-nino.json   # D from the recipe
lego-image-processor parts list el-nino.json --kits 1                              # extra tiles in D
cd ../web && python -m web98138.prebuild --out site --maps official-31203,ocean-el-nino   # A-E
```

Check: the D PDF's last page names groups 2b·3·1·2a, "unpeg frame 2 between strips D and E", joints
F|G, H|A, B|C (15 pegs each), the border pp. 140–153 and "not among the building instructions'
combinations".
