# Feature Specification: Price Estimates for Maps

**Feature Branch**: `011-price-estimates`

**Created**: 2026-11-22

**Status**: Draft (four scoping decisions answered by the user on 2026-11-22; see Clarifications
and `run-state.md`)

**Input**: User description: "Build a pricing tool for maps. The maintainer runs it locally during
map development; it gives an estimated price that is shown on the web site. The tool never runs in
the web app." Scoping answers (user, 2026-11-22): (1) price source: the official BrickLink API
price guide, OAuth 1.0 credentials from environment variables; (2) the site shows two estimates per
map variant: every map piece, and only the pieces needed beyond one 31203 kit; (3) statistic:
average price of new parts sold in the last 6 months, USD, with a low–high range from the minimum
and maximum sold prices, falling back to the current for-sale average, else unpriced; (4) delivery:
an online fetch command writes a dated, cited price snapshot committed as runtime reference data,
an offline command estimates any layout from it, and the web prebuild reads it offline.

## Context

Features 001–009 turn a recipe into a layout, a parts list with cited LEGO, BrickLink and
Rebrickable IDs, marketplace files and build sheets, and 008 puts the six bundled maps on
98138.world in combinations A, B and C (18 variants). A visitor can download a BrickLink wanted
list, but has no idea what the pieces cost until they upload it. Feature 005 deliberately estimated
no prices (its FR-018; `PRICE_NOTE` in `parts/partslist.py` says "none are estimated") because a
price needs a marketplace API with credentials and changes daily. This feature changes that
decision on purpose, in a way that keeps the project's rules:

1. **Prices are reference data with a date, not a live feed.** The only network step is a
   maintainer command run on a laptop with the maintainer's own BrickLink API credentials. It
   writes a snapshot file of unit prices per lot (part + color) with its retrieval date and the
   exact query parameters, and the snapshot is committed under
   `cli/src/lego_image_processor/data/` like the other cited runtime data (constitution I, IV, V).
2. **Everything after the snapshot is offline and reproducible.** Estimating a layout reads only
   the layout and the snapshot, so anyone with the repository gets the same numbers to the cent,
   and tests run without the network (constitution IV, VII).
3. **The web site never talks to BrickLink.** The prebuild computes estimates through the CLI
   library and writes them into the manifest; the service stays file-only (008 FR-017, constitution
   VI).
4. **Lots are already identified.** BrickLink item numbers (4073 for the 1×1 round plate, LEGO
   6141; 98138 for the 1×1 round tile) and BrickLink color IDs are cited in `part_numbers.json`,
   `kit_colors.json` and `part_colors.json` (44 plate and 40 tile colors). The bundled recipes use
   19 lots: 10 plate colors (White plus the land-elevation scale) and the kit's 9 tile colors.
5. **BrickLink is owned by The LEGO Group** (since 2019). Using its API on a site that says "Not
   affiliated with or endorsed by The LEGO Group" makes the wording of attribution matter: the site
   must credit BrickLink as the price source without implying that BrickLink or LEGO endorses it.

## Clarifications

### Session 2026-11-22 (user scoping answers)

- Q: Where do prices come from? → A: The official BrickLink API price guide, authenticated with
  OAuth 1.0 (consumer key, consumer secret, token value, token secret). The maintainer supplies the
  four values in environment variables; they are never committed, logged or written to any output.
  Lots are identified by the cited BrickLink item numbers and color IDs already in the repository.
  (user)
- Q: What does the site show? → A: Two estimates for each map variant: buying every map piece (all
  10,240) and buying only what is needed beyond one 31203 kit (the one-kit top-up the site already
  offers as a parts list). (user)
- Q: Which statistic? → A: The average price of NEW parts SOLD over the last 6 months, in US
  dollars, with a low–high range from the minimum and maximum sold prices. A lot with no sales falls
  back to the current for-sale (stock) average and says so; a lot with no price at all is
  unpriced, and the estimate is marked incomplete with the number of unpriced pieces. (user)
