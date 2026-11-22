# Contract: HTTP routes (008)

All routes GET (HEAD allowed). Anything else: 404 page (HTML) or 405.

| Route | Response |
|---|---|
| `/` | 200 HTML: gallery of 4 maps |
| `/about` | 200 HTML |
| `/maps/{map_id}` | 307 → `/maps/{map_id}/A` (404 if unknown map) |
| `/maps/{map_id}/{c}` | 200 HTML for `c` in A, B, C; lowercase a/b/c → 301 to uppercase; other → 404 |
| `/maps/{map_id}/{c}/preview.png` | 200 `image/png` inline |
| `/maps/{map_id}/{c}/thumb.png` | 200 `image/png` inline |
| `/maps/{map_id}/{c}/download/{kind}` | 200 attachment; `kind` from the fixed set present in the manifest; 404 otherwise |
| `/manifest.json` | 200 `application/json` (the build manifest) |
| `/healthz` | 200 `{"status":"ok","variants":12,"generated_at":...,"version":...}` |
| `/static/style.css` | 200 `text/css` |
| `/robots.txt` | 200 `text/plain`, allow all |

Content types: json `application/json`, xml `application/xml`, csv `text/csv; charset=utf-8`,
pdf `application/pdf`, png `image/png`.
Download header: `Content-Disposition: attachment; filename="98138-world_<map>_<C>_<kind>.<ext>"`.
Every response: CSP and security headers (research R6); no `Set-Cookie`.
Host `www.98138.world` → 301 `https://98138.world{path}`.
Unknown routes → 404 HTML page with the footer.

## Prebuild CLI

```
python -m web98138.prebuild --out DIR [--maps ID,...] [--combinations A,B,C]
                            [--cache-dir DIR] [--fetch] [--quiet]
```
Exit 0 ok; 1 build error (message + disclaimer); 2 usage. Without `--fetch`, a missing dataset is
an error naming `--fetch`. Prints one line per variant and the total size and time.
Environment `GIT_COMMIT` (optional) is recorded in the manifest.

## Service configuration

Environment `WEB98138_SITE_DIR` (default `/site` in the container; required locally).
`create_app(site_dir)` for tests. `web98138.app:app` is the ASGI app built from the environment
lazily at import.
