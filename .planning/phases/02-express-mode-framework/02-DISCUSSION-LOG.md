# Phase 2: Express Mode Framework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 02-express-mode-framework
**Areas discussed:** Express project lifecycle, Orchestrator startup flow, Intake routing & session continuity

---

## Express Project Lifecycle

**Major scope change:** User challenged the fundamental assumption that express projects need lifecycle tracking in the portal DB.

**User's position:** Express is throwaway — PH helps get the environment, customizes it, hands it off, and is done. No value in tracking these as "projects." The only value in persisting data is: (1) metrics (how many express runs, automated vs. manual), and (2) eventually, RCARS learning data (which base CIs worked for which needs).

**Key quote:** "I'm not sure we should 'track' these. They are meant to be throwaway... What benefit does tracking the lifecycle do? Once PH provides the environment, it should forget about it."

**Outcome:** Express projects are NOT tracked as projects. Metrics only. RCARS learning data backlogged (needs design to avoid polluting content search). Added to both PH and RCARS backlogs.

**Follow-up realization:** Phase 2 as originally scoped (full express framework) is "incredibly light" without the express skill. User agreed to restructure Phase 2 to focus on orchestrator evolution and session continuity (benefits all modes, enables chatbot), with express intake routing folded in as a lightweight addition.

---

## Orchestrator Startup Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Local manifest wins | If a manifest exists locally, use it. Only query portal when no local manifest found. | |
| Show both | Always query portal alongside local discovery. Show all projects. | |
| Local first, portal on demand | Use local manifest if found. If not found, query portal automatically. User can ask for portal projects anytime. | ✓ |

**User's choice:** Option 3, with a prompt hint: "If you don't see your project here, ask for a list from the portal."

### MCP Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful degradation | Note unavailable, continue local-only. | |
| Warn and block portal features | Warn user, list unavailable features, proceed local-only. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Warn and block portal features.

### User Identification

| Option | Description | Selected |
|--------|-------------|----------|
| Red Hat email from git config | Read user.email from git config. | |
| Explicit config in manifest or env var | User sets email in PH config or env var. | |
| Ask on first use, cache locally | Prompt on first query, save locally. | |

**User's choice:** Combo of 2 and 3 — check for configured email first (PH config or env var), if not found, prompt once and cache locally.

---

## Intake Routing & Session Continuity

### Intake Data Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Full intake interview | Everything captured during intake. Portal becomes full source of truth. | |
| Summary + key fields | Enough to resume and show on portal, not full manifest copy. | |
| Mirror the manifest | Portal DB schema mirrors manifest.yaml fields. Either can bootstrap the other. | ✓ |

**User's choice:** Most like option 3. Manifest still needs to be source of truth. Portal DB mirrors the same shape. Portal can augment with portal-specific needs (especially for express during build/configure), but for onboarded/self-published modes it shouldn't be meaningfully different.

### Sync Timing

| Option | Description | Selected |
|--------|-------------|----------|
| On phase transitions | Coarse-grained, portal may lag during active work. | |
| On every manifest write | Real-time sync on every skill update. | ✓ |
| On session end | Batched at session teardown. | |

**User's choice:** On every manifest write.

### Express State Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Portal DB only | Express intake data lives exclusively in portal DB. | ✓ |
| Portal DB + local temp file | Write to both; temp file for convenience, DB for durability. | |
| You decide | Claude picks. | |

**User's choice:** Portal DB only.

---

## Claude's Discretion

- Portal DB schema details for manifest mirroring
- MCP tool contracts for session continuity
- Express metrics storage mechanism
- User email caching format and location
- Manifest-to-portal sync conflict handling

## Deferred Ideas

- RCARS express learning data — backlogged to both PH and RCARS repos
- Express portal UI (kanban, detail views) — removed from Phase 2
- Express project lifecycle tracking — removed
- Babylon ordering automation — manual gate
- Portal user identity model — separate workstream
