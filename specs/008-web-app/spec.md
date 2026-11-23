# Feature Specification: Web App (pick, preview, download)

**Feature Branch**: `008-web-app`

**Created**: 2026-11-22

**Status**: Implemented (owner decisions 1–6 relayed by the coordinating agent and recorded as
user-confirmed; agent decisions logged in `run-state.md` for owner review)

**Input**: Owner brief, relayed by the coordinating agent on 2026-11-22: "Build feature 008, the
first web app for 98138.world" with six owner decisions (scope v1: pick, preview, download; stack:
one Python service with server-rendered templates; prebuilt outputs; Fly.io deployment; footer,
privacy and design; security basics). See `run-state.md`.

## Context

Features 001–007 built a CLI and library that turn a recipe into a layout on the kit 31203
template, a preview, a parts list with cited IDs, marketplace files and printable build sheets, in
any of the kit's three frame combinations. Nobody can use any of this without installing Python.
This feature puts the four bundled maps on the web at 98138.world so that a visitor can look at
them and download everything needed to build one.

Constitution principle VI applies directly: the web app MUST call the CLI library and MUST NOT
duplicate its logic. The constitution defers the web stack, performance and scale targets to this
first web feature's specification; they are set here (FR-020–FR-024, SC-004–SC-006).

The four bundled maps: `official-31203` (the kit's own design), `official-31203-bathymetry` (the
official look derived from ocean depth), `ocean-sst` (sea surface temperature), `land-elevation`
(elevation on land). The three combinations: A (frames 1·2·3, Europe and Africa in the centre,
default), B (3·1·2, America), C (2·3·1, Asia and Australia) (LEGO 31203 building instructions,
pp. 7–8; `data/kit_31203_arrangements.json`).

## Clarifications

### Session 2026-11-22 (owner decisions, relayed by the coordinating agent)

- Q: What is in scope for v1? → A: Pick one of the 4 bundled maps and a combination (A, B, C), see the stud preview, download layout JSON, parts list (and `--kits 1` top-up), BrickLink XML, Rebrickable CSV, build-sheet PDF; show description, citation, license, parts summary; an About page. No uploads, accounts or recipe editing. (user)
- Q: What stack? → A: One Python service importing `lego_image_processor`, server-rendered Jinja2 templates, minimal hand-written CSS, little or no JS, no front-end build, in a top-level `web/` directory with its own pyproject and offline tests; framework chosen in research.md, permissive licenses only. (user)
- Q: Build on demand or ahead of time? → A: Ahead of time: a build step builds all 12 variants and every download with a manifest (checksums, tool version); the image runs it at build time; the running app serves files only and fits shared-cpu-1x 256 MB. (user)
- Q: Where is it deployed? → A: Fly.io, app `world-98138` (unless taken), region sjc or lax, internal port 8080, forced HTTPS, auto stop/start; `docs/deploy.md` with exact steps and Hover DNS records. The agent does not run fly commands that change anything. (user)
- Q: Footer, privacy and design? → A: Disclaimer, repo link, dataset citations, Rebrickable acknowledgement; no trackers, analytics or cookies; accessible, responsive, calm, map-forward; crisp previews (8–12 px per stud) and gallery thumbnails from the library renderer. (user)
- Q: Security basics? → A: Fixed routes, validated IDs, no user-supplied paths, correct content types and file names, cache headers, no debug in production, non-root container. (user)

### Session 2026-11-22 (autonomous clarify)

