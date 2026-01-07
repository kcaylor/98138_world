# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**98138.world** is a LEGO map generation system that creates custom LEGO World Map-compatible building plans from satellite imagery. The project consists of:

1. **Python CLI tools** (designed for potential open-source release)
2. **Web application** (backend + frontend) hosted on Fly.io at 98138.world

Users upload satellite images, and the system generates:
- LEGO map designs compatible with the LEGO World Map kit format
- Complete parts lists with official LEGO part numbers
- Step-by-step building instructions

## Development Workflow: Speckit Commands

This project uses the **Speckit** workflow for structured feature development. Always follow this sequence:

### 1. Create Feature Specification
```bash
/speckit.specify "feature description here"
```
- Creates a new numbered feature branch (e.g., `1-feature-name`)
- Generates `specs/###-feature-name/spec.md` with user stories, requirements, and success criteria
- Validates specification quality with a requirements checklist
- **Output**: Technology-agnostic specification focused on user value

### 2. Build Technical Plan
```bash
/speckit.plan
```
- Must be run from a feature branch created by `/speckit.specify`
- Generates `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`
- Includes "Constitution Check" to verify compliance with project principles
- **Output**: Complete technical design ready for task breakdown

### 3. Generate Task List
```bash
/speckit.tasks
```
- Creates `tasks.md` with dependency-ordered, user-story-aligned tasks
- Tasks are organized by priority (P1, P2, P3) for incremental delivery
- Marks parallel-executable tasks with `[P]` flag
- **Output**: Actionable implementation checklist

### 4. Execute Implementation
```bash
/speckit.implement
```
- Checks prerequisites and validates all checklists before starting
- Executes tasks phase-by-phase, respecting dependencies
- Marks completed tasks with `[X]` in tasks.md
- **Output**: Working, tested implementation

### Additional Commands
```bash
/speckit.clarify          # Resolve spec ambiguities with targeted questions (max 5)
/speckit.checklist        # Generate custom validation checklists
/speckit.analyze          # Cross-artifact consistency analysis
/speckit.taskstoissues    # Convert tasks to GitHub issues
/speckit.constitution     # Update project constitution
```

## Project Constitution

The project constitution (`.specify/memory/constitution.md`) defines **seven core principles**:

### I. CLI-First Architecture
- **All features MUST work as standalone CLI commands first**
- Web UI consumes CLI tools; never duplicates logic
- CLI output: JSON + human-readable formats to stdout
- This enables testing, automation, and open-source release

### II. Modular & Open Source Ready
- CLI code lives in separate package(s) with independent versioning
- Zero hardcoded credentials or proprietary endpoints in CLI
- Web-specific features (auth, billing) isolated in backend

### III. Incremental Delivery (NON-NEGOTIABLE)
- Features delivered as independently testable user stories
- P1 user story = complete MVP
- Deploy/demo after each story before proceeding
- TDD: Write tests → Verify failure → Implement → Verify pass

### IV. Test-First Development
- Contract tests for all CLI commands (input/output validation)
- Integration tests for end-to-end workflows (image → map → parts list)
- Unit tests for critical algorithms (image processing, color matching)
- Test data MUST include real satellite imagery and LEGO reference data

### V. Performance & Scale Targets
- CLI: Process 1024x1024 image → LEGO map in <30 seconds
- Web API: Support 100 concurrent users
- File storage: Images up to 10MB, outputs up to 5MB
- Response time: Web UI interactions <2 seconds p95

### VI. Deployment & Infrastructure
- **Platform**: Fly.io with custom domain (98138.world)
- Backend: Dockerized Python (FastAPI or Flask)
- Frontend: Static-deployable (React/Vue/Svelte)
- Database: PostgreSQL (Fly.io Postgres)
- Secrets: Fly.io secrets only (never in code/git)
- Optimize for Fly.io free tier initially

### VII. Data & Privacy
- Users own uploaded images and generated maps
- Users can delete their data
- Clear LEGO disclaimer: Not affiliated with or endorsed by LEGO Group
- No third-party data sharing without consent

**Constitution violations MUST be justified** in the implementation plan's "Complexity Tracking" section with simpler alternatives documented.

## Repository Structure

