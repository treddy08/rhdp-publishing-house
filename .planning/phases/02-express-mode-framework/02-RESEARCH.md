# Phase 2: Express Mode Framework - Research

**Researched:** 2026-05-04
**Domain:** Orchestrator evolution, session continuity (MCP tool design + DB schema), intake routing
**Confidence:** HIGH

## Summary

Phase 2 was dramatically restructured during the discuss-phase. The original spec assumed express projects as durable portal objects with lifecycle management, kanban views, and artifact storage. The user decided express is throwaway -- PH helps build the environment and walks away. The only persisted express data is lightweight aggregate metrics (run counts, automation vs. manual breakdown). RCARS learning data is backlogged entirely.

What remains is the critical infrastructure work that benefits ALL modes and enables the Phase 4 chatbot: (1) orchestrator evolution from "find a manifest" to "find state wherever it lives" via portal MCP queries, (2) session continuity so intake data persists in the portal DB and survives Claude Code restarts, (3) manifest-to-portal sync on every write, and (4) express intake routing as a lightweight third option that dead-ends at the environment gate.

**Primary recommendation:** Build the session continuity MCP tools and DB schema first (portal repo), then evolve the orchestrator and intake skills (skills-plugin repo) to use them. Express intake routing folds into the intake skill update as a third branch with minimal additional code. The portal DB schema should mirror the manifest YAML shape using JSONB, not normalized columns, to keep the contract simple and avoid schema drift.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Express projects are NOT tracked as "projects" in the portal. They are transient workflows -- PH helps build the environment and walks away. No lifecycle tracking, no kanban presence, no portal detail views.
- **D-02:** Express metrics are tracked -- count of express runs, how many were fully automated (post-Babylon) vs. had manual steps. Lightweight aggregate data only.
- **D-03:** RCARS learning data (storing selected base CI + customization steps from express runs to improve future runs) is backlogged. Needs careful design to avoid polluting content search results. Added to both PH and RCARS backlogs.
- **D-04:** Express intake data lives in portal DB only (no local file, no git repo). The express skill reads it from the portal when it eventually runs.
- **D-05:** Local manifest first, portal on demand. If a manifest exists locally, use it. If not found, query portal via MCP automatically. User can explicitly request portal project list anytime. Include a hint: "If you don't see your project here, ask for a list from the portal."
- **D-06:** When MCP is unavailable (no API key, server down), warn the user and block portal-dependent features. List what's unavailable (session continuity, express mode, portal project discovery). Proceed with local-only mode.
- **D-07:** User identification: check for a configured email first (PH config file or environment variable). If not found, prompt on first portal query and cache locally. One-time setup, then automatic.
- **D-08:** Portal DB mirrors manifest schema -- same core project data shape. Portal can augment with portal-specific fields (UI state, express session data), but core project data is identical. Either source (manifest or portal DB) can bootstrap the other.
- **D-09:** Portal DB updated on every manifest write. Every time a skill updates the manifest, it also pushes to the portal via MCP. Real-time sync, not batched.
- **D-10:** This session continuity layer is the critical foundation for the Phase 4 chatbot. The chatbot is just another client of the same portal state -- different frontend, same backend data.
- **D-11:** Intake presents three deployment modes after vetting (onboarded, self-published, express). User selects. PH never steers toward a mode.
- **D-12:** Express intake runs a second RCARS base-finding query (broader, infrastructure-focused). Quality is limited until RCARS gets infrastructure-aware catalog metadata -- currently relies on content analysis as a proxy.
- **D-13:** Express flow dead-ends at the environment gate for now ("order this Babylon environment, come back when it's ready"). No express skill to continue with until that's built separately.
- **D-14:** Same patterns as Phase 1: `gsd-project` branch for PH repos, submodule awareness for `skills-plugin`, docs centralize in `rhdp-publishing-house` under `docs/`.

### Claude's Discretion
- Portal DB schema details for manifest mirroring (which fields, JSONB vs. normalized columns)
- MCP tool contracts for session continuity (`ph_store_intake_results`, `ph_get_intake_results` -- may need redesign given the manifest-mirror approach)
- Express metrics storage mechanism (DB table, counter, or metrics endpoint)
- User email caching format and location (dotfile, config file, etc.)
- How manifest-to-portal sync handles conflicts or stale data

