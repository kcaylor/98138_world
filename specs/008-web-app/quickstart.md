# Quickstart: Web App (008)

```bash
cd web
uv venv --python 3.11 && uv pip install -e ../cli -e . pytest httpx pypdf
.venv/bin/python -m web98138.prebuild --out site-output          # datasets cached; add --fetch first time
WEB98138_SITE_DIR=site-output .venv/bin/uvicorn web98138.app:app --port 8080
open http://127.0.0.1:8080/
.venv/bin/pytest -q
```

Not affiliated with or endorsed by The LEGO Group.
