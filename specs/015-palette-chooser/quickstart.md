# Quickstart: Palette chooser

```bash
cd cli
poetry run lego-image-processor map cells land-elevation -o cells.json --arrangement B
PYTHONPATH=tools poetry run python -m kit31203 ice-mask --check     # needs the cached ERSST LTM file

cd ../web
python -m web98138.prebuild --out site --maps land-elevation,ocean-sst --no-prices
WEB98138_SITE_DIR=site uvicorn web98138.app:app --port 8080
# open http://localhost:8080/maps/land-elevation/A → "Try other colors"
```

Check: set 5 land classes, edit a bound, pick colors, switch "Show as White ice", reload (the
fragment restores it), Reset (the built preview returns). With JavaScript off the page is the
feature 008 page plus a note.