### Deferred Ideas (OUT OF SCOPE)
- RCARS express learning data -- store base CI + customization steps for future run improvement. Added to PH and RCARS backlogs. Needs design to avoid polluting content search.
- Express portal UI (kanban, detail views, artifact viewer) -- removed from Phase 2. May revisit if express usage patterns warrant it.
- Express project lifecycle tracking -- removed. Express is throwaway.
- Babylon ordering automation -- manual gate works for now.
- Portal user identity model (email to GitHub mapping) -- separate workstream, not blocking this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

**CRITICAL: Requirements EXPRESS-10, EXPRESS-11, EXPRESS-12 conflict with locked decision D-01.** The CONTEXT.md explicitly removes express kanban presence, portal detail views, and artifact viewers. These requirements should be marked as descoped/deferred during planning -- they were written before the discuss-phase restructured the scope.

| ID | Description | Research Support | Scope Status |
|----|-------------|------------------|--------------|
| EXPRESS-01 | Separate `ExpressProject` database model | Descoped per D-01. Express is not tracked as a project. Replace with lightweight `ExpressMetric` counter table and `IntakeSession` table for session continuity. | RESTRUCTURED |
| EXPRESS-02 | `ExpressArtifact` model for artifacts | Descoped per D-01. Express artifacts are not stored in portal. Express produces a recap in the user's terminal and that is the end. | DESCOPED |
| EXPRESS-03 | `ph_create_express_project` MCP tool | Descoped per D-01. Replace with `ph_store_intake_results` for session continuity and `ph_record_express_run` for metrics. | RESTRUCTURED |
| EXPRESS-04 | `ph_update_express_status` MCP tool | Descoped per D-01. No status tracking for express. | DESCOPED |
| EXPRESS-05 | `ph_store_express_artifact` MCP tool | Descoped per D-01. No artifact storage for express. | DESCOPED |
| EXPRESS-06 | `ph_get_express_project` MCP tool | Descoped per D-01. No express project retrieval. | DESCOPED |
| EXPRESS-07 | `ph_store_intake_results` and `ph_get_intake_results` for session continuity | Core deliverable. Session continuity for ALL modes (onboarded, self-published, express). This is the critical foundation. | IN SCOPE |
| EXPRESS-08 | Orchestrator checks local manifest first, then portal via MCP, then new intake | Core deliverable. Orchestrator evolution per D-05. | IN SCOPE |
| EXPRESS-09 | Intake skill routes to express flow with RCARS vetting and base-finding | In scope. Third mode option in intake per D-11, D-12, D-13. Dead-ends at environment gate. | IN SCOPE |
| EXPRESS-10 | Portal kanban shows express projects | Descoped per D-01. Express has no portal presence. | DESCOPED |
| EXPRESS-11 | Portal express project detail view | Descoped per D-01. No express detail views. | DESCOPED |
| EXPRESS-12 | Artifact viewer for recap and intake design | Descoped per D-01. No express artifacts in portal. | DESCOPED |

**Replacement deliverables (from scope restructuring):**
- **NEW-01:** `IntakeSession` DB model -- stores intake data for session continuity across all modes
- **NEW-02:** `ExpressMetric` DB model -- lightweight counters for express run tracking (D-02)
- **NEW-03:** `ph_sync_manifest` MCP tool -- pushes manifest data to portal on every write (D-09)
- **NEW-04:** `ph_list_user_projects` MCP tool or filter parameter on `ph_list_projects` -- finds projects by user email (D-05, D-07)
- **NEW-05:** User email identification and caching mechanism (D-07)
- **NEW-06:** Orchestrator SKILL.md rewrite for MCP-aware startup flow (D-05, D-06)
- **NEW-07:** Intake SKILL.md update for three-mode routing (D-11, D-12, D-13)
- **NEW-08:** Manifest sync hook documentation for all skills that write manifests (D-09)
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Manifest storage (source of truth) | Local filesystem (git repo) | Portal DB (mirror) | Manifest YAML in git is the canonical source for onboarded/self-published modes. Portal mirrors for cross-session discovery. |
| Session continuity data | Portal DB (API tier) | -- | Portal DB is the durable store that survives CC restarts. MCP tools provide the access layer. |
| Express intake data | Portal DB (API tier) | -- | Express has no git repo (D-04). Portal DB is the only store. |
| User identification | Claude Code client | Portal DB (API tier) | CC reads email from local config/env, sends to portal MCP for project filtering. |
| Orchestrator startup logic | Claude Code client (skill) | -- | Skill reads local manifest, falls back to MCP query. Decision logic is client-side. |
| Intake routing (3 modes) | Claude Code client (skill) | -- | Intake skill presents options and routes. Server stores results. |
| Express metrics | Portal DB (API tier) | -- | Aggregate counters stored in DB. No client-side metrics. |
| Manifest-to-portal sync | Claude Code client (skill) | Portal DB (API tier) | Skills trigger sync after every manifest write. Portal MCP tool receives and stores. |