- Q: URL scheme for a variant? → A: `/maps/<map-id>/<A|B|C>`; `/maps/<map-id>` redirects to `/A`; a lowercase combination redirects (301) to uppercase; downloads at `/maps/<map-id>/<C>/download/<kind>`. (agent decision: readable, fixed, maps directly onto validated manifest keys)
- Q: Paper size of the build-sheet PDF? → A: Both US Letter and A4, as two downloads. (agent decision: the CLI supports both; the site serves an international audience; +~23 MB of output. CLOSE CALL, FOR OWNER REVIEW: the brief named one PDF)
- Q: Format of the "parts list" download? → A: The CLI's parts list JSON (`parts list -o`), full and one-kit top-up; the page shows the same lots as a table. (auto-resolved: specs/005-parts-lists contracts; the CLI's file output is JSON)
- Q: What does the page show for the parts summary? → A: lots, pieces, pieces one kit covers (needed minus to-buy with `--kits 1`), pieces and lots to buy with one kit; per lot: color, part, LEGO/BrickLink/Rebrickable IDs, needed, one kit supplies, to buy. (auto-resolved: PartsList.totals() and Lot.to_dict() in cli/src/lego_image_processor/parts/partslist.py)
- Q: `www.98138.world`? → A: Gets its own certificate and is redirected (301) to `https://98138.world` by the app. (agent decision: one canonical host)
- Q: Health check route? → A: `GET /healthz` → `{"status": "ok", "variants": 12, ...}`; also used by the Fly HTTP check. (agent decision)
- Q: Is the manifest public? → A: Yes, at `/manifest.json`, so anyone can check file checksums. (agent decision: reproducibility, constitution IV)
- Q: Does the runtime image contain the CLI library? → A: No. The library runs in the build stage; the runtime stage copies the output and installs only the web service and its server dependencies. Principle VI is met because every file and every number shown comes from the library at build time. (agent decision: memory and image size, owner decision 3 invites it)
- Q: Minimum machines? → A: `min_machines_running = 0` with `auto_stop_machines = "stop"` (recommended in plan.md; cold start is a second or two). (agent decision, FOR OWNER REVIEW)
- Q: Round studs in the preview? → A: No; the library's square-per-stud renderer at 10 px per stud (map pages) and 3 px (thumbnails), shown with pixelated scaling. A round-stud style would need a new CLI option (reserved: CLI flags). (agent decision)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick a map and see it (Priority: P1)

A visitor opens 98138.world on a laptop or phone, sees the four maps as a gallery of small
previews with a title and one-line description each, picks one, and sees a large, crisp stud
preview of it with its description, its data citation and license, and a summary of the parts it
needs (lots, pieces, and how much of it one 31203 kit covers).

**Why this priority**: it is the smallest useful site: it shows what the project does.

**Independent Test**: request the home page and each map page; each map page shows the preview
image, description, citation (for maps built from a dataset), license and parts summary, and every
page has the footer.

**Acceptance Scenarios**:

1. **Given** the home page, **When** it loads, **Then** it lists exactly the four bundled maps, each
   with a thumbnail, its title, its description and a link to its page.
2. **Given** a map page, **When** it loads, **Then** it shows the preview for combination A, the
   map's description, its layers (which is data-driven and which is background), the citation and
   license of every dataset it uses, and the parts summary: lots, pieces, pieces one kit covers and
   pieces to buy on top of one kit.
3. **Given** a map whose parts include colors beyond the kit, **When** the parts table is shown,
   **Then** each lot shows its LEGO, BrickLink and Rebrickable IDs and a Rebrickable
   acknowledgement appears on the page.
4. **Given** the map's suitability report has warnings, **When** the page loads, **Then** the
   warnings are listed in plain words.
5. **Given** a phone-width screen (360 px), **When** any page loads, **Then** the preview scales to
   the screen width with no horizontal scrolling and the downloads remain readable as a list.

---

### User Story 2 - Choose a frame combination (Priority: P1)

The visitor switches the map between combinations A, B and C and sees the preview, parts summary
and downloads for the board as hung that way.

**Why this priority**: the owner named the three combinations as part of the minimum scope.

**Independent Test**: open the same map in A, B and C; the preview images differ by a whole-frame
shift, the selected combination is marked, and the download links point at that combination's
files.

