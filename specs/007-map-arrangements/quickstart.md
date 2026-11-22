# Quickstart: Map Arrangements (007)

From `cli/`:

```bash
# Build a recipe hung as Combination B (America in the centre)
.venv/bin/lego-image-processor map build land-elevation --arrangement B -o elev-B.json --preview elev-B.png
# ... or C (Asia and Australia in the centre)
.venv/bin/lego-image-processor map build land-elevation --arrangement asia-australia -o elev-C.json

# Re-hang an existing layout (no recomputation), and back
.venv/bin/lego-image-processor map build official-31203 -o official.json
.venv/bin/lego-image-processor layout arrange official.json --arrangement B -o official-B.json
.venv/bin/lego-image-processor layout arrange official-B.json --arrangement A -o official-A.json

# Validate (mask under the layout's arrangement) and build sheets
.venv/bin/lego-image-processor validate official-B.json
.venv/bin/lego-image-processor sheets build elev-B.json -o elev-B.pdf
```

Not affiliated with or endorsed by The LEGO Group.