## Standard Stack

### Core (No New Dependencies)

This phase adds NO new packages. All work uses the existing stack from Phase 1.

| Library | Version | Purpose | Verified |
|---------|---------|---------|----------|
| FastMCP | 3.2.4 | MCP server framework -- new tools register with existing `@mcp.tool()` pattern | [VERIFIED: pip show in portal venv] |
| SQLAlchemy | 2.0.49 | ORM for new DB models -- follows existing `mapped_column` pattern | [VERIFIED: pip show in portal venv] |
| Alembic | >=1.13 | DB migrations for new tables -- follows existing migration pattern | [VERIFIED: requirements.txt, 2 existing migrations] |
| Pydantic | 2.13.3 | Schemas for new API endpoints and MCP tool responses | [VERIFIED: pip show in portal venv] |
| httpx | 0.28.1 | Already in deps -- no additional HTTP clients needed this phase | [VERIFIED: pip show in portal venv] |
| PostgreSQL | 16 | Database -- new tables added alongside existing schema | [CITED: CLAUDE.md Full Stack Summary] |

### Frontend (No Changes This Phase)

No frontend work is needed. The CONTEXT.md descoped all portal express UI (D-01). The existing kanban/project views are unchanged. Session continuity and express metrics are backend-only -- the Phase 4 chatbot will be the first new consumer of this data.

## Architecture Patterns

### System Architecture Diagram

```
Claude Code User
    |
    |--- 1. Check local: read publishing-house/manifest.yaml
    |       |
    |       +-- Found? --> Use it (existing flow, unchanged)
    |       |
    |       +-- Not found?
    |               |
    |--- 2. Check portal via MCP: ph_list_projects(owner_email=...)
    |       |
    |       +-- Found projects? --> Present list, user picks
    |       |
    |       +-- No projects? --> Start new intake
    |               |
    |--- 3. Intake flow:
    |       |
    |       +-- Conversational intake (unchanged)
    |       +-- RCARS vetting (unchanged, uses ph_rcars_query)
    |       +-- Mode selection: onboarded | self-published | express
    |               |                               |
    |               |                               +-- Express: second RCARS query (base-finding)
    |               |                               +-- Express: store intake in portal DB only
    |               |                               +-- Express: dead-end at environment gate
    |               |
    |               +-- Onboarded/Self-pub: store intake in portal DB
    |               +-- User creates/clones repo
    |               +-- Orchestrator finds intake data in portal, writes manifest
    |
    |--- 4. Every manifest write:
            |
            +-- Skill updates local manifest.yaml
            +-- Skill calls ph_sync_manifest(project_id, manifest_data)
            +-- Portal DB updated in real-time

Portal Backend (FastAPI + FastMCP)
    |
    +-- MCP Tools (new):
    |       ph_store_intake_results(owner_email, mode, intake_data) --> IntakeSession table
    |       ph_get_intake_results(session_id) --> IntakeSession table
    |       ph_sync_manifest(project_id, manifest_yaml) --> Manifest table (existing)
    |       ph_list_projects(owner_email) --> Project table (existing, add filter)
    |       ph_record_express_run(owner_email, base_ci, automated) --> ExpressMetric table
    |
    +-- DB Models (new):
    |       IntakeSession -- stores intake data for session continuity
    |       ExpressMetric -- lightweight counters for express runs
    |
    +-- DB Models (modified):
            Project -- add owner_email column
```

### Recommended Project Structure (Portal Backend Changes)

```
src/backend/
├── app/
│   ├── models/
│   │   ├── __init__.py          # Add IntakeSession, ExpressMetric imports
│   │   ├── intake_session.py    # NEW: IntakeSession model
│   │   ├── express_metric.py    # NEW: ExpressMetric model
│   │   ├── project.py           # MODIFY: add owner_email column
│   │   └── ...                  # Existing models unchanged
│   ├── mcp/
│   │   ├── session_tools.py     # NEW: session continuity MCP tools
│   │   ├── tools.py             # MODIFY: add owner_email filter to ph_list_projects
│   │   └── ...                  # Existing tools unchanged
│   ├── schemas/
│   │   ├── intake_session.py    # NEW: Pydantic schemas
│   │   └── ...
│   └── core/
│       └── types.py             # NEW: shared JSONBType (DRY refactor)
├── alembic/
│   └── versions/
│       └── xxxx_add_intake_session_express_metric.py  # NEW migration
└── tests/
    ├── test_session_tools.py    # NEW: session continuity MCP tool tests
    └── ...
```

