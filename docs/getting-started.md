# Getting Started

## Prerequisites

### 1. Install Claude Code

[Install Claude Code](https://docs.anthropic.com/en/docs/claude-code) if you haven't already.

### 2. Install the Publishing House plugin

Clone the skills repo. You only do this once.

```bash
git clone git@github.com:rhpds/rhdp-publishing-house-skills.git ~/rhdp-publishing-house-skills
```

Add the plugin to your Claude Code settings, or pass it at launch with `--plugin-dir ~/rhdp-publishing-house-skills`.

### 3. Create your project repo from the template

**Option A — GitHub web UI (no extra tools required):**

1. Go to `https://github.com/rhpds/rhdp-publishing-house-template`
2. Click **Use this template → Create a new repository**
3. Set it to **Private**, give it a name, and create it
4. Clone it:
   ```bash
   git clone git@github.com:your-org/your-repo.git
   cd your-repo
   ```

**Option B — `gh` CLI:**

```bash
gh repo create my-new-lab \
  --template rhpds/rhdp-publishing-house-template \
  --private --clone
cd my-new-lab
```

---

## Quick Start

From inside your project repo, start Claude Code and run:

```
/rhdp-publishing-house
```

The orchestrator finds the manifest, syncs the repo, and starts intake.

> **Resuming later:** Run `/rhdp-publishing-house` from your project directory. If the orchestrator can't find your project, it'll ask for the path or repo URL.

### 4. Answer the intake questions

The intake agent asks what you're building, what it's for, and how you plan to deploy it. If you already have a design doc, Google Doc, or rough outline, provide it and the agent extracts answers from it instead of asking every question.

You'll cover:

- **What are you building?** — name, type (workshop or demo), target audience
- **Deployment mode** — RHDP Published or Self-Published (see below)
- **Modules** — how many, rough titles, estimated duration
- **Automation** — whether the lab needs infrastructure pre-configured

### 5. Approve the spec

After intake, the agent produces `publishing-house/spec/design.md` and per-module outlines. Review and approve. This is the only hard gate before writing starts.

### 6. Write, automate, edit

From here, the orchestrator guides you. Say what you want to do and it routes to the right agent:

- `"write module 1"` — writer agent generates AsciiDoc from the module outline
- `"build automation"` — automation agent captures requirements, creates the catalog, writes code
- `"edit all"` — editor agent reviews content against Red Hat standards and your spec
- `"what's next"` — lightweight status summary, no heavy loading

### 7. End the session

Say `"I'm done for today"` or `"session summary"`. The orchestrator writes a worklog entry, commits the manifest and worklog, and pushes. Next session, the pull happens automatically.

---

## Deployment Modes

Set during intake. Determines the automation path and publishing target.

| Mode | Description | Automation | Published In RHDP? |
|------|-------------|------------|-------------------|
| **RHDP Published** (`onboarded`) | Full pipeline. Review gates, AgnosticV catalog, published as a standalone item. | Ansible, GitOps, or both | Yes |
| **Self-Published** (`self_published`) | You manage deployment. Uses the generic Field Source CI with your GitOps repo URL. | GitOps only (Helm + ArgoCD) | No |
| **Express** (`express`) | Fast path for one-off demo environments. No git repo, no review gates. See [Express Mode](express-mode-overview.md). | Live cluster customization | No |

The content pipeline (intake, writing, editing) is the same for onboarded and self-published modes. Express mode is a separate fast path — it runs through intake, identifies a base CI from the RCARS catalog, and then gates on environment provisioning. See [Express Mode](express-mode-overview.md) for the full lifecycle.

---

## Autonomy Levels

Control how much review you want at each step:

```
/rhdp-publishing-house              # supervised (default) — review everything
/rhdp-publishing-house semi         # review at phase gates only
/rhdp-publishing-house full         # review at phase completion
```

Switch any time mid-session: `"switch to semi"`

---

## Required vs. Optional Phases

**Required** (cannot be skipped):
- **Intake** — shortcuttable with a pre-existing spec, but always runs
- **Approval** — you review and sign off on the spec; never auto-advanced
- **Technical Editing** — runs regardless of how content was produced
- **Code & Security Review** — required for `rhdp_published`; recommended for `self_published`
- **Final Review** — holistic check before marking ready

**Optional** (skip if handled another way):
- **Vetting** — check against existing RHDP content via RCARS
- **Spec Refinement** — clean up spec before writing starts
- **Writing** — skip if you wrote content manually
- **Automation** — skip if environment setup is handled externally

Say `"skip writing"`, `"I already have content"`, or `"skip automation"` to jump ahead.

---

## Collaborating on a Project

The manifest is the source of truth. Push your repo; a colleague runs `/rhdp-publishing-house` and picks up exactly where you left off.

The orchestrator **pulls at session start and pushes at session end** — you don't need to manage this manually.

For async handoffs, use the worklog:

```
"leave a note: check with Prakhar on pool sizing before creating the catalog"
"what's outstanding"
"resolve item 2026-04-14-001"
```

The worklog lives in `publishing-house/worklog.yaml` and is committed with every update.

---

## Resuming a Session

Run `/rhdp-publishing-house` from your project directory. The orchestrator:

1. Finds the manifest in the current directory
2. Pulls latest changes
3. Reads manifest and worklog
4. Presents current status and open items
5. Asks what you want to do next

If the orchestrator can't find your project, it offers to locate it by path, clone it from a remote, or walk you through creating a new one.

---

## Tips

- **Invest in module outlines.** The writer agent generates content from `publishing-house/spec/modules/` — the more detailed the outline, the better the output.
- **Human edits are expected.** Edit content, specs, and automation files freely between sessions. All agents read fresh and respect what's there.
- **The worklog is for notes, not tasks.** Manifest tracks phases; worklog tracks decisions, handoffs, and context that doesn't fit in structured fields.
- **RCARS not available?** Skip vetting and come back to it later — it's optional.
- **Automation testing gate.** After the automation agent writes code, you deploy it yourself and confirm with `"testing done"`.
