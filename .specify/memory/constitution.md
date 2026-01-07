<!--
  Sync Impact Report
  ==================
  Version change: (initial) → 1.0.0

  Modified principles: N/A (initial creation)

  Added sections:
  - Core Principles (I-VII)
  - Deployment & Infrastructure
  - Open Source Readiness
  - Governance

  Removed sections: N/A

  Templates alignment:
  ✅ plan-template.md - Constitution Check section aligns with all principles
  ✅ spec-template.md - User story prioritization aligns with incremental delivery
  ✅ tasks-template.md - Task organization aligns with CLI-first and test principles

  Follow-up TODOs: None - all fields completed
-->

# 98138.world Constitution

## Core Principles

### I. CLI-First Architecture

Every feature MUST be accessible via command-line interface before web integration. Python CLI tools are the foundation; web UI is a consumer of these tools.

**Rationale**: CLI tools enable testing, automation, debugging, and potential open-source release independent of web infrastructure. This ensures core logic remains portable and framework-agnostic.

**Requirements**:
- All satellite processing, LEGO map generation, and parts list creation MUST work as standalone CLI commands
- CLI tools MUST accept input via stdin/args and output to stdout (JSON and human-readable formats)
- Web backend MUST call CLI tools as subprocess or library; no duplicated logic
- CLI tools MUST be independently testable without web dependencies

### II. Modular & Open Source Ready

CLI tools MUST be designed for potential open-source release with clear separation from proprietary web services.

**Rationale**: Public CLI tools drive adoption and community contribution while protecting proprietary infrastructure and business logic.

**Requirements**:
- CLI code lives in separate package(s) with independent versioning
- No hardcoded credentials, API keys, or proprietary endpoints in CLI code
- Clear LICENSE file and contribution guidelines prepared from start
- Web-specific features (user accounts, payment, hosting) isolated in web backend
- CLI tools MUST work offline or with local file inputs

### III. Incremental Delivery (NON-NEGOTIABLE)

Features MUST be delivered as independently testable, deployable user stories in priority order (P1 → P2 → P3).

**Rationale**: Enables early validation, faster feedback, and minimizes risk. Each story should provide tangible value to users.

**Requirements**:
- P1 user story MUST be a complete, usable MVP
- Each user story MUST be testable without requiring other stories
- Each story MUST include acceptance criteria and independent test validation
- Deploy/demo after each story completion before proceeding to next priority
- TDD approach: Write tests → Verify failure → Implement → Verify pass

### IV. Test-First Development

Tests MUST be written before implementation for all core processing logic (satellite analysis, LEGO generation, parts calculation).

**Rationale**: LEGO maps have precise constraints (brick compatibility, color mapping, structural integrity). Test-first ensures correctness before writing complex image processing and generation logic.

**Requirements**:
- Contract tests for all CLI commands (input/output validation)
- Integration tests for end-to-end workflows (image → LEGO map → parts list)
- Unit tests for critical algorithms (image processing, brick selection, color matching)
- Tests MUST fail before implementation begins
- Test data MUST include real satellite imagery samples and LEGO World Map reference data

### V. Performance & Scale Targets

System MUST handle realistic workloads for hobbyist and professional users.

**Performance Goals**:
- CLI: Process standard satellite image (1024x1024) → LEGO map in < 30 seconds
- Web API: Support 100 concurrent users without degradation
- File storage: Handle images up to 10MB, output files up to 5MB
- Response time: Web UI interactions < 2 seconds p95

**Scale Targets**:
- Initial launch: 100 users/month
- Year 1 growth: 1,000 users/month
- Storage: ~100GB for user-generated maps (estimated)

### VI. Deployment & Infrastructure Standards

**Platform**: Fly.io with custom domain (98138.world)

**Requirements**:
- Backend MUST be containerized (Docker) for Fly.io deployment
- Frontend MUST be static-deployable (CDN-ready)
- Environment-based configuration (local/staging/production)
- Secrets management via Fly.io secrets (never in code/git)
- Zero-downtime deployments via Fly.io blue-green or rolling strategy
- Monitoring MUST include error tracking, performance metrics, and user analytics