### Recommended Project Structure (Skills Plugin Changes)

```
skills-plugin/
├── skills/
│   ├── orchestrator/
│   │   └── SKILL.md             # REWRITE: MCP-aware startup flow (D-05, D-06)
│   └── intake/
│       └── SKILL.md             # MODIFY: three-mode routing (D-11, D-12, D-13)
```

### Pattern 1: Session Continuity MCP Tools

**What:** MCP tools that store and retrieve intake session data in the portal DB, enabling state to survive Claude Code restarts.

**When to use:** Every time the intake skill completes an intake interview or a user resumes a project from a different machine/session.

**Example:**

```python
# Source: Existing pattern in app/mcp/tools.py + D-08 manifest-mirror approach
@mcp.tool()
def ph_store_intake_results(
    owner_email: str,
    mode: str,
    intake_data: dict,
    project_name: str | None = None,
) -> dict:
    """Store intake interview results in the portal DB for session continuity.

    Args:
        owner_email: Red Hat email of the project owner.
        mode: Deployment mode ('onboarded', 'self_published', 'express').
        intake_data: Full intake data dict (mirrors manifest project + lifecycle shape).
        project_name: Optional project name for display.
    """
    db = SessionLocal()
    try:
        session = IntakeSession(
            owner_email=owner_email,
            mode=mode,
            project_name=project_name,
            intake_data=intake_data,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return {
            "session_id": str(session.id),
            "owner_email": session.owner_email,
            "mode": session.mode,
            "created_at": session.created_at.isoformat(),
        }
    finally:
        db.close()
```

[VERIFIED: Pattern matches existing `ph_store_validation_results` in `tools.py` lines 84-130]

### Pattern 2: Manifest Sync on Every Write

**What:** A hook pattern where skills push manifest data to the portal DB after every local manifest write.

**When to use:** D-09 requires real-time sync on every manifest write.

**Implementation approach:** The sync is NOT a Python function hook in the skill code (skills are SKILL.md files, not Python modules). Instead, the orchestrator and intake skill instructions in SKILL.md tell the agent to call the `ph_sync_manifest` MCP tool after every manifest update. This is a behavioral instruction, not a code hook.

**Example SKILL.md instruction:**

```markdown
## Manifest Sync Rule

After every manifest write (updating `publishing-house/manifest.yaml`), immediately
call the `ph_sync_manifest` MCP tool with the full manifest content:

1. Read the updated manifest.yaml
2. Call `ph_sync_manifest(project_id, manifest_yaml)` with the YAML content
3. If the MCP call fails, warn the user but do not block workflow

This ensures the portal DB stays in sync for session continuity.
If MCP is unavailable, this step is skipped (local-only mode per D-06).
```

### Pattern 3: Orchestrator MCP-Aware Startup

**What:** The orchestrator checks local manifest first, then queries portal via MCP if not found.

**When to use:** Every orchestrator session start (Step 1 of SKILL.md).

**Key behavior changes from current orchestrator:**
1. Current: Only checks local filesystem (CWD and subdirectories)
2. New: After local check fails, queries portal via `ph_list_projects` filtered by user email
3. New: If MCP unavailable, warns user and proceeds local-only (D-06)
4. New: Adds express mode project discovery from portal (though express projects have no local state)

### Pattern 4: Express Intake Dead-End

**What:** When user selects express mode during intake, a second RCARS query finds base infrastructure, intake data is stored in portal DB only, and the flow dead-ends at the environment gate.

**When to use:** D-13 -- express flow stops after base CI identification.

**Key constraint:** No local files are written for express. No manifest.yaml, no git repo. Everything goes to portal DB via MCP (D-04).

### Anti-Patterns to Avoid

