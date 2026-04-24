# Publishing House — Development Worklog

Session notes and open items for the PH dev team.

---

## 2026-04-21

### Session Summary

Full skills redesign implemented and tested end-to-end with the RHBK OIDC lab
(`ex-instruction-test`). Reviewed all phases: intake, writing, automation. Documented
12 issues, resolved them all in one implementation pass. All changes committed and pushed.

### What Was Done

- Skills redesign (deployment modes, worklog, smart intake, git sync) — complete
- Intake: Environment section replaces Infrastructure+Automation, simplified repo setup, Showroom required by default
- Orchestrator: strict phase order (writing before automation), worklog routing, project discovery from any directory
- Automation: AsciiDoc-first 7a, per-user-cluster vs shared-cluster topology question, 7c writes worklog entries for blockers, Showroom in provision_data
- Automation manifest format: self_published infrastructure taxonomy (field-per-user-cluster, field-shared-cluster)
- GitOps guide: rewritten around ci-template-gitops patterns, two-role model (field_content_cluster + field_content_tenant), eventual consistency
- Template: removed journal.md (superseded by worklog.yaml), content/ and automation/ now submodules
- Docs: refreshed getting-started, how-it-works, portal.md (was dashboard.md), README, skills README

### Open Items for Next Session

**1. DISCUSS: PH development team design**

Nate owns the orchestrator, overall design, and the contributor standards. Individual
skills (writer, automation, editor) should be ownable by other contributors without
needing to understand the whole system.

Need to write a **contributor spec** that defines:
- What a skill MUST read from the manifest/spec before starting
- What state a skill MUST update when it completes
- What a skill MUST NOT touch (phase-level transitions belong to the orchestrator)
- How a skill surfaces blockers (worklog entries, not improvised fields)
- How to test a skill in isolation

This is the prerequisite for delegating skill ownership to other team members.

**2. LONGTERM: PH chatbot UI**

Instead of running Claude Code or Cursor locally, a hosted chatbot runs the skills on
the user's behalf. Users interact via browser — no local tooling required. Would tie
RCARS, Publishing House, and the portal together into a single entry point.

This is a future design effort, not near-term implementation.

**3. AgnosticD: Split ocp4_workload_field_content**

Split into `field_content_cluster` + `field_content_tenant` roles. Both deploy ArgoCD
apps and return immediately (no health waiting). ArgoCD eventual consistency handles
operator → CR ordering. Field Source CI runs both in sequence without waiting between.
This is a separate workstream in the AgnosticD repo.

**4. Subagent-per-module writing**

For large labs (2+ hours, 6+ modules), writing could use isolated subagents per module
to avoid context accumulation. Parked — revisit when scale becomes a real problem.
