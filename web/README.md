# web98138: the 98138.world web site

Pick one of the six bundled maps and a frame combination (A–E; D and E are not in the building
instructions, feature 010), see the stud preview, and
download everything to build it: layout JSON, parts lists (full and topped up from one 31203 kit),
BrickLink wanted list, Rebrickable CSV and build-sheet PDFs (US Letter and A4). Feature 008; see
`specs/008-web-app/`.

Not affiliated with or endorsed by The LEGO Group.

## How it works

- **Build step** (`python -m web98138.prebuild --out DIR [--fetch] [--maps ...] [--combinations ...]
  [--cache-dir ...]`): calls the CLI library (`lego_image_processor`, in `../cli`) for every map ×
  combination and writes the files plus `manifest.json` (size, SHA-256, content type of every
  file; tool, recipe and dataset versions; the data shown on the pages). Only `--fetch` uses the
  network, to download missing pinned datasets.
- **Service** (`web98138.app`, FastAPI + Jinja2): checks the output at start-up and serves pages and
  files from it. It never imports the CLI library, builds maps or downloads data. No JavaScript, no
  cookies, nothing loaded from other sites.

Routes: `/`, `/about`, `/maps/<map>/<A|B|C>`, `.../preview.png`, `.../thumb.png`,
`.../download/<kind>` (`layout`, `parts`, `parts-1kit`, `bricklink`, `rebrickable`,
`bricklink-1kit`, `rebrickable-1kit`, `sheets-letter`, `sheets-a4`), `/manifest.json`, `/healthz`,
`/robots.txt`. Contract: `specs/008-web-app/contracts/routes.md`.

## Develop

```bash
uv venv --python 3.11 && uv pip install -e ../cli -e . pytest httpx2 pypdf
.venv/bin/pytest                                           # offline
.venv/bin/python -m web98138.prebuild --out site-output    # datasets from ~/.cache/lego-image-processor
WEB98138_SITE_DIR=site-output .venv/bin/uvicorn web98138.app:app --port 8080
```

Python 3.11 (the CLI pins scikit-image 0.21). Dependencies are permissive (FastAPI MIT, Starlette,
Jinja2 and uvicorn BSD-3). `requirements.txt` (runtime) and `requirements-build.txt` (the CLI's
dependencies for the image build) are pinned with hashes; regenerate them with the `uv pip compile`
lines at the top of the `.in` files.

## Deploy

`Dockerfile`, `fly.toml` and `.dockerignore` are at the repository root; see `docs/deploy.md`.