- Q: How is it delivered? → A: A CLI command that needs keys and the network writes a dated, cited
  price snapshot (JSON of unit prices per lot), committed as runtime reference data; an offline CLI
  command estimates any layout from the snapshot (JSON and text, full and top-up); the web prebuild
  reads the snapshot offline through the CLI library and puts the estimates in the manifest and
  pages with the snapshot date and source. Tests are offline with a small fixture snapshot and a
  mocked HTTP layer. (user)

### Session 2026-11-22 (clarify, autonomous)

- Q: How does the web prebuild get the snapshot inside the Docker build? → A: It ships as package
  data in `cli/src/lego_image_processor/data/`, so `pip install ./cli` in the build stage installs
  it and the prebuild reads it through the library; the runtime stage never needs it (it gets only
  the built site). The test fixture snapshot cannot reach the image (`.dockerignore` excludes
  `cli/tests`). (auto-resolved: `Dockerfile` lines 19–29, `.dockerignore`, `cli/pyproject.toml`
  packages; same path as every other reference file the prebuild already reads)
- Q: Where do estimates go in `manifest.json`? → A: Per variant, as `estimates: {"full": …,
  "one_kit": …}` next to the existing `summary` in each `maps[].variants[C]` entry; the snapshot
  reference (file name, SHA-256, retrieval date, source, attribution, estimate wording, staleness)
  once, in a top-level `prices` block. The additions are optional keys (manifest `format_version`
  stays "1"): a site built without estimates omits them and its pages show no price section; when
  `prices` is present, `catalog.py` checks that every variant carries both estimates. No new file
  kind (`KINDS` unchanged). (auto-resolved: `web/src/web98138/prebuild.py` `build_variant` already
  returns per-variant `summary` and `nothing_to_buy_with_kit`, and `build_site` writes shared notes
  such as `price_note` once at top level; `catalog.py` validates `format_version`, variants and
  file kinds strictly)
- Q: How is the one-kit top-up quantity computed? → A: Exactly as the site's top-up parts list
  today: `build_parts_list(layout, owned=OwnedInputs(kits=1))`, per lot `to_buy` = max(0, needed −
  kit supply from the cited inventory), no loose, missing or spare parts. The estimate library
  accepts parts lists (the prebuild passes the `full` and `topup` lists it already builds) or a
  layout (it builds both). `parts estimate` always reports full and one-kit top-up; it does not
  take `--owned`/`--missing`/`--spares` in this feature. (auto-resolved:
  `cli/src/lego_image_processor/parts/partslist.py` `build_parts_list`, `parts/owned.py`
  `OwnedInputs`, `web/src/web98138/prebuild.py` lines 157–159; user answer 2 names the one-kit
  top-up)
- Q: Which HTTP library does the fetch use? → A: The standard library (`urllib.request`), with an
  injectable opener for mocked tests, as `datasets/cache.py` does; no new dependency. (auto-resolved:
  `cli/pyproject.toml` has no HTTP library; `cli/src/lego_image_processor/datasets/cache.py`
  `_default_opener`/`opener=`)
- Q: Is OAuth 1.0 signing hand-written or a new dependency? → A: Hand-written with the standard
  library (`hmac`, `hashlib`, `base64`, `secrets`, `urllib.parse`): HMAC-SHA1 signature in the
  `Authorization` header per RFC 5849, tested against the RFC's published example and fixed
  nonce/timestamp vectors. `requests-oauthlib` is not added (it would bring `requests` and
  `oauthlib` into the CLI's runtime dependencies and the hashed `web/requirements-build.txt` for
  about 50 lines of code). (auto-resolved: no-new-dependency choice follows the stdlib-only fetch
  pattern; a new dependency would have been escalated)
- Q: Where is the BrickLink API base URL kept, given constitution VI ("no hardcoded secrets or
  proprietary endpoints" in CLI code)? → A: The API is publicly documented, so it is not treated as
  a private endpoint; its base URL and documentation URL are kept in cited reference data, not in
  code, as dataset URLs are kept in `data/datasets.json`, and are copied into the snapshot's source
  block. The plan's Constitution Check records this. (auto-resolved: constitution VI and IV;
  `data/datasets.json` pattern; flagged for owner review in `run-state.md`)
