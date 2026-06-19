# Publishing House — Development Worklog

Session notes and handoff context for the PH dev team. Use this to communicate between developers what was done, what's in progress, and what the next person should pick up.

Clear periodically — the backlog ([BACKLOG.md](BACKLOG.md)) is the persistent roadmap.

---

## 2026-06-18/19 — Publishing House Central architecture + implementation (Nate)

### Backlog triage and quick wins
- Triaged the full PH backlog, prioritized near-term items
- Added Zero-Touch Showroom support to the project template (`runtime/`, `setup/` dirs), manifest (`showroom_type` field), intake skill, and orchestrator (cleanup for classic projects)
- Dropped `ph_store_validation_results` wiring — git review files are the source of truth, portal UI adds complexity without current value
- Updated Jira integration spec: project key RHDPCD, Template 2 (Basic Project) with self-service switch to OJA-ITS-003 (Standard) via Delegated Project Admin. JSM request submitted.

### PH Central architecture evolution (major)
- Brainstormed and designed the architecture evolution from portal to "Publishing House Central"
- Design spec: [2026-06-19-publishing-house-central-design.md](docs/superpowers/specs/2026-06-19-publishing-house-central-design.md)
- Core principle: **trust but verify** — local LLM and skills have full creative freedom, Central owns validation, gate enforcement, and custody chain
- All phases are required (no optional phases), three deployment mode profiles with different gate hardness
- Central reads from git (not MCP payloads), project identity = repo URL + branch
- Custody chain: independent record of gate decisions that the manifest can't override