**Acceptance Scenarios**:

1. **Given** a map page, **When** the visitor picks B, **Then** the page shows the B preview, says
   "Combination B: frames 3·1·2, America in the centre", and every download is the B variant.
2. **Given** any combination, **When** the page is shown, **Then** the current combination is
   indicated visually and to assistive technology, and the other two are one tap away.
3. **Given** a combination value other than A, B or C, **When** it is requested, **Then** the site
   answers "not found" and never builds anything.

---

### User Story 3 - Download the build files (Priority: P1)

The visitor downloads the files to build the chosen map in the chosen combination: the layout
JSON, the parts list (full, and topped up from one owned 31203 kit), the BrickLink wanted list XML
and Rebrickable CSV (full and top-up), and the printable build-sheet PDF.

**Why this priority**: the end goal is a physical build (constitution V).

**Independent Test**: download every file of one variant; each has the right content type and a
descriptive file name, the layout validates as a schema 2.0 kit layout, the XML parses as a
BrickLink wanted list, the CSV has the Rebrickable header, and the PDF opens with 42 or more pages.

**Acceptance Scenarios**:

1. **Given** a map page, **When** the visitor looks at downloads, **Then** each file is listed with
   what it is for, its format and its size.
2. **Given** a top-up file where one kit already covers every piece, **When** the page is shown,
   **Then** it says "One kit covers every piece; nothing to buy" instead of offering an empty file.
3. **Given** any download, **When** it is fetched, **Then** the file name names the site, the map
   and the combination (for example `98138-world_ocean-sst_B_bricklink.xml`) and is sent as an
   attachment with the correct content type.
4. **Given** the same deployed build, **When** a file is downloaded twice, **Then** the bytes are
   identical and match the checksum in the build manifest.

---

### User Story 4 - Understand the project (Priority: P2)

The visitor reads an About page that explains the project: the kit as a fixed template, maps as a
land layer and an ocean layer described by a recipe, where the data comes from, the three frame
combinations, that the site is open source, and that it is not affiliated with LEGO.

**Why this priority**: context and honesty; not needed to download a map.

**Independent Test**: the About page names the three combinations with their frame orders and
centres, links the source repository, and states there are no cookies or trackers.

**Acceptance Scenarios**:

1. **Given** the About page, **When** it loads, **Then** it explains A, B and C with their frame
   orders and centres and cites the building instructions pages.
2. **Given** the About page, **When** it loads, **Then** it links to the source repository and
   says that the site sets no cookies and uses no analytics.

---

### User Story 5 - Deploy and operate (Priority: P2)

The owner deploys the site to Fly.io at 98138.world by following written steps, and the running
service only serves files built ahead of time: it never downloads datasets or builds maps while
serving visitors, and it runs on the smallest machine size.

**Why this priority**: the site must go live, but the pages and files come first.

**Independent Test**: the build step produces all 12 variants and a manifest from the pinned
datasets; the service starts from that output alone, answers a health check, and refuses to start
(clear error) if the output is missing or incomplete. The deploy document lists every command and
DNS record.

**Acceptance Scenarios**:

1. **Given** the pinned datasets, **When** the build step runs, **Then** it writes 4 maps × 3
   combinations of every file plus a manifest listing each file's size and SHA-256 and the tool
   versions and dataset checksums used.
2. **Given** the built output, **When** the service starts with no network access, **Then** every
   page and file is served.
3. **Given** the health check route, **When** it is requested, **Then** it answers 200 with a short
   machine-readable status once the manifest is loaded.
4. **Given** `docs/deploy.md`, **When** the owner follows it, **Then** it gives the exact commands
   to create the app, deploy, add certificates for `98138.world` and `www.98138.world`, and the
   DNS records to add at the domain's registrar (Hover).

### Edge Cases

- An unknown map ID, a combination other than A/B/C, an unknown download kind, or a path with
  traversal characters: "not found" (404), nothing read outside the built output.