- Q: Where do test fixtures live? → A: `cli/tests/fixtures/prices/`: a small synthetic snapshot
  (the official layout's 10 lots and the `land-elevation` fixture's lots, plus one stock-only lot
  and one missing lot), with a `.source.json` saying its values are synthetic and not BrickLink
  data; and synthetic API responses in the documented response shape for the mocked fetch. Web
  tests pass the CLI fixture snapshot to `build_site` through a snapshot-path parameter (default:
  the packaged snapshot). (auto-resolved: `cli/tests/fixtures/datasets/*.source.json` convention;
  `web/tests/conftest.py` prebuilds offline from CLI fixtures)
- Q: Does the site offer an estimate download file? → A: No; estimates appear in the manifest and
  on map pages only (user answer 4), and the CLI command writes JSON for anyone who wants a file.
  (auto-resolved: user answer 4; `KINDS` unchanged)

### Session 2026-11-22 (user answers to clarify escalations)

- Q: BrickLink's API Terms of Use could not be read on 2026-11-22 (bricklink.com was down for
  maintenance). Build and publish prices now, or gate them? → A: Build everything and ship prices:
  assume the terms allow publishing derived estimates with attribution and committing the per-lot
  snapshot. A real snapshot is committed once the owner runs the fetch with their keys, and the
  site shows prices from the next deploy. The owner will check the terms when the site is back.
  (user)
- Q: Which average? → A: The quantity-weighted average (`qty_avg_price`); the plain per-sale
  average (`avg_price`) is recorded in the snapshot too. (user)
- Q: Names? → A: As proposed: `parts prices fetch`, `parts estimate LAYOUT`,
  `BRICKLINK_CONSUMER_KEY`, `BRICKLINK_CONSUMER_SECRET`, `BRICKLINK_TOKEN_VALUE`,
  `BRICKLINK_TOKEN_SECRET`, `cli/src/lego_image_processor/data/bricklink_price_guide.json`, and
  manifest `variants[].estimates.full` / `.one_kit` plus a top-level `prices` block. (user)
- Q: Constitution VI ("no proprietary endpoints") and the BrickLink API? → A: A publicly
  documented API with user-supplied credentials is not a proprietary endpoint; its base URL lives
  in cited reference data, not in code, and the plan's Constitution Check records this. No
  amendment. (user)
- Attribution text (agent, for the owner to check against the terms): "Price data: BrickLink price
  guide (bricklink.com). BrickLink is a trademark of LEGO BrickLink, Inc. Not endorsed by
  BrickLink." It replaces the draft's "BrickLink Corporation" wording, since BrickLink's terms of
  service (updated 2025-09-18) name LEGO BrickLink, Inc. as the operator.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Estimate the cost of any layout from the committed snapshot (Priority: P1)

A maker or the maintainer points the tool at a layout file and gets an estimated cost in US
dollars: the total for buying every map piece, the total for buying only what is needed beyond one
31203 kit, each with a low–high range, the snapshot date and source, and per-lot detail (quantity,
unit price, which statistic priced it, line total). Lots the snapshot cannot price are listed, and
the estimate says it is incomplete and how many pieces are unpriced. No network and no credentials
are needed.

**Why this priority**: it is the core value (a number a maker can plan with) and it works from the
committed snapshot alone, so it is usable and testable before any fetch is run on a real account.
A small fixture snapshot is enough to deliver it.

**Independent Test**: with a fixture snapshot and the official layout (and a recipe-built fixture
layout), compute estimates; check each line total and the totals against hand-computed values;
run twice and compare bytes; run with the network disabled.

**Acceptance Scenarios**:

1. **Given** the official layout and a snapshot that prices all 10 of its lots from sales, **When**
   the maker estimates it, **Then** the full estimate's average equals the sum over lots of
   quantity × unit average price, its low and high equal the sums with the unit minimum and
   maximum, the estimate is complete, and with one kit there is nothing to buy (top-up total $0.00,
   stated as "One kit covers every piece").
