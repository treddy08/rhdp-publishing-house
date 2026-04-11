# Getting Started

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- A GitHub account with access to the `rhpds` org

## Quick Start

The plugin is not yet published to a marketplace. Follow these steps to set up locally.

### 1. Clone the plugin repo

```bash
git clone git@github.com:rhpds/rhdp-publishing-house.git ~/rhdp-publishing-house
```

### 2. Create a project repo from the template

```bash
gh repo create my-new-lab \
  --template rhpds/rhdp-publishing-house-template \
  --private --clone
```

### 3. Enter your project repo

```bash
cd my-new-lab
```

### 4. Start Claude Code with the plugin

From inside your project repo, start Claude Code with `--plugin-dir` pointing
to where you cloned the plugin in step 1:

```bash
claude --plugin-dir ~/rhdp-publishing-house
```

### 5. Start the orchestrator

In the Claude Code session:

```
/rhdp-publishing-house
```

The orchestrator detects a fresh project and walks you through intake.

### 6. Follow the orchestrator

The orchestrator guides you through the content lifecycle. Not all phases are required —
use what helps you, skip what doesn't.

**Required phases:**
- **Intake** — build your spec (or bring an existing one to shortcut)
- **Approval** — you review and approve the spec
- **Technical Editing** — quality review (runs regardless of how content was produced)
- **Security Review** — content security audit
- **Final Review** — holistic check before marking ready

**Optional phases** (skip if you've handled them another way):
- **Vetting** — check against existing RHDP content via RCARS
- **Spec Refinement** — clean up for downstream agents
- **Writing** — skip if you wrote the content manually
- **Automation** — skip if environment setup is handled externally

Say "skip writing" or "I already have content" to jump ahead.
Ask "what's next" at any point for guidance.

### 7. Collaborate

Push your repo. A colleague clones it, runs `/rhdp-publishing-house`, and picks
up exactly where you left off. The manifest tracks everything.

## Autonomy Levels

Control how much review you want:

```
/rhdp-publishing-house              # supervised (default) — review everything
/rhdp-publishing-house semi         # review at phase gates only
/rhdp-publishing-house full         # review at phase completion
```

Switch mid-session: "switch to semi"

## Model Recommendations

Different phases benefit from different models:

| Phase | Recommended Model | Why |
|-------|------------------|-----|
| **Intake** | Opus 4.6 | Deep exploration of requirements, thorough spec generation |
| **Writing** | Sonnet 4.6 | Module outlines provide sufficient guardrails |
| **Editing** | Sonnet 4.6 | Checklist-driven review against standards |
| **Automation** | Opus 4.6 | Complex reasoning for Ansible/Helm generation |
| **Security** | Sonnet 4.6 | Pattern-matching against known security checks |
| **Review** | Sonnet 4.6 | Structured holistic review |

For simple 5-10 minute labs, Sonnet 4.6 handles all phases well.
For large multi-module workshops, Opus on intake and automation pays off in spec
quality and automation correctness.

## Tips

- The manifest (`publishing-house/manifest.yaml`) is the source of truth for lifecycle state
- Module outlines in `publishing-house/spec/modules/` drive the writing phase — invest time making them good
- Human edits to content, specs, and automation are expected and respected by all agents
- If RCARS API isn't available, you can skip vetting and come back to it later
- The automation phase includes a testing gate — deploy and verify your automation works before moving to security review