- Lowercase combination in a URL (`/maps/ocean-sst/b`): redirect to the uppercase canonical URL.
- A top-up export with nothing to buy (one kit covers the map): no file; the page says so.
- A map with no dataset (`official-31203`): the page cites the kit design source instead of a
  dataset.
- Output directory missing, manifest missing, or a file listed in the manifest missing or with the
  wrong size: the service fails at start-up with a clear message rather than serving broken links.
- A visitor with images disabled or a screen reader: every preview has a text alternative naming
  the map and combination.
- Wide screens: the preview does not grow beyond a comfortable width; it is never blurry (studs
  stay square-edged when scaled).

## Requirements *(mandatory)*

### Functional Requirements

**Pages and content**

- **FR-001**: The site MUST offer exactly the four bundled maps (`official-31203`,
  `official-31203-bathymetry`, `ocean-sst`, `land-elevation`) and the three combinations (A, B,
  C), 12 variants in all. No uploads, accounts or recipe editing.
- **FR-002**: The home page MUST show a gallery of the four maps, each with a thumbnail preview,
  title, one-line description and link to its page.
- **FR-003**: Each map page MUST show, for the chosen combination: a large preview (at least 8 px
  per stud), the map's title and description, its two layers and their roles, the citation and
  license of each dataset it uses (or the kit design source), its suitability warnings, the parts
  summary (lots, pieces, pieces one kit covers, pieces and lots to buy with one kit) and a table of
  lots with LEGO, BrickLink and Rebrickable names and IDs and counts.
- **FR-004**: Each map page MUST let the visitor switch between A, B and C with plain links, mark
  the current one, and describe it ("frames 3·1·2, America in the centre").
- **FR-005**: Each map page MUST list its downloads with a description, format and size: layout
  JSON; parts list JSON (full) and parts list JSON topped up from one kit; BrickLink wanted list
  XML and Rebrickable CSV, full and one-kit top-up; build-sheet PDF.
- **FR-006**: When a one-kit top-up has nothing to buy, the page MUST say so and offer no file for
  that export.
- **FR-007**: An About page MUST explain the project, the template, recipes and layers, the data
  sources, the three combinations (citing the building instructions pp. 7–8), the open-source
  repository and the privacy stance.
- **FR-008**: Every page MUST show a footer with "Not affiliated with or endorsed by The LEGO
  Group." and a link to the source repository (https://github.com/kcaylor/98138_world). Pages
  showing Rebrickable IDs MUST show the Rebrickable acknowledgement; pages showing a map built from
  a dataset MUST show that dataset's citation and license.
- **FR-009**: Pages MUST work without JavaScript, set no cookies, and load nothing from third
  parties (no trackers, analytics, fonts or scripts from other sites).
  *Amended by feature 015 (FR-020, owner decision 2026-11-22): the only script allowed is the
  site's own hand-written `/static/palette.js` on map pages (progressive enhancement; no inline
  script, no front-end build); pages still work fully without it.*
- **FR-010**: Pages MUST be usable on a 360 px wide phone without horizontal scrolling, and meet
  basic accessibility: one `h1` per page, landmarks, text alternatives for images, visible focus,
  sufficient contrast, a language attribute, and the current combination exposed to assistive
  technology.

**Files and downloads**

- **FR-011**: Every download MUST be produced by the CLI library (the same functions behind `map
  build`, `parts list`, `parts export` and `sheets build`); the web code MUST NOT reimplement
  mapping, parts or sheet logic.
- **FR-012**: Downloads MUST be sent as attachments with the correct content type and a file name
  of the form `98138-world_<map>_<combination>_<kind>.<ext>`.
- **FR-013**: Previews MUST be rendered by the library's preview renderer: a large image of at
  least 8 px per stud for map pages and a small thumbnail for the gallery, displayed without
  smoothing so studs stay sharp.