### PH Central backend implementation (63 tests)
- Renamed repo from `rhdp-publishing-house-portal` to `rhdp-publishing-house-central`
- All work on `feature/ph-central-registration` branch (not merged to main)
- **New services:** GitRepoReader, PhaseEngine, GateService, SpecValidator
- **New models:** GateRecord (custody chain), SubmittedResult, Project.branch column
- **7 MCP tools:** `ph_register`, `ph_list_projects`, `ph_get_status`, `ph_request_gate`, `ph_submit_results`, `ph_get_history`, `ph_approve` (noted, deferred)
- **Gate enforcement:** Central verifies its own gate records (doesn't trust manifest), RCARS unavailable = hard reject, self-approval rejected for onboarded projects, spec commit tracking for vetting loop
- **Vetting posture:** Server-side challenging assessment with fixed tone, "completed" not "approved" for non-approval phases
- Deployed to `publishing-house-central-dev` namespace on ocpv-infra01, parallel to existing dev deployment
- RCARS SA allowlist updated for new namespace
- Fixed Ansible build tasks (replaced `kubernetes.core.k8s_info` with `oc` commands for Build resources)

### Skill updates
- All work on `feature/ph-central-skills` branch (not merged to main)
- Orchestrator: uses Central tools, tool boundary enforcement, one-gate-per-request rule, all phases required
- Intake: removed direct RCARS calls, vetting handled by Central via orchestrator, spec refinement reads vetting findings for recommendations

### MCP server configuration
- Found and fixed MCP config location: `~/.claude.json` (not `~/.claude/mcp.json` or `~/.claude/settings.json`)
- Transport type `http` with trailing slash matches existing working servers
- Moved MCP config to `~/devel/secrets/ph-mcp-dev.json`, removed old `~/.config/rhdp-publishing-house/` directory
- Updated user docs three times as we found the correct configuration

### Key discovery: LLM presentation problem
- Despite server-side gate enforcement working correctly, the LLM orchestrator consistently reinterprets Central's output — says "approved" when Central said "completed", ignores `vetting_assessment` fields, auto-advances through multiple gates
- Multiple rounds of instruction strengthening (one-gate-per-request, STOP/WAIT, verbatim presentation) did not reliably fix the behavior
- This is a fundamental limitation of LLM-driven interfaces for workflow enforcement, not fixable with better instructions
- Added **deterministic client layer** as BLOCKING priority backlog item

### Other fixes
- Removed stale `rhdp-skills-marketplace` local dev clone (was causing confusion with outdated v2.4.8 vs installed v2.14.0)
- Saved memory: always check installed plugin paths (`~/.claude/plugins/marketplaces/`) not dev clones

### Feature branches (NOT merged to main)
| Repo | Branch | Content |
|---|---|---|
| `rhdp-publishing-house-central` | `feature/ph-central-registration` | Backend: 7 MCP tools, 5 services, 3 models, 63 tests, Ansible fixes |
| `rhdp-publishing-house-skills` | `feature/ph-central-skills` | Orchestrator + intake rewritten for Central |
| `rhdp-publishing-house` | `feature/ph-central` | Spec, plans, backlog, submodule pointer |

### What's next
1. **Deterministic client layer** (BLOCKING) — design the application that sits between user and Central, controls workflow deterministically, uses LLM only for creative work
2. **Dashboard redesign** — show Central data (custody chain, gate history, project status from git)
3. **SpecValidator LLM quality checks** — backend LLM via LiteLLM/MaaS for spec quality assessment
4. **Merge feature branches** — after the client layer approach is decided and validated

---

## 2026-05-15 — Phase 4 brainstorm + design spec (Nate)

### Hosted Workspace design (formerly "Portal Chatbot")
- Brainstormed and designed the Phase 4 hosted access solution
- Original concept was a portal chatbot calling MCP tools — evolved to a full hosted Dev Spaces workspace after determining full CC skill parity was required
- Key architectural decisions:
  - OpenShift Dev Spaces with custom UDI (RHEL9 base), hosted on `quay.io/rhpds/ph-udi:latest`
  - Portal provisions workspaces via Dev Spaces API, MaaS keys via LiteLLM REST API
  - One workspace per project per user, opt-in ("Open in Dev Spaces" button on project detail)
  - One-way integration only: workspace → portal (MCP), portal never pushes to workspace
  - CC CLI updated at every session start, not baked into image
  - MaaS key lifecycle fully portal-managed — provision, validate on resume, revoke on delete
  - Key duration configurable (env var), expired key = restart workspace from portal
  - Chose Dev Spaces over lighter alternatives partly for Red Hat dog-fooding story
- Design spec written: [2026-05-15-hosted-workspace-design.md](docs/superpowers/specs/2026-05-15-hosted-workspace-design.md)
- BACKLOG.md updated: Phase 4 renamed and marked SPEC COMPLETE, new backlog items added

### Backlog additions
- MCP auth rationalization (near-term)
- Lightweight express mode execution (future — Dev Spaces too heavy for one-off demos)
- UDI image rebuild pipeline, mid-session key rotation, Dev Spaces API exploration (future)

### What's next
- **Phase 4 spec review** — share with team for feedback before implementation planning
- **Phase 3: Jira integration** — spec done, blocked on Jira SA provisioning
- **Express skill** — unblocked, needs brainstorm
- See [BACKLOG.md](BACKLOG.md) for full roadmap

---

## 2026-05-06 — Documentation overhaul + template restructuring (Nate, pre-PTO)

### Documentation accuracy review
- Cross-referenced all docs/ against actual code in all 4 repos (portal, skills, template, main)
- Fixed 12 files: broken links, wrong parameter types, missing MCP tools, stale branch refs
- Replaced 7 ASCII art diagrams with Mermaid (exec summary, how-it-works, portal, rcars-integration, portal-deployment)
- Added Mermaid custom_fences config to mkdocs.yml
- Updated CLAUDE.md MCP tools table: added 3 missing tools (`ph_get_launch_instructions`, `ph_store_validation_results`, `ph_get_validation_results`)
- Fixed `ph_get_launch_instructions` param type (int → str), advisor poll interval (3s → 10s), `ph_list_projects` return shape
- Removed stale `gsd-project` branch references from portal-deployment.md

### Portal cleanup
- Renamed `_ph_dashboard_oauth` cookie → `_ph_portal_oauth`
- Fixed "from the dashboard" → "from the portal" in delete dialog
- Built and deployed frontend to dev

### Template restructuring
- Embedded Showroom scaffold in PH template (site.yml, ui-config.yml, content/antora.yml, nav.adoc, index.adoc)
- Removed submodule pattern: content/ and automation/ are now regular directories, not separate repos
- Removed `integrations.showroom_repo` and `integrations.automation_repo` from manifest template
- Removed 84 lines of submodule gate logic from orchestrator SKILL.md
- Updated template CLAUDE.md, README.md, .gitignore
- Updated how-it-works.md project template section

### Housekeeping
- Removed `.planning/` directory (replaced by backlog + docs as source of truth)
- Added `.claude/` to .gitignore, restored `.superpowers/`

### Test prompts
- Created 15 intake test prompts in test/ (3 modes × 5 tech areas)
- Mix of direct asks and CFP abstract styles for realistic intake testing

### What's next
- **Test intake end-to-end** using the test prompts against live MCP server
- **Phase 3: Jira integration** — spec done, ready for implementation planning (blocked on Jira SA)
- **Phase 4: Portal chatbot** — needs brainstorm
- **Express skill** — unblocked, needs design
- See [BACKLOG.md](BACKLOG.md) for full roadmap
