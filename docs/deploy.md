# Deploying 98138.world on Fly.io

The site is one small Python service (`web/`, feature 008) in one Docker image. The image build
installs the CLI library, downloads the pinned public datasets (~561 MB: ~10.8 MB for the
first six maps, plus 385 MB of MOD17A3 NPP and 147 MB of MODIS-Aqua chlorophyll for `living-planet`,
feature 012, plus 0.7 MB of GPCP and 17.8 MB of NSIDC sea ice in 60 files for `rainfall`, feature
013; each checked by SHA-256 or, for the ERDDAP file, a content SHA-256), and prebuilds every
map in every frame combination (8 × 3 = 24 variants, ~146 MB) into `/site`. The builder needs about
650 MB of RAM at peak (the NPP GeoTIFF is read strip by strip, never decoded whole) and a little
over 1 GB of disk for the dataset cache.
The running container only serves those files: it never downloads data or builds maps, and it
fits Fly's smallest machine (shared-cpu-1x, 256 MB; measured ~60 MB RSS).

Map pages show price estimates (feature 011) from the committed BrickLink price snapshot
`cli/src/lego_image_processor/data/bricklink_price_guide.json`, installed with the CLI as package
data. The image build never calls BrickLink and holds no BrickLink credentials. Until a complete
snapshot is committed, the `Dockerfile` builds without prices (`ARG PREBUILD_PRICES=--no-prices`,
no price panel). After committing one, deploy with `--build-arg PREBUILD_PRICES=` (or change that
default) and the prebuild then **fails** if the snapshot is missing or partial. See "Refreshing
prices" below.

Configuration: `fly.toml` (app `world-98138`, region `sjc`, internal port 8080, forced HTTPS,
auto stop/start with `min_machines_running = 0`, health check `GET /healthz`), `Dockerfile`
(two stages, `python:3.11.18-slim-bookworm`, runs as uid 10001), `.dockerignore`.

Not affiliated with or endorsed by The LEGO Group.

## 0. Before you start

- For prices on the site: a complete price snapshot is committed (`git ls-files cli/src/
  lego_image_processor/data/bricklink_price_guide.json` prints it) and the deploy passes
  `--build-arg PREBUILD_PRICES=`. Without both, the site builds without price estimates.
- `flyctl` installed and logged in: `fly auth login` (check with `fly auth whoami`).
- Run every command below from the repository root (where `fly.toml` is).
- Optional local check (needs Docker; see "Smoke test" at the end).

## 1. Create the app (once)

```bash
fly apps create world-98138
```

If the name is taken, pick another (for example `world-98138-site`), change `app = ...` in
`fly.toml` to match, and use that name below wherever `world-98138` appears.

## 2. Deploy

```bash
fly deploy --build-arg GIT_COMMIT=$(git rev-parse HEAD)
```

The build runs on Fly's remote builder (no local Docker needed) and takes a few minutes the first
time. The `GIT_COMMIT` build argument is optional; it shows in the site footer and in
`/manifest.json`. A first deploy of an app with an HTTP service allocates a shared IPv4 and a
dedicated IPv6 address. Check:

```bash
fly status
fly ips list
curl -fsS https://world-98138.fly.dev/healthz     # {"status":"ok","variants":24,...}
open https://world-98138.fly.dev/
```

If `fly ips list` shows no IPv6 address, run `fly ips allocate-v6`; if it shows no IPv4, run
`fly ips allocate-v4 --shared`.

`fly deploy` may create two machines for redundancy. One is enough for this site:
`fly scale count 1` (optional).

## 3. Certificates for the domain

```bash
fly certs add 98138.world
fly certs add www.98138.world
```

Each command prints the DNS records Fly expects. Use the addresses it prints (they are the same
as `fly ips list`).

## 4. DNS records at Hover

The domain's nameservers are `ns1.hover.com` and `ns2.hover.com`, so the records are edited at
Hover: sign in → Domains → `98138.world` → **DNS** tab.