**Prebuilt outputs**

- **FR-014**: A build step MUST produce every file for all 12 variants into an output directory
  from the bundled recipes and pinned datasets, downloading missing pinned datasets (verified by
  checksum) only during this step.
- **FR-015**: The build step MUST write a manifest listing, for every variant, every file's path,
  size, SHA-256 and content type, plus the tool versions, recipe checksums and dataset checksums
  used and the build time.
- **FR-016**: The build step MUST accept a subset of maps and combinations, and a dataset cache
  location, so tests can build a small output offline.
- **FR-017**: The running service MUST serve pages and files from the built output only: it MUST
  NOT download datasets or build maps while serving.
- **FR-018**: The service MUST check the output at start-up (manifest present, every listed file
  present with the listed size) and fail with a clear error otherwise.
- **FR-019**: The service MUST answer a health check route with 200 and a small JSON status.

**Stack, security and deployment**

- **FR-020**: The service MUST be one Python process that renders HTML on the server from
  templates, with hand-written CSS and no front-end build step; every dependency MUST have a
  permissive license.
- **FR-021**: Only fixed routes MUST exist; map IDs, combinations and download kinds MUST be
  validated against the manifest, and no part of a URL may be used as a file path.
- **FR-022**: Responses MUST carry correct content types, security headers (content security
  policy allowing only the site itself, no sniffing, no framing, strict referrer policy) and cache
  headers (built files cacheable; pages briefly cacheable). Production MUST NOT run in debug mode.
- **FR-023**: The container MUST build the outputs during the image build and run the service as a
  non-root user; the running image MUST NOT need the build-only tools.
- **FR-024**: The repository MUST include the deployment configuration for Fly.io (app, region,
  internal port 8080, forced HTTPS, automatic stop/start, health check) and `docs/deploy.md` with
  the exact commands, the certificate steps for `98138.world` and `www.98138.world`, the DNS
  records to add at Hover, and a container build smoke test.

### Key Entities

- **Variant**: one map in one combination (12 in all); has a preview, a thumbnail, a set of
  downloads and a parts summary.
- **Download**: one built file of a variant: kind (layout, parts, parts-1kit, bricklink,
  rebrickable, bricklink-1kit, rebrickable-1kit, sheets), path, size, SHA-256, content type,
  download file name.
- **Manifest**: the record of a build: tool versions, recipe and dataset checksums, build time,
  maps with their descriptions, layers, citations, warnings, and variants with their downloads and
  parts summaries.
- **Combination**: A, B or C, with frame order, centre and name, from the kit arrangement data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can go from the home page to downloading the build-sheet PDF for any map in
  any combination in at most three clicks.
- **SC-002**: All 12 variants and their files are available; every file's checksum matches the
  manifest (100%).
- **SC-003**: Every page passes a check for the required footer text, the repository link, no
  cookies set, and no third-party resource references (100% of pages).
- **SC-004**: The running service uses at most 150 MB of memory under normal load, so it fits the
  smallest Fly.io machine (256 MB).
- **SC-005**: Pages are served in under 200 ms at the server for a single visitor (no work beyond
  rendering a template from data in memory).
- **SC-006**: The build step for all 12 variants completes in under 5 minutes on a laptop with
  datasets cached.
- **SC-007**: Pages are readable at 360 px width with no horizontal scrolling.

## Assumptions

- Traffic is small (a hobby site); one machine with automatic stop/start is enough. Scale targets
  beyond that are out of scope.
- Build outputs change only when the site is redeployed, so they can be cached by browsers for a
  day.
- The parts summary "what one kit covers" means the pieces of the map supplied by one 31203 kit
  (the CLI's `--kits 1`), with no spares.
- Build sheets are offered on US Letter and A4 paper (agent decision; the CLI supports both).
- The site is in English only.
- Out of scope: uploads, accounts, custom recipes, on-demand builds, prices, search, analytics.