- **Normalized express project table:** D-01 explicitly says no express project tracking. Do not create an `ExpressProject` model with lifecycle fields. Use a flat `IntakeSession` for session continuity and a counter `ExpressMetric` for metrics.
- **Polling or batch sync:** D-09 requires real-time sync on every manifest write. Do not batch or defer portal updates.
- **MCP-first startup:** D-05 says local manifest first, portal on demand. Do not query the portal if a local manifest is found.
- **Duplicating JSONBType:** The codebase already has `JSONBType` copied in 3 model files. Extract to a shared location (`app/core/types.py`) rather than adding a 4th copy. [VERIFIED: grep found `class JSONBType` in manifest.py, phase.py, validation.py]
- **OAuth or complex auth for user identification:** D-07 is email in config/env, one-time prompt, local cache. No SSO, no portal login.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB migrations | Manual SQL ALTER TABLE | Alembic `alembic revision --autogenerate` | Existing Alembic setup with 2 migrations. Autogenerate detects new models. [VERIFIED: alembic/env.py imports all models] |
| JSONB storage | Custom JSON serialization | SQLAlchemy JSONBType (existing pattern) | Already works across PostgreSQL (prod) and SQLite (tests). [VERIFIED: models/manifest.py] |
| MCP tool registration | Manual endpoint wiring | `@mcp.tool()` decorator on the shared `mcp` instance | Existing pattern in tools.py and rcars_tools.py. [VERIFIED: app/mcp/server.py] |
| API key auth on new tools | Separate auth layer | Existing `ApiKeyAuth` middleware applies to ALL tools | Middleware intercepts every `on_call_tool` call. [VERIFIED: app/mcp/auth.py] |
| Test DB setup | Manual test DB config | Existing `conftest.py` with SQLite test DB | Auto-creates and drops tables per test. [VERIFIED: tests/conftest.py] |

**Key insight:** This phase adds new MCP tools and DB models using well-established patterns already in the codebase. No new frameworks, no new deployment patterns, no new auth mechanisms. The complexity is in the skill-level behavior changes (orchestrator startup, intake routing), not in the backend code.

## Common Pitfalls

### Pitfall 1: Circular Sync Loop
**What goes wrong:** Manifest sync pushes to portal, portal updates trigger a refresh, refresh pulls back the same data, triggers another sync.
**Why it happens:** The existing portal has a `refresh_all_projects` scheduler that fetches manifests from GitHub every 30 minutes. If the sync-via-MCP updates the same `Manifest` record, the refresh job could overwrite it.
**How to avoid:** The `ph_sync_manifest` MCP tool should update the existing `Manifest.parsed_data` and `Manifest.raw_yaml` fields directly. The GitHub refresh job should check `Manifest.fetched_at` -- if the manifest was updated via MCP more recently than the last GitHub fetch, skip the GitHub fetch for that project. OR: make MCP-synced manifests the authoritative source and only refresh from GitHub on explicit user request.
**Warning signs:** Portal DB manifest data oscillates between two versions (MCP-pushed vs. GitHub-fetched).

### Pitfall 2: IntakeSession Orphans
**What goes wrong:** Intake sessions are created in portal DB but never converted to projects (user abandons after intake).
**Why it happens:** Express sessions are fire-and-forget (D-01). Onboarded/self-published sessions may never get a repo created.
**How to avoid:** Add a `status` field to `IntakeSession` (active/converted/abandoned). Consider a cleanup job that marks sessions older than 30 days as abandoned. Do not auto-delete -- the data may be useful for metrics.
**Warning signs:** Growing number of unclaimed intake sessions in DB.

### Pitfall 3: MCP Tool Availability Assumption
**What goes wrong:** Skills assume MCP tools are always available and crash or hang when they are not.
**Why it happens:** D-06 requires graceful degradation, but skill authors may not implement the fallback path.
**How to avoid:** The orchestrator SKILL.md must explicitly check MCP availability before using portal-dependent features. The check is: "try to call `ph_list_projects`; if it fails or the tool is not found, warn user and set local-only mode." Express intake must refuse to proceed without MCP (D-04 -- express data lives in portal DB only).
**Warning signs:** "Tool not found" errors in Claude Code when MCP server is not configured.