2. **Given** a layout that needs pieces beyond one kit (for example `land-elevation`), **When**
   estimated, **Then** the top-up estimate prices only each lot's quantity to buy from the one-kit
   parts list (feature 005, `--kits 1`), and the full estimate prices every needed piece.
3. **Given** a lot whose snapshot entry has no sales but has a for-sale average, **When** estimated,
   **Then** that lot is priced from the for-sale (stock) average and range, marked "for-sale
   price (no sales in 6 months)", and the estimate summary counts the lots and pieces priced that
   way.
4. **Given** a lot with no snapshot entry, no price at all, or no verified BrickLink IDs (an
   unverified lot from 005), **When** estimated, **Then** the lot is listed as unpriced with the
   reason, contributes nothing to the totals, and the estimate is marked incomplete with the number
   of unpriced lots and pieces.
5. **Given** the same layout and snapshot twice, **When** estimated as JSON, **Then** the two files
   are identical (no timestamp in the output; the snapshot's own date is recorded).
6. **Given** a snapshot older than the staleness threshold (default 90 days) on the date the
   estimate is made, **When** estimated, **Then** the output warns that prices are from that date
   and may be out of date; the numbers are unchanged.
7. **Given** any estimate output, **When** read, **Then** it says it is an estimate, that it
   excludes shipping, fees and taxes and that marketplace prices vary, names the price source and
   date, carries the BrickLink attribution, and ends with "Not affiliated with or endorsed by The
   LEGO Group."
8. **Given** a missing, unreadable or wrong-format snapshot, or a layout the parts list rejects,
   **When** estimated, **Then** the command fails with the reason and writes nothing.

---

### User Story 2 - Fetch a cited price snapshot from BrickLink (Priority: P2)

The maintainer, with BrickLink API credentials in four environment variables, runs one command
that queries the BrickLink price guide for every lot the bundled recipes use (and, on request,
every cited plate and tile color) and writes a price snapshot: for each lot, the six-month
new-sold statistics and the current new for-sale statistics, with counts, plus the retrieval date,
the API parameters, the guide types, currency and condition. The fetch is polite to the API, can be
interrupted and resumed, and never prints or stores the credentials. The maintainer reviews the
file and commits it.

**Why this priority**: it produces the real data behind US1 and US3, but it needs a BrickLink
account and the network, so it comes after the offline core, which a fixture snapshot can drive.

**Independent Test**: with a mocked HTTP layer, run the fetch for a few lots: check the requests
(item type, item number, color, guide type, condition, currency, region), the snapshot written
(provenance and per-lot values), behaviour on rate-limit and server errors, resume after an
interruption, and that no credential value appears in any output, log line or file.

**Acceptance Scenarios**:

1. **Given** credentials in the environment and the default lot set, **When** the maintainer runs
   the fetch, **Then** the snapshot holds an entry for every lot used by any bundled recipe in any
   combination (19 lots today), each keyed by part and LEGO color ID with its BrickLink item type,
   item number and color ID from the cited tables.
2. **Given** the option to include all cited colors, **When** the fetch runs, **Then** the snapshot
   also holds every plate and tile color in `kit_colors.json` and `part_colors.json`.
3. **Given** each lot, **When** it is fetched, **Then** two price-guide queries are made: six-month
   sold, new, US dollars; and current for-sale (stock), new, US dollars; and the entry records, for
   each, the average price used, the minimum and maximum, the number of sales or listings and the
   total quantity.
4. **Given** a completed fetch, **When** the snapshot is read, **Then** it records the source
   (BrickLink API price guide, endpoint family, API documentation URL), the retrieval date and time
   (UTC), every query parameter that affects the numbers, the condition, currency, region and
   period, the tool version, the lot set used, the attribution text and the disclaimer.
5. **Given** a fetch interrupted after some lots (network failure, rate limit, or the maintainer
   stops it), **When** it is run again with the resume option, **Then** lots already fetched in
   that run are kept and only the rest are queried; the snapshot is marked complete only when every
   lot has been fetched.
6. **Given** the API answers "too many requests" or a server error, **When** the fetch continues,
   **Then** it waits and retries with increasing delay up to a limit, and if the limit is reached it
   stops, keeps the progress so far, and says how to resume.
7. **Given** a missing credential variable, **When** the fetch starts, **Then** it fails before any
   request, naming the missing variable (never a value); **given** credentials the API rejects,
   **then** it stops at the first rejection with BrickLink's error code and message and writes no
   snapshot.
8. **Given** any run, **When** its output, logs, errors and written files are searched, **Then** no
   credential value or OAuth signature appears in any of them.
9. **Given** a new snapshot replacing an older one, **When** the fetch finishes, **Then** it prints
   a summary: lots fetched, lots priced from sales, from stock only, and unpriced, and the largest
   changes in unit average price against the previous snapshot.

---

### User Story 3 - Show estimates on 98138.world (Priority: P3)

A visitor on a map page sees two estimates for the chosen map and combination: "every piece" and
"on top of one 31203 kit", each as an average with a low–high range in US dollars, the date of the
prices and their source, and plain words that it is an estimate that excludes shipping, fees and
taxes. If some pieces could not be priced, the page says the estimate is incomplete and how many
pieces it leaves out.

**Why this priority**: it is the user-visible goal, but it depends on US1 (the library function)
and on a committed snapshot from US2, and on the open terms-of-use question.

**Independent Test**: prebuild the test variants from a fixture snapshot; check that the manifest
holds both estimates per variant with the snapshot's date, source and completeness, that the map
page shows them with the required wording and attribution, and that the service still starts and
serves with no network and never imports the CLI library.

**Acceptance Scenarios**:

1. **Given** a prebuild with the committed snapshot, **When** it finishes, **Then** every variant
   in the manifest carries a full estimate and a one-kit top-up estimate (average, low, high,
   complete or not, unpriced lots and pieces, lots priced from stock), and the manifest records the
   snapshot's file name, SHA-256, retrieval date and source once.
2. **Given** a map page, **When** it loads, **Then** it shows both estimates (for example
   "Every piece: about $412 (range $260–$1,150)" and "On top of one kit: about $96 (range
   $55–$310)"), the date of the prices, the source with a link to BrickLink, the words "Estimate
   only; excludes shipping, fees and taxes; prices vary by seller and over time", the BrickLink
   attribution, and the existing footer disclaimer.
3. **Given** a variant whose one-kit top-up has nothing to buy, **When** its page loads, **Then**
   the top-up estimate reads "One kit covers every piece" rather than "$0".
4. **Given** an incomplete estimate, **When** the page loads, **Then** it says "Incomplete: N
   pieces in M colors could not be priced" next to the figure.
5. **Given** a snapshot older than the staleness threshold at prebuild time, **When** the page
   loads, **Then** it carries a visible note that the prices are from that date and may be out of
   date.
6. **Given** the running service, **When** it serves any page, **Then** it makes no outbound
   request and reads estimates only from the built output.
7. **Given** no snapshot is available to the prebuild, **When** it runs, **Then** it fails with a
   clear message (the site does not silently drop prices); an explicit option builds without
   estimates, and the pages then show no price section.

### Edge Cases

- A lot priced from sales whose minimum equals its maximum (a single sale): range collapses to one
  value; shown as such.
- A lot whose sold average is far outside its min–max range or is zero: impossible by construction
  of BrickLink's figures; if a snapshot entry violates min ≤ average ≤ max or has a negative or
  zero price, the snapshot is rejected as invalid when loaded.
- A layout using a color the snapshot does not cover (for example an image-derived layout, or a
  cited color outside the default lot set): that lot is unpriced; the output suggests fetching with
  all cited colors.
- An unverified lot (no BrickLink IDs, 005 Q2): unpriced with reason "no verified BrickLink IDs".
- A snapshot marked incomplete (an interrupted fetch never resumed): estimating with it works but
  warns that the snapshot is partial; the web prebuild refuses a partial snapshot unless explicitly
  allowed.
- The BrickLink API's daily request limit is reached mid-fetch: the fetch stops, keeps progress and
  says to resume later.
- The BrickLink token is bound to an IP address and the maintainer is on another network: BrickLink
  rejects the request; the error says so and names the BrickLink setting to check, without showing
  the token.
- The same piece counted twice in a layout (not possible; lots come from the 005 parts list).
- Arrangement: estimates follow the parts list of the layout as given; variants whose pieces differ
  between combinations get different estimates, the others get the same ones.
- Rounding: unit prices are kept as BrickLink returns them (decimal, up to 4 places); line totals
  and totals are computed in exact decimal arithmetic and rounded half-up to cents only at the end;
  the site rounds displayed figures to whole dollars.
- Clock: staleness is judged against the date the estimate or prebuild runs (or a date given on
  the command line, so tests are deterministic).

## Requirements *(mandatory)*

### Functional Requirements

**Price snapshot (reference data)**

- **FR-001**: The package MUST ship a price snapshot file in `cli/src/lego_image_processor/data/`,
  with a documented format (format version, source, retrieval date-time UTC, query parameters,
  condition N, currency USD, region, guide types, period, lot set, completeness, tool version,
  attribution, disclaimer, and one entry per lot). It MUST NOT contain credentials or request
  signatures.
- **FR-002**: Each lot entry MUST record part (LEGO design ID and BrickLink item type and number),
  LEGO color ID and name, BrickLink color ID and name (from the cited tables), and for each of the
  two guide types queried (six-month sold, current stock), the average unit price, minimum,
  maximum, number of sales or listings and total quantity, or that no data was returned.
- **FR-003**: The snapshot MUST be validated when loaded (format version, required fields, prices
  non-negative, minimum ≤ average ≤ maximum, every lot's BrickLink IDs matching the cited tables);
  an invalid snapshot MUST be rejected with the reason.
- **FR-004**: The snapshot MUST be written deterministically (lots sorted by part, then LEGO color
  ID; fixed key order) so that re-writing the same fetched data gives identical bytes and diffs
  between snapshots are readable.

**Fetching (maintainer, online)**

- **FR-005**: A CLI command (proposed `parts prices fetch`) MUST query the BrickLink API price guide
  and write the snapshot. It is the only command in this feature that uses the network. It uses
  the standard library for HTTP and for OAuth 1.0 HMAC-SHA1 signing (no new dependency), and reads
  the API base URL from cited reference data rather than code.
- **FR-006**: Credentials MUST come only from four environment variables (proposed
  `BRICKLINK_CONSUMER_KEY`, `BRICKLINK_CONSUMER_SECRET`, `BRICKLINK_TOKEN_VALUE`,
  `BRICKLINK_TOKEN_SECRET`). The command MUST fail before any request when one is missing, naming
  only the variable. Credential values and OAuth signatures MUST NOT appear in standard output,
  errors, logs, the snapshot or any other file, including on failure.
- **FR-007**: The default lot set MUST be every lot used by any bundled recipe in any combination
  (A, B, C), derived from the recipes, not a hand-kept list; an option MUST add every cited plate
  and tile color; an option MAY restrict the fetch to named lots (for testing and repairs).
- **FR-008**: For each lot the command MUST query the price guide twice: guide type "sold", new
  condition, US dollars, the API's six-month period; and guide type "stock", new condition, US
  dollars; with no country or region filter (worldwide) and prices excluding VAT, and record those
  parameters in the snapshot.
- **FR-009**: The command MUST pace requests (default at most one request per second), retry
  rate-limit and server errors with increasing delays up to a set number of attempts, stop on
  authentication errors and on the API's daily-limit error, and keep the progress made.
- **FR-010**: Progress MUST be saved after each lot so that an interrupted fetch can be resumed
  with an option that reuses the lots already fetched with the same parameters; a snapshot is
  marked complete only when every lot in its lot set has been fetched.
- **FR-011**: On success the command MUST print a summary: lots fetched, priced from sales, from
  stock only, unpriced, and the largest unit-price changes against the snapshot it replaces.

**Estimating (offline)**

- **FR-012**: A CLI command (proposed `parts estimate LAYOUT`) and a library function MUST estimate
  a layout from the committed snapshot (or a snapshot named on the command line) with no network
  and no credentials. It MUST build the parts list through feature 005's library (no duplicate lot
  logic) and produce two estimates: **full** (every needed piece) and **one-kit top-up** (each
  lot's quantity to buy with one kit, as `parts list --kits 1`: `to_buy` with one kit's cited
  supply, no loose, missing or spare parts). The library function MUST also accept already built
  full and one-kit parts lists so the prebuild does not build them twice.
- **FR-013**: For each lot, the unit price MUST be the six-month new sold average when the lot had
  sales, else the current new for-sale average (marked as the fallback), else the lot is unpriced.
  The low and high unit prices MUST be the minimum and maximum of the same guide type.
- **FR-014**: Each estimate MUST report: average, low and high totals (sum of quantity × unit
  price), pieces and lots priced from sales, from stock, and unpriced, a complete/incomplete flag
  and, when incomplete, the unpriced lots and pieces with reasons.
- **FR-015**: Arithmetic MUST be exact decimal; totals rounded half-up to cents; outputs MUST carry
  no timestamp, so the same layout and snapshot give identical bytes.
- **FR-016**: Output MUST be available as a human-readable table and as JSON (format version,
  layout path and SHA-256 and provenance as in the 005 parts list, snapshot file name, SHA-256,
  retrieval date and source, staleness flag, both estimates with per-lot lines, notes, attribution
  and disclaimer).
- **FR-017**: The output MUST warn when the snapshot is older than the staleness threshold (default
  90 days; configurable; the reference date can be given for reproducible tests) and when the
  snapshot is partial.

**Wording and compliance**

- **FR-018**: Every estimate output (human, JSON, web) MUST say it is an estimate, excludes
  shipping, fees and taxes, and that prices vary by seller and over time; MUST name the price
  source and date; MUST carry the BrickLink attribution; and MUST end with (or carry in
  `disclaimer`) "Not affiliated with or endorsed by The LEGO Group." It MUST NOT imply that
  BrickLink or The LEGO Group endorses the project.
- **FR-019**: Feature 005's FR-018 ("prices MUST NOT be estimated or shown") is superseded: parts
  list files keep carrying no prices (their format is unchanged), and their price note MUST point
  to the estimate command instead of saying none are estimated.

**Web site**

- **FR-020**: The web prebuild MUST compute both estimates for every variant through the CLI
  library from the committed snapshot, offline, and write them into the manifest with the
  snapshot's file name, SHA-256, retrieval date, source, completeness and staleness: per variant
  as `estimates.full` and `estimates.one_kit`, and the snapshot reference once in a top-level
  `prices` block (optional keys; manifest format version unchanged). The snapshot is the packaged
  one by default (installed with the CLI in the image's build stage); a parameter names another
  file (tests use the fixture). It MUST fail without a snapshot or with a partial one unless
  explicitly told to build without estimates or to allow a partial snapshot. The catalog MUST check
  that every variant carries both estimates when the `prices` block is present.
- **FR-021**: Each map page MUST show both estimates (average and range, whole dollars), the price
  date, the source with a link to BrickLink, the estimate wording of FR-018, the BrickLink
  attribution, an "incomplete" note with counts when applicable, "One kit covers every piece" when
  the top-up has nothing to buy, and a staleness note when applicable.
- **FR-022**: The web service MUST remain file-only: it MUST NOT call BrickLink or any other price
  source, hold credentials, or import the CLI library; the runtime image MUST NOT contain the
  credentials or the fetch command's configuration. The site keeps 008's no-JS, no-cookie,
  no-third-party-resource rules (a plain link to BrickLink is allowed).

**Tests**

- **FR-023**: Tests MUST NOT use the network: estimates use a small committed synthetic fixture
  snapshot in `cli/tests/fixtures/prices/` (with a `.source.json` saying it is synthetic);
  the fetch uses a mocked HTTP layer and fake credentials, and a test MUST check that no credential
  value reaches any output or file.

### Key Entities

- **Lot key**: part (LEGO design ID; BrickLink item type and number) and color (LEGO color ID;
  BrickLink color ID), from the cited tables.
- **Price-guide figures**: for one lot and one guide type (sold six months, or stock): average,
  minimum, maximum, count of sales or listings, total quantity, or "no data".
- **Price snapshot**: provenance (source, retrieval time, parameters, lot set, completeness, tool
  version), attribution, disclaimer, and one entry per lot with its two sets of figures.
- **Estimate line**: a lot, its quantity, the unit average, low and high used, the basis (sold,
  stock fallback, unpriced with reason) and its line totals.
- **Estimate**: full or one-kit top-up; totals (average, low, high), counts by basis, completeness,
  unpriced lots and pieces.
- **Estimate report**: layout reference and provenance, snapshot reference, staleness, both
  estimates, notes, attribution, disclaimer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every bundled recipe in every combination (18 variants), an estimate from a
  complete snapshot of the default lot set prices every lot (no lot unpriced for lack of an entry).
- **SC-002**: Any estimate recomputed from the committed snapshot and the same layout reproduces
  the published figures to the cent (100% of variants), and repeated runs give byte-identical JSON.
- **SC-003**: Estimating a 10,240-position layout takes under 2 seconds on a laptop, with no
  network.
- **SC-004**: A full default fetch (19 lots, 38 queries) completes in under 5 minutes at the
  default pace, and a fetch with all cited colors stays well within BrickLink's daily request limit.
- **SC-005**: In tests, no credential value or signature appears in any output, error, log or file
  (100% of fetch scenarios, including failures).
- **SC-006**: Every map page on the site shows both estimates with the date, source, attribution,
  estimate wording and disclaimer (100% of the 18 variant pages), and the service makes no outbound
  request.
- **SC-007**: The full CLI and web test suites pass with no network access.

## Assumptions

- The four scoping questions were asked and answered by the user on 2026-11-22 (see
  Clarifications); other details below are agent assumptions, recorded in `run-state.md`.
- The maintainer has a BrickLink account with API access and registers the consumer and token
  themselves; the token may be bound to an IP address, which is BrickLink's rule, not this tool's.
- "Average price" means BrickLink's quantity-weighted average (`qty_avg_price`) of the guide;
  the plain per-sale average (`avg_price`) is recorded alongside it in the snapshot for reference.
  The range uses the guide's `min_price` and `max_price`. (Agent assumption; the quantity-weighted
  figure is closer to what a buyer of thousands of pieces pays.)
- The six-month period is the one the BrickLink price guide's "sold" type covers; the tool does not
  choose it. "Stock" is the current listings at retrieval time.
- Worldwide prices (no country or region filter), excluding VAT, in USD; no currency conversion.
- The default staleness threshold is 90 days.
- The snapshot is committed under a fixed file name (proposed `bricklink_price_guide.json`); its
  date is inside the file. One current snapshot is kept; history lives in git.
- The site rounds to whole dollars; JSON keeps cents. Figures are per variant; variants with the
  same pieces show the same figures.
- The one-kit top-up uses the kit's full supply (005 `--kits 1`, no missing pieces, no spares), as
  the site's existing top-up parts list does.
- BrickLink's daily API request limit (5,000 requests per day at the time of writing, per its API
  documentation) is far above what one fetch needs (38 queries by default; 168 with all 84 cited
  colors); the pacing default is politeness, not a limit the tool must meet.
- Out of scope: shipping, fees and taxes; choosing stores or optimising a cart; used-condition
  prices; currencies other than USD; live prices on the site; BrickOwl or any other marketplace;
  pricing the frame, baseplates or any non-map kit part (map pieces only, as in feature 005);
  estimates for layouts uploaded on the site (there are no uploads).
- Not affiliated with or endorsed by The LEGO Group.
