# Publishing House Common Rules

Rules that apply to ALL Publishing House skills. Read this before working on any PH skill.

## Manifest is Source of Truth

- Always read `publishing-house/manifest.yaml` before taking action
- Update manifest after completing any phase or substep
- Never modify manifest fields outside your agent's scope
- Use ISO 8601 dates (YYYY-MM-DD) for all timestamps

## Autonomy Levels

The manifest's `project.autonomy` field controls agent behavior:

- **supervised**: Present every artifact to user for approval before writing to disk or committing. Ask "Does this look right?" after each output. Do not commit without explicit approval.
- **semi**: Write artifacts to disk and commit to a WIP branch. Run validation skills automatically. Only pause for user input at phase gates (transitions between lifecycle phases) and decision points (e.g., RCARS vetting results).
- **full**: Work through the entire current phase end-to-end. Present completed output at the phase gate for review before transitioning to the next phase.

## Phase Transitions

- Only the orchestrator transitions between phases
- Agents report completion back to the user; the orchestrator updates the manifest
- Never skip the approval gate (phase 4) — it always requires explicit human approval

## Read Before You Act

All agents MUST read their input files fresh at execution time. Never rely on prior context, cached content, or assumptions about file state.

- **Orchestrator:** Read `manifest.yaml` at session start and after every agent dispatch
- **Intake agent:** Read the manifest and any provided spec documents at the start of each phase
- **Writer agent:** Read the specific module outline from `spec/modules/` immediately before writing. If the outline changed since the last draft, the new version is what matters.
- **Editor agent:** Read both the module outline and the generated content before reviewing
- **All agents:** The files on disk at dispatch time are the contract. If a human or another agent modifies a file after dispatch, the running agent is not responsible for picking up those changes mid-execution.

## Human Modifications Are Expected

Content files, spec files, and outlines may be modified by humans at any time — between
sessions, between agent invocations, or even mid-phase. A human may edit AsciiDoc content
directly, refine a module outline, or restructure sections without going through an agent.

**Never assume a file is the same as when an agent last wrote it.** Always read the current
version from disk. If a file has changed since the last agent run:
- Respect the human's changes as intentional
- Build on top of what exists rather than overwriting it
- Flag divergence from the spec as informational (the human may have had good reasons)
- Ask before reverting or overwriting human work, even in `full` autonomy mode

The manifest tracks module status, but it cannot track every human edit. A module marked
`drafted` may have been substantially revised by a human since the writer agent produced it.
Treat the file on disk as the source of truth for content, and the manifest as the source
of truth for lifecycle state.

## File Conventions

- Specs go in `publishing-house/spec/`
- Module outlines go in `publishing-house/spec/modules/`
- Review artifacts go in `publishing-house/reviews/`
- Decision records go in `publishing-house/decisions/`
- Content output goes in `content/`
- Automation output goes in `automation/`

## Sensitive Content

Publishing house project repos are private. However:
- Never include real credentials, API keys, or tokens in any file
- Use `<placeholder>` syntax for sensitive values
- Content that will eventually move to a public Showroom repo must follow
  Red Hat's public repository guidelines (no internal hostnames, customer data, etc.)

## Communication Style

- Be concise and direct
- Lead with the answer or action, not the reasoning
- When presenting status, use structured format:
  - Current phase, what's done, what's next
  - Module-level progress where applicable
- Ask one question at a time when gathering information

## Referencing Other Skills

When dispatching to existing RHDP skills, inform the user which skill is being used:
"Using showroom:create-lab to write Module 1 content."

Do not re-implement logic that exists in other skills. Wrap and invoke them.