1. **Delete** the parking records: the `A` record for `@` that points at Hover's parking address,
   and any `*` (wildcard) or `www` record Hover created for parking or forwarding. Also turn off
   any Hover domain forwarding for the domain.
2. **Add** these records (Hover's "Add a record"; leave TTL at the default):

| Type | Hostname | Value |
|---|---|---|
| `A` | `@` | the IPv4 address from `fly ips list` (type `v4`, shared) |
| `AAAA` | `@` | the IPv6 address from `fly ips list` (type `v6`) |
| `CNAME` | `www` | `world-98138.fly.dev` |

3. Optional, to let Fly issue the certificate before DNS propagates or if validation stalls:
   `fly certs setup 98138.world` (and for `www.98138.world`) prints an
   `_acme-challenge` `CNAME` record (hostname `_acme-challenge` or `_acme-challenge.www`, value
   ending in `.flydns.net`). Add it exactly as printed.

## 5. Check

```bash
fly certs check 98138.world           # wait for "Ready" / issued certificate
fly certs check www.98138.world
dig +short A 98138.world               # the Fly IPv4
dig +short AAAA 98138.world            # the Fly IPv6
curl -sI https://98138.world/ | head -5                    # 200
curl -sI https://www.98138.world/about | grep -i location  # 301 to https://98138.world/about
curl -fsS https://98138.world/healthz
```

DNS changes at Hover usually show within minutes; allow up to an hour. Certificates are issued
once the `A`/`AAAA` records resolve to Fly.

## Updating the site

Commit, then `fly deploy --build-arg GIT_COMMIT=$(git rev-parse HEAD)`. Every deploy rebuilds all
variants from the pinned datasets; the files only change when the code, recipes or datasets do
(timestamps inside JSON and PDFs aside).

Useful: `fly logs` (startup and errors; access logs are off for privacy), `fly status`,
`fly machine list`. To avoid cold starts set `min_machines_running = 1` in `fly.toml` and redeploy
(one always-on 256 MB machine).

## Refreshing prices

Prices are only as fresh as the committed snapshot; pages say so once it is older than 90 days at
build time. Before a deploy that should carry new prices, on a machine whose IP the BrickLink API
token allows (specs/011-price-estimates/quickstart.md §4–5):

```bash
cd cli
export BRICKLINK_CONSUMER_KEY=… BRICKLINK_CONSUMER_SECRET=… BRICKLINK_TOKEN_VALUE=… BRICKLINK_TOKEN_SECRET=…
poetry run lego-image-processor parts prices fetch -o src/lego_image_processor/data/bricklink_price_guide.json
# if it stops: rerun the same command with --resume
git status          # the snapshot only; never a *.progress.json
poetry run pytest tests/unit/prices/test_packaged_snapshot.py
git add src/lego_image_processor/data/bricklink_price_guide.json && git commit
```

Then deploy as above. The credentials never go into the repository, the image or Fly secrets.
To check the site build locally without the network:
`python -m web98138.prebuild --out /tmp/site --prices cli/tests/fixtures/prices/bricklink_price_guide.json`
(`--no-prices` builds pages without the price panel; `--allow-partial-prices` accepts a partial
snapshot, and the pages then say it is partial). Neither option is used by the `Dockerfile`.

## Smoke test with Docker (optional, for anyone with Docker)

```bash
docker build --platform linux/amd64 -t world-98138 --build-arg GIT_COMMIT=$(git rev-parse HEAD) .
docker run --rm world-98138 id                         # uid=10001(app)
docker run --rm -d --name w98 -p 8080:8080 --memory 256m world-98138
curl -fsS http://localhost:8080/healthz                 # {"status":"ok","variants":24,...}
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" \
  http://localhost:8080/maps/ocean-sst/B/download/sheets-letter   # 200 application/pdf
docker stats --no-stream w98                            # memory well under 256 MiB
docker image ls world-98138                             # runtime image size
docker stop w98
```

The build stage needs network access (PyPI and the two dataset URLs in
`cli/src/lego_image_processor/data/datasets.json`).