**Cost Constraints**:
- Optimize for Fly.io free tier initially
- Plan for auto-scaling when user base grows
- Image processing MUST be async/background for expensive operations

### VII. Data & Privacy

**User Data**:
- Uploaded satellite images MUST be stored securely with user ownership
- Users MUST be able to delete their data
- Generated LEGO maps and parts lists belong to the user
- No third-party data sharing without explicit consent

**LEGO Compliance**:
- System uses LEGO World Map kit format as reference (educational/personal use)
- Parts lists reference official LEGO part numbers for user convenience
- Clear disclaimer: Not affiliated with or endorsed by LEGO Group
- User-generated content policy to prevent misuse

## Deployment & Infrastructure

**Technology Stack**:
- **CLI Tools**: Python 3.11+, packaged with Poetry or setuptools
- **Backend**: Python (FastAPI or Flask), containerized
- **Frontend**: Modern framework (React/Vue/Svelte), static build
- **Database**: PostgreSQL (Fly.io Postgres) for user data, maps, parts lists
- **Storage**: Fly.io volumes or S3-compatible for images and generated files
- **CI/CD**: GitHub Actions for testing, building, deploying to Fly.io

**Repository Structure**:
```
cli/                  # Python CLI tools (open-source ready)
├── src/
├── tests/
└── pyproject.toml

backend/              # Web API (FastAPI)
├── src/
├── tests/
└── Dockerfile

frontend/             # Web UI
├── src/
├── tests/
└── Dockerfile or static build

specs/                # Feature specs managed by speckit
docs/                 # User documentation
.specify/             # Speckit configuration
```

## Open Source Readiness

**CLI Package Preparation**:
- [ ] Choose license (MIT or Apache 2.0 recommended for broad adoption)
- [ ] Write comprehensive README with installation, usage, examples
- [ ] Create CONTRIBUTING.md with development setup, testing, PR guidelines
- [ ] Add CODE_OF_CONDUCT.md for community standards
- [ ] Prepare example satellite images and expected outputs for testing
- [ ] Document LEGO World Map format specification (reverse-engineered or reference)
- [ ] Set up automated testing and release pipeline (GitHub Actions + PyPI)

**Separation Checklist**:
- [ ] CLI has zero dependencies on web backend code
- [ ] All web-specific logic (auth, billing, hosting) in `backend/` only
- [ ] CLI configuration via files or env vars (no hardcoded web URLs)
- [ ] Shared data models (if any) in separate package or copied

## Governance

**Constitution Authority**: This constitution supersedes all conflicting practices. Changes require documented rationale and version increment.

**Compliance**:
- All feature specs MUST be reviewed against these principles
- Implementation plans MUST include "Constitution Check" section
- Violations MUST be justified in "Complexity Tracking" with simpler alternatives documented
- Code reviews MUST verify principle adherence

**Amendment Process**:
1. Propose change with rationale (why current principle is blocking progress)
2. Document impact on existing code and features
3. Update version (MAJOR for breaking changes, MINOR for additions, PATCH for clarifications)
4. Propagate changes to all templates and documentation
5. Notify all contributors of changes

**Version Control**:
- MAJOR: Principle removed or fundamentally changed (e.g., removing CLI-first requirement)
- MINOR: New principle added or significant expansion (e.g., adding security principle)
- PATCH: Clarifications, typos, non-semantic refinements

**Quality Gates**:
- Pre-commit: Linting, formatting, type checks pass
- PR merge: All tests pass, code review approved, constitution compliance verified
- Deployment: Integration tests pass, performance benchmarks met

**Runtime Guidance**: For implementation-specific guidance, refer to `.specify/templates/` and individual feature `plan.md` files.

**Version**: 1.0.0 | **Ratified**: 2026-01-04 | **Last Amended**: 2026-01-04