```
cli/                      # Python CLI tools (open-source ready)
├── src/                  # Core logic: image processing, LEGO generation, parts calculation
├── tests/                # Contract, integration, and unit tests
└── pyproject.toml        # Python package configuration

backend/                  # Web API (FastAPI)
├── src/                  # API endpoints, user management, file storage
│   ├── models/           # Database models
│   ├── services/         # Business logic (calls CLI tools)
│   └── api/              # REST endpoints
├── tests/                # Backend tests
└── Dockerfile            # Fly.io deployment

frontend/                 # Web UI
├── src/                  # React/Vue/Svelte components
│   ├── components/       # UI components
│   ├── pages/            # Page views
│   └── services/         # API client
└── tests/                # Frontend tests

specs/                    # Feature specifications (managed by speckit)
├── ###-feature-name/     # Each feature gets a numbered directory
│   ├── spec.md           # User stories, requirements, success criteria
│   ├── plan.md           # Technical design and architecture
│   ├── tasks.md          # Implementation task list
│   ├── research.md       # Technical research and decisions
│   ├── data-model.md     # Data entities and relationships
│   ├── quickstart.md     # Integration scenarios
│   ├── contracts/        # API contracts (OpenAPI/GraphQL schemas)
│   └── checklists/       # Quality validation checklists

docs/                     # User documentation
.specify/                 # Speckit templates and scripts
├── memory/
│   └── constitution.md   # Project principles and governance
├── templates/            # Spec, plan, task, and checklist templates
└── scripts/bash/         # Feature workflow automation scripts
```

## Architecture Principles

### CLI as Foundation
The CLI tools are the **single source of truth** for core functionality:

1. **Satellite image processing**: Convert image → LEGO-compatible color palette
2. **LEGO map generation**: Determine brick placement, colors, and structure
3. **Parts list calculation**: Count required pieces by type and color
4. **Instruction generation**: Create step-by-step assembly guide

The web backend **never reimplements** this logic. It either:
- Calls CLI tools as subprocesses (for isolation)
- Imports CLI as a library (for performance)

### User Story Independence
Each user story must be:
- **Independently implementable**: Can be built without other stories
- **Independently testable**: Has its own acceptance criteria and tests
- **Independently deployable**: Delivers standalone value to users
- **Prioritized**: P1 = MVP, P2/P3 = enhancements

Example user story structure:
```
P1: User uploads satellite image → System generates basic LEGO map
P2: User customizes color palette → System regenerates with custom colors
P3: User downloads building instructions PDF
```

After implementing P1, you have a working MVP. P2 and P3 add value incrementally.

## Common Development Tasks

### Working with Features

**Start a new feature:**
```bash
/speckit.specify "Add satellite image color quantization to LEGO palette"
```

**Check current feature status:**
```bash
git branch --show-current  # Shows: ###-feature-name
```

**View feature documentation:**
```bash
ls specs/$(git branch --show-current)/
# Shows: spec.md, plan.md, tasks.md, etc.
```

### Constitution Compliance

When creating implementation plans, the `/speckit.plan` command automatically includes a "Constitution Check" section. Verify:

- **CLI-first**: Feature works standalone via CLI before web integration
- **Open source ready**: No hardcoded secrets or proprietary endpoints in CLI code
- **Test-first**: Tests written before implementation, with failing state verified
- **Incremental**: User stories can be delivered independently in priority order
- **Performance**: Meets targets (<30s image processing, <2s web response)
- **Deployment**: Follows Fly.io containerization and secrets management
- **Privacy**: User data ownership and deletion capabilities

### Testing Strategy

**Test hierarchy (highest to lowest priority):**
1. **Contract tests**: Validate CLI command interfaces (inputs, outputs, errors)
2. **Integration tests**: End-to-end workflows (image upload → map generation → parts list)
3. **Unit tests**: Critical algorithms (color quantization, brick selection, structural validation)

**Test data requirements:**
- Real satellite imagery samples (various resolutions, color profiles)
- LEGO World Map reference data (official piece catalog, color mappings)
- Expected outputs for regression testing

**TDD workflow:**
```bash
# 1. Write test (it should fail)
# 2. Run test → verify failure
# 3. Implement feature
# 4. Run test → verify pass
# 5. Refactor if needed
# 6. Run test again → verify still passes
```

## Technology Stack

**Current (as of constitution v1.0.0):**
- **CLI**: Python 3.11+, packaged with Poetry or setuptools
- **Backend**: Python (FastAPI or Flask), containerized with Docker
- **Frontend**: Modern framework (React/Vue/Svelte), static build
- **Database**: PostgreSQL (Fly.io Postgres)
- **Storage**: Fly.io volumes or S3-compatible object storage
- **CI/CD**: GitHub Actions (testing, building, Fly.io deployment)

**Key dependencies (CLI):**
- Image processing: Pillow, scikit-image, or similar
- LEGO brick logic: Custom algorithms (to be developed)
- CLI framework: Click or argparse
- Testing: pytest

**Key dependencies (backend):**
- API framework: FastAPI (recommended) or Flask
- Database ORM: SQLAlchemy
- Authentication: OAuth2/JWT
- File uploads: Multipart handling, async processing