### Pitfall 4: owner_email Column Migration on Existing Data
**What goes wrong:** Adding `owner_email` to the `Project` model fails or leaves existing projects with null emails.
**Why it happens:** Existing projects were registered via GitHub URL -- they have `owner_github` but no email.
**How to avoid:** Make `owner_email` nullable. The `ph_list_projects` filter should handle null gracefully (return projects where `owner_email` matches OR where `owner_github` matches the user's GitHub username). Backfilling is a separate concern (portal user identity model is deferred).
**Warning signs:** `ph_list_projects(owner_email=...)` returns empty results even though the user has registered projects.

### Pitfall 5: Manifest Schema Drift
**What goes wrong:** The portal DB `parsed_data` JSONB field and the local `manifest.yaml` diverge in schema over time.
**Why it happens:** D-08 says "same core data shape" but JSONB is schema-less. Skills may add manifest fields that the portal does not expect, or vice versa.
**How to avoid:** The sync tool (`ph_sync_manifest`) should store the full YAML as-is in both `raw_yaml` and `parsed_data` (parse it server-side). Do not selectively extract fields -- store the entire manifest. This makes the portal a faithful mirror.
**Warning signs:** Portal project detail page shows stale or incomplete data compared to local manifest.

### Pitfall 6: Express Mode Blocking Without Clear User Guidance
**What goes wrong:** User selects express mode but MCP is unavailable, and the skill silently fails or gives a confusing error.
**Why it happens:** Express requires MCP (D-04, D-06) but the intake skill may not check until deep in the flow.
**How to avoid:** Check MCP availability BEFORE presenting the three-mode selection. If MCP is unavailable, present only two modes (onboarded, self-published) and explain why express is disabled.
**Warning signs:** User selects express, gets partway through intake, then hits a wall.

## Code Examples

### IntakeSession DB Model

```python
# Source: Following existing model pattern in app/models/project.py
# with JSONBType from app/models/manifest.py

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.types import JSONBType  # Shared, extracted from duplicated copies


class IntakeSession(Base):
    __tablename__ = "intake_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
        # 'onboarded', 'self_published', 'express'
    project_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
        # 'active', 'converted', 'abandoned'
    intake_data: Mapped[dict] = mapped_column(JSONBType, nullable=False)
        # Full intake results -- mirrors manifest project + lifecycle.phases.intake shape
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
        # FK to projects.id once converted (nullable until user creates repo/project)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

[VERIFIED: Pattern follows existing Project model in app/models/project.py]

### ExpressMetric DB Model

```python
# Source: Lightweight counter per D-02

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ExpressMetric(Base):
    __tablename__ = "express_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    base_ci: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    automated: Mapped[bool] = mapped_column(Boolean, default=False)
        # False until Babylon automation is built
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

[VERIFIED: Pattern follows existing ValidationRun model]

### Modified ph_list_projects with Email Filter

```python
# Source: Existing ph_list_projects in app/mcp/tools.py, adding owner_email filter

@mcp.tool()
def ph_list_projects(owner_email: str | None = None) -> list[dict]:
    """List Publishing House projects, optionally filtered by owner email.

    Args:
        owner_email: Optional Red Hat email to filter projects by owner.
    """
    db = SessionLocal()
    try:
        query = db.query(Project).order_by(Project.name)
        if owner_email:
            query = query.filter(Project.owner_email == owner_email)
        projects = query.all()
        # ... rest unchanged
    finally:
        db.close()
```

[VERIFIED: Extends existing implementation in tools.py lines 20-54]

### User Email Caching (Skill-Level)

```markdown
## User Email Identification (D-07)

Check for user email in this order:
1. Environment variable: `PH_USER_EMAIL`
2. PH config file: `~/.config/rhdp-publishing-house/config.yaml` -> `user.email`
3. Git config: `git config user.email` (fallback, may be personal not Red Hat)

If none found:
- Ask: "What's your Red Hat email? (used for project ownership, one-time setup)"
- Cache to `~/.config/rhdp-publishing-house/config.yaml`
- Never ask again

Config file format:
```yaml
user:
  email: "nstephan@redhat.com"
```
```

[ASSUMED: Config file path and format are recommendations. User may prefer a different location.]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manifest-only state | Manifest + portal DB mirror | This phase | Enables session continuity and chatbot |
| Find project in CWD only | CWD -> portal MCP -> new intake | This phase | Users no longer need to be in repo directory |
| Two deployment modes | Three deployment modes (+ express) | This phase | Express mode accessible via intake |
| GitHub refresh as only portal data source | MCP sync + GitHub refresh | This phase | Real-time portal updates vs. 30-min polling |

**Deprecated/outdated:**
- The `curl` call to RCARS `/recommend` was already fixed in Phase 1 (RCARS-05). Express base-finding uses the same `ph_rcars_query` tool.
- `KeycloakTokenVerifier` was removed in Phase 1. API key auth via FastMCP Middleware is the current pattern.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | User email config file at `~/.config/rhdp-publishing-house/config.yaml` | Code Examples - User Email Caching | Low -- location is Claude's discretion per CONTEXT.md. User can override. |
| A2 | Express metric records one row per express run (not aggregated counters) | Code Examples - ExpressMetric | Low -- aggregate queries can always be computed from individual records. More flexible than pre-aggregated counters. |
| A3 | `IntakeSession.intake_data` stores the full manifest-shaped dict | Architecture Patterns | Medium -- if the manifest shape is too large for JSONB or if specific fields need indexing, a hybrid approach may be needed. Current manifests are ~100 lines of YAML which serialize to small JSON dicts. |
| A4 | The GitHub refresh job should defer to MCP-synced data when MCP sync is more recent | Pitfalls - Circular Sync Loop | Medium -- requires modifying the existing `refresh_project_service` logic to check sync timestamps. Alternative: separate the MCP-synced manifest from the GitHub-fetched manifest. |

## Open Questions (RESOLVED)

1. **How should `ph_sync_manifest` interact with the existing GitHub refresh job?** (RESOLVED)
   - What we know: The portal refreshes manifests from GitHub every 30 minutes (`refresh_interval_minutes`). Phase 2 adds MCP-based sync on every manifest write.
   - Resolution: Add a `sync_source` column to the Manifest model ('github' or 'mcp'). The refresh job checks: if `sync_source == 'mcp'` and `fetched_at` is within the last refresh interval, skip GitHub fetch. This prevents overwriting fresher MCP data with stale GitHub data. Adopted in Plan 02-01 (migration) and Plan 02-02 (ph_sync_manifest sets sync_source='mcp').

2. **Should `ph_sync_manifest` create the project record if it does not exist?** (RESOLVED)
   - What we know: Currently, projects are created via the REST API (`POST /api/v1/projects`) which requires a GitHub repo URL. But session continuity means intake data should land in the portal BEFORE the repo exists.
   - Resolution: Keep them separate. `ph_store_intake_results` creates an `IntakeSession` (pre-project). `ph_sync_manifest` updates an existing `Project`'s manifest. Project creation (linking an `IntakeSession` to a new `Project`) happens when the user creates their repo and the orchestrator finds the intake data. Adopted in Plan 02-02 (separate tools).

3. **How does the orchestrator link a new repo to a previously stored intake session?** (RESOLVED)
   - What we know: User does intake (session stored in portal DB), creates repo, opens it in Claude Code, runs orchestrator.
   - Resolution: The orchestrator queries `ph_get_intake_results(owner_email=...)` to find active sessions. If exactly one is found, use it. If multiple, present a list. The user confirms. Then the orchestrator writes the manifest locally and calls `ph_sync_manifest` to link the project. Adopted in Plan 02-03 (orchestrator startup flow section C).

## Environment Availability

Step 2.6: SKIPPED (no external dependencies). This phase uses only the existing portal backend stack (Python, PostgreSQL, Alembic, FastMCP) which were verified available during Phase 1 execution.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio |
| Config file | `src/backend/pyproject.toml` |
| Quick run command | `cd rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd rhdp-publishing-house-portal/src/backend && python -m pytest tests/ -v --tb=short` |

[VERIFIED: pyproject.toml has `[tool.pytest.ini_options]` with `testpaths = ["tests"]`]

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPRESS-07 | Store and retrieve intake results via MCP tools | unit | `pytest tests/test_session_tools.py -x` | Wave 0 |
| EXPRESS-08 | Orchestrator startup: local manifest -> portal MCP -> new intake | manual-only | N/A (skill behavior, not code) | N/A |
| EXPRESS-09 | Intake routes to express mode with RCARS base-finding | manual-only | N/A (skill behavior, not code) | N/A |
| NEW-01 | IntakeSession model CRUD operations | unit | `pytest tests/test_intake_session_model.py -x` | Wave 0 |
| NEW-02 | ExpressMetric model and recording | unit | `pytest tests/test_express_metric.py -x` | Wave 0 |
| NEW-03 | ph_sync_manifest stores manifest data in portal DB | unit | `pytest tests/test_session_tools.py::test_sync_manifest -x` | Wave 0 |
| NEW-04 | ph_list_projects filters by owner_email | unit | `pytest tests/test_api_projects.py::test_list_projects_by_email -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (quick run, stop on first failure)
- **Per wave merge:** `pytest tests/ -v --tb=short` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_session_tools.py` -- covers EXPRESS-07, NEW-03
- [ ] `tests/test_intake_session_model.py` -- covers NEW-01 (IntakeSession CRUD)
- [ ] `tests/test_express_metric.py` -- covers NEW-02 (ExpressMetric recording)
- [ ] Update `tests/conftest.py` -- add IntakeSession and ExpressMetric to model imports for test DB creation
- [ ] Update `alembic/env.py` -- add new model imports for migration autogeneration

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing API key auth via FastMCP Middleware -- no changes needed. New MCP tools are protected by the same `ApiKeyAuth.on_call_tool` middleware. |
| V3 Session Management | no | MCP is stateless request/response. No server-side sessions. |
| V4 Access Control | yes | `ph_list_projects(owner_email)` filters by email -- ensures users only see their own projects. BUT: no server-side enforcement that the caller's email matches the API key holder. This is acceptable for Phase 2 (internal team, <20 users, API keys are per-person) but should be revisited if user base grows. |
| V5 Input Validation | yes | Pydantic schemas validate all MCP tool inputs. `owner_email` validated as non-empty string. `mode` validated as enum. `intake_data` validated as dict. |
| V6 Cryptography | no | No new crypto. API keys use existing SHA-256 pattern. |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| User A queries projects belonging to User B | Information Disclosure | `owner_email` filter on `ph_list_projects`. Currently honor-system (caller provides their own email). Acceptable for internal team. |
| Malicious intake_data JSONB payload | Tampering | Pydantic validation on MCP tool input. JSONB stored as-is -- no SQL injection risk (parameterized via SQLAlchemy). Size limit via FastAPI request body limit. |
| MCP tool called without auth | Elevation of Privilege | `ApiKeyAuth` middleware blocks unauthenticated calls with ToolError. [VERIFIED: auth.py on_call_tool] |

## Project Constraints (from CLAUDE.md)

- **Multi-repo:** Changes span `rhdp-publishing-house-portal` (backend: models, MCP tools, migrations) and `rhdp-publishing-house` (skills-plugin submodule: orchestrator, intake SKILL.md). Docs centralize in `rhdp-publishing-house` under `docs/`.
- **Auth model:** API key auth for external MCP access. New tools inherit existing auth automatically.
- **Ansible deployers:** All infrastructure changes go through Ansible. Phase 2 has no infrastructure changes (no new Routes, no new Secrets) -- only code and DB migration changes.
- **Dependency chain:** RCARS integration (Phase 1) is complete. Express mode uses the same `ph_rcars_query` tool.
- **FastMCP version:** >=3.2.0 (3.2.4 installed). Middleware pattern established in Phase 1.
- **httpx version:** >=0.28.0 (0.28.1 installed). No additional HTTP clients needed.
- **Sensitive data policy:** Do not write credentials, API keys, or environment-specific URLs into committed files. User email is not a secret but should be in a gitignored config file, not in the manifest.

## Sources

### Primary (HIGH confidence)
- Portal backend codebase (`rhdp-publishing-house-portal/src/backend/`) -- all model, tool, config, and test patterns verified by reading source files
- Skills plugin codebase (`skills-plugin/skills/orchestrator/SKILL.md`, `skills-plugin/skills/intake/SKILL.md`) -- current orchestrator and intake behavior verified
- Phase 2 CONTEXT.md (`.planning/phases/02-express-mode-framework/02-CONTEXT.md`) -- locked decisions and scope restructuring
- Phase 1 CONTEXT.md (`.planning/phases/01-rcars-mcp-gateway/01-CONTEXT.md`) -- cross-repo patterns, established conventions
- Express mode design spec (`docs/superpowers/specs/2026-04-28-express-mode-design.md`) -- original architecture, partially descoped
- RCARS integration design spec (`docs/superpowers/specs/2026-04-27-rcars-integration-design.md`) -- MCP tool patterns, auth model
- Manifest template (`template/publishing-house/manifest.yaml`) -- canonical manifest YAML schema

### Secondary (MEDIUM confidence)
- Package versions verified via `pip show` in portal backend venv (fastmcp 3.2.4, SQLAlchemy 2.0.49, Pydantic 2.13.3, httpx 0.28.1)
- Alembic migration pattern verified via `alembic/env.py` and `alembic/versions/` directory listing

### Tertiary (LOW confidence)
- None -- all claims in this research were verified against the codebase or cited from CONTEXT.md decisions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing packages verified
- Architecture: HIGH -- follows established MCP tool and DB model patterns from Phase 1
- Pitfalls: HIGH -- identified from direct codebase analysis (refresh job, JSONBType duplication, auth middleware)
- Skill changes: MEDIUM -- SKILL.md changes are behavioral instructions, not code. Exact wording needs iteration.

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (stable -- no fast-moving dependencies)
