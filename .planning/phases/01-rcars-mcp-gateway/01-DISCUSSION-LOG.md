# Phase 1: RCARS MCP Gateway - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-30
**Phase:** 01-rcars-mcp-gateway
**Areas discussed:** API key lifecycle, RCARS client resilience, Cross-repo work plan, Documentation scope

---

## API key lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Hot-reload from Secret | Backend watches or periodically re-reads the K8s Secret (e.g. every 60s). Zero-downtime key management. | |
| Pod restart | Backend reads keys at startup only. Update Ansible vars, redeploy, pod restarts. | ✓ |
| You decide | Let Claude pick the best approach. | |

**User's choice:** Pod restart
**Notes:** "Okay with pod restart for initial implementation. Later should be more robust. API keys in a kube secret." Future vision: browser-based Red Hat SSO auth.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Manual workflow only | Follow design spec: openssl rand, sha256sum, paste into Ansible vars, redeploy. | ✓ |
| Simple CLI helper | Script that generates key, hashes it, outputs Ansible vars entry. | |
| You decide | Let Claude pick. | |

**User's choice:** Manual workflow only
**Notes:** "Manual fine for now for few initial users. Future: callback that authenticates via Red Hat SSO in browser."

---

| Option | Description | Selected |
|--------|-------------|----------|
| Environment variable | Keys from single env var (YAML string). | |
| Volume-mounted file | Secret mounted as file the backend reads. | ✓ |
| You decide | Let Claude pick. | |

**User's choice:** Volume-mounted file
**Notes:** Leaves door open for hot-reload later.

---

## RCARS client resilience

| Option | Description | Selected |
|--------|-------------|----------|
| Retry with backoff | 3 retries with exponential backoff (1s, 2s, 4s) on transient failures. Fail fast on 4xx. | ✓ |
| Fail fast, no retry | Return error immediately. Skill or user decides to retry. | |
| You decide | Let Claude pick. | |

**User's choice:** Retry with backoff
**Notes:** "Does it make sense for the skill to have logic programmed for retries? I am trying to keep the skill size and complexity manageable." — Retry logic belongs in the backend HTTP client, not the skill.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal - actionable only | Simple "RCARS unavailable, vetting skipped" message. | |
| Moderate - include context | Retry count, failure type, service name. Enough for developer diagnosis. | ✓ |
| You decide | Let Claude balance. | |

**User's choice:** Moderate - include context

---

| Option | Description | Selected |
|--------|-------------|----------|
| Active probe | Health endpoint calls RCARS on every request. Accurate, adds latency. | ✓ |
| Passive / last-known | Track success/failure of recent calls. No extra load. | |
| You decide | Let Claude choose. | |

**User's choice:** Active probe

---

## Cross-repo work plan

| Option | Description | Selected |
|--------|-------------|----------|
| Portal-first, then fan out | Build full gateway in portal, then companion changes. | |
| Dependency order | RCARS allowlist first, then portal, then skills. Each step verifiable. | ✓ |
| You decide | Let Claude figure out sequencing. | |

**User's choice:** Dependency order

---

| Option | Description | Selected |
|--------|-------------|----------|
| Config changes only | Prepare Ansible vars, document deploy command. User deploys manually. | ✓ |
| Include deploy steps | Plan includes running Ansible deployer. | |
| You decide | Let Claude assess. | |

**User's choice:** Config changes only

---

| Option | Description | Selected |
|--------|-------------|----------|
| Independent PRs per repo | Each repo gets its own PR. | |
| Single tracking PR + companions | Portal PR primary, others reference it. | |
| Direct commits (no PRs) | Commit directly to branches. | ✓ |

**User's choice:** Direct commits
**Notes:** `gsd-project` branch for PH repos. Direct to `main` for `rcars-advisory` (rcars-dev builds from main, rcars-prod from production — only touch dev). Skills and template are submodules in rhdp-publishing-house — commit through main dev repo, pull local clones after.

---

## Documentation scope

| Option | Description | Selected |
|--------|-------------|----------|
| All 5 ship together | Complete documentation alongside code. | ✓ |
| Essentials only, defer rest | CC Setup Guide and MCP Tools Reference only. | |
| You decide | Let Claude assess. | |

**User's choice:** All 5 ship together
**Notes:** "Documentation is a first class citizen and requirement. It should be done alongside or as soon as something works. If there are changes that need to be made to the rcars documentation to make all of this match, do that as well."

---

| Option | Description | Selected |
|--------|-------------|----------|
| All in this repo | All docs under `docs/` in rhdp-publishing-house. | ✓ |
| Split by repo | User-facing here, implementation docs in portal repo. | |
| You decide | Let Claude place docs. | |

**User's choice:** All in this repo
**Notes:** "I am already not happy with the portal repo being separate, I think it will be confusing in the end."

---

## Claude's Discretion

- FastMCP 2.0 → 3.2+ migration approach
- httpx AsyncClient configuration details
- RCARS HTTP client module structure
- Health check probe implementation details
- Keycloak auth scaffolding removal approach

## Deferred Ideas

- Browser-based API key provisioning via Red Hat SSO callback — future milestone
- Portal repo consolidation into main dev repo — user flagged dissatisfaction
- Hot-reload for API key Secret — preserved as future option by volume-mount choice
