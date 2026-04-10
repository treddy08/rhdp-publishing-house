# RHDP Publishing House

## AI-Powered Content Lifecycle Management for RHDP

### The Problem

Building an RHDP workshop today requires a content developer to juggle multiple tools, skills, and processes — writing AsciiDoc modules, creating AgnosticV catalogs, developing Ansible/GitOps automation, coordinating reviews, and managing security checks. Each step requires different expertise and tools. Most time is spent on toil, not design.

### The Solution

**RHDP Publishing House** is a Claude Code plugin that turns content developers into content architects. One command — `/rhdp-publishing-house` — provides a persistent, state-aware orchestrator that manages the entire content lifecycle through specialized AI agents.

```
Intake* → Vetting → Spec Refinement → [Approval*] → Writing → Editing*
  → Automation → Security Review* → Final Review* → Ready for Publishing

* = required    (unmarked = optional, skip if handled another way)
```

### How It Works

**Use What Helps You** — Publishing House doesn't require end-to-end adoption. Intake, editing, and security review are required quality gates. Writing and automation are optional — skip them if you've handled those steps manually or with another tool. Bring an existing spec to shortcut intake.

**Single Entry Point** — Run `/rhdp-publishing-house` and the orchestrator picks up where you left off. "Welcome back — Module 1 is drafted, Module 2 is next." No skill memorization required.

**Specialized Agents** — Six focused AI agents — Intake, Writer, Editor, Automation, Security, Review — each backed by existing RHDP skills where possible (showroom, agnosticv, code-review). No reinventing the wheel.

**Configurable Autonomy** — Three modes: **supervised** (review every artifact), **semi** (review at gates), **full** (review at phase completion). Start supervised, build trust, scale up.

**RCARS Integration** — Automatically vets new content against the existing RHDP catalog via the RCARS API. Identifies gaps, prevents duplication, and can feed gap analysis directly into new project creation.

**Persistent State** — A YAML manifest tracks every phase, module, and decision. Start Monday, pick up Wednesday. Hand off to a colleague — they see exactly where things stand.

**Lowers the Bar** — Less technical team members can create simple 5-10 minute labs without relying on dedicated technical resources. The automation agent writes working Ansible/Helm — not just scaffolding. New contributors become productive faster.

### Three Ways to Start a Project

1. **Full Spec** — Experienced content dev brings a detailed spec. Agent fills any gaps.
2. **Rough Idea** — "I need a lab on ServiceMesh." Agent builds the full spec through conversation.
3. **RCARS Gap** — RCARS identifies a content gap. That single sentence becomes the seed for a new project.

### What Changes for Content Developers

| Today | With Publishing House |
|-------|----------------------|
| Write every AsciiDoc module by hand | Design the architecture, agents write the content (or skip if you wrote it yourself) |
| Manually create AgnosticV configs | Agents handle catalog creation and validation (or skip if handled externally) |
| Write all automation from scratch | Automation agent writes working Ansible/Helm (or skip and bring your own) |
| Remember which skills/tools to use when | One command, orchestrator knows what's next |
| Track progress in your head or ad hoc notes | Manifest tracks everything automatically |
| Context lost between sessions and handoffs | Pick up any day, hand off to anyone |
| Quality review is manual and inconsistent | Editing + security review always run, regardless of how content was produced |

### Solo or Team — Works Either Way

Publishing House is built for collaboration without requiring it. The YAML manifest is the coordination layer — no external project management tool needed.

- **Timezone handoff** — Developer A works through spec and design, pushes. Developer B picks up hours later, runs `/rhdp-publishing-house`, sees exactly where things stand and what's next.
- **Role-based handoff** — A content architect designs the spec and overall structure, then hands the project to a developer who executes with agent assistance. Each person works to their strengths.
- **Solo mode** — One person benefits equally. The orchestrator tracks progress across days and weeks. Nothing falls through the cracks.
- **Distributed review** — Different team members can own different phases. One writes, another edits, a third handles security. The manifest tracks who did what.

### Built on What We Have

Publishing House doesn't replace existing tools — it orchestrates them. It wraps `showroom:create-lab`, `showroom:verify-content`, `agnosticv:catalog-builder`, `code-review`, and other skills already in the RHDP marketplace. New capabilities (intake, automation writing, content security) are added as focused, standalone agent skills.

### Architecture: Hub + Spoke

A thin orchestrator manages state and dispatches to specialized agent skills. Each agent is its own skill — focused, testable, independently iterable.

```
/rhdp-publishing-house [supervised|semi|full]
         |
    Orchestrator (reads manifest, determines phase, dispatches)
         |
    +----+----+--------+----------+---------+--------+
    |         |        |          |         |        |
 Intake    Writer   Editor   Automation  Security  Review
```

### Implementation Path

- **Phase 1:** Plugin structure + orchestrator + manifest system + intake agent
- **Phase 2:** Writer + editor agents (wrapping existing showroom skills)
- **Phase 3:** Automation agent (AgnosticV + Ansible/Helm generation)
- **Phase 4:** Security + review agents
- **Phase 5:** RCARS integration (when API is ready)
- **Future:** CLI/web app extraction, ZT grading integration, `/rhdp` namespace consolidation