## Important Notes

### LEGO Compliance
- This system uses the LEGO World Map kit format as a **reference** for educational/personal use
- Parts lists reference **official LEGO part numbers** for user convenience
- **Always include disclaimer**: "Not affiliated with or endorsed by The LEGO Group"
- Do not claim official LEGO endorsement or partnership
- User-generated content policy to prevent trademark misuse

### Fly.io Deployment Considerations
- **Optimize for free tier** initially (shared CPU, 256MB RAM)
- **Image processing is expensive**: Use async/background jobs (Celery, RQ, or Fly.io Machines)
- **Storage**: Fly.io volumes (persistent) or S3-compatible (Tigris, R2)
- **Secrets**: Use `fly secrets set` - never commit credentials
- **Scaling**: Plan for auto-scaling when user base grows (currently targeting 100 users/month)

### Open Source Readiness Checklist
Before releasing CLI tools as open source:
- [ ] Choose license (MIT or Apache 2.0 recommended)
- [ ] Comprehensive README (installation, usage, examples)
- [ ] CONTRIBUTING.md (development setup, testing, PR guidelines)
- [ ] CODE_OF_CONDUCT.md (community standards)
- [ ] Example satellite images and expected outputs
- [ ] LEGO World Map format specification documented
- [ ] Automated testing and release pipeline (GitHub Actions + PyPI)
- [ ] Zero dependencies on web backend code
- [ ] No hardcoded credentials or proprietary endpoints

## Critical Workflows

### Feature Implementation Flow
```
User describes feature
    ↓
/speckit.specify → spec.md created (user stories, requirements)
    ↓
Review & clarify spec (use /speckit.clarify if needed)
    ↓
/speckit.plan → plan.md, research.md, data-model.md, contracts/ created
    ↓
Review Constitution Check for violations
    ↓
/speckit.tasks → tasks.md created (dependency-ordered, by user story)
    ↓
Review tasks, ensure P1 is complete MVP
    ↓
/speckit.implement → Execute tasks phase-by-phase
    ↓
Test each user story independently
    ↓
Deploy/demo before next priority
```

### When Constitution Check Fails
If your implementation plan violates a principle:

1. **Document the violation** in "Complexity Tracking" section
2. **Explain why it's needed** for the current feature
3. **Document simpler alternatives** and why they were rejected
4. **Get user approval** before proceeding

Example:
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Direct DB access in CLI | Performance for large datasets | Subprocess calls add 500ms overhead per query |

### Handling Checklist Failures
The `/speckit.implement` command checks checklists before starting:

- **If incomplete**: Lists failing items and asks for user approval to proceed
- **If complete**: Automatically starts implementation
- **Manual override**: User can choose to proceed despite incomplete checklists

## Tips for Working in This Codebase

1. **Always start with `/speckit.specify`** - Never create features ad-hoc
2. **Respect the CLI-first principle** - Build CLI tools before web features
3. **Test before implementing** - TDD is non-negotiable for core logic
4. **User stories are sacred** - Each story should be independently deliverable
5. **Constitution violations need justification** - Document in Complexity Tracking
6. **Keep CLI and web backend separate** - CLI should work offline with local files
7. **Prepare for open source** - Write CLI code as if it's already public
8. **Optimize for Fly.io free tier** - Async processing for expensive operations
9. **Include LEGO disclaimer** - Always clarify non-affiliation with LEGO Group
10. **Incremental delivery** - P1 = MVP, deploy/demo before P2/P3

## Getting Help

For questions about:
- **Speckit commands**: Read `.claude/commands/speckit.*.md` files
- **Project principles**: Read `.specify/memory/constitution.md`
- **Feature workflow**: Follow the scripts in `.specify/scripts/bash/`
- **Template structure**: Check `.specify/templates/` for spec, plan, task formats

## Active Technologies
- Python 3.11+ (per constitution requirement for CLI tools) + Pillow (image I/O), NumPy (array operations), scikit-image (color space conversion), Click (CLI framework) (001-image-processing)
- Local filesystem only (input images, output images, LEGO color palette JSON/CSV) (001-image-processing)
- Python 3.11+ (per constitution requirement for CLI tools) + Pillow (image I/O), NumPy (array operations), Click (CLI framework), json (output serialization) (002-lego-map-layout)
- Local filesystem only (input: quantized images; output: JSON/CSV position layouts; reference: LEGO kit config + land/sea mask JSON) (002-lego-map-layout)

## Recent Changes
- 001-image-processing: Added Python 3.11+ (per constitution requirement for CLI tools) + Pillow (image I/O), NumPy (array operations), scikit-image (color space conversion), Click (CLI framework)
