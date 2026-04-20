# Getting Started

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- A GitHub account with access to the `rhpds` org

## Install the Plugin

Point Claude Code at the Publishing House skills repo. You only do this once.

```bash
git clone git@github.com:rhpds/rhdp-publishing-house-skills.git ~/rhdp-publishing-house-skills
```

Then add the plugin directory to your Claude Code settings, or pass it at launch:

```bash
claude --plugin-dir ~/rhdp-publishing-house-skills
```

> **Tip:** Add `--plugin-dir ~/rhdp-publishing-house-skills` to your shell alias or Claude Code config so you don't need to pass it every time.

## Start a New Project

### 1. Create a project repo from the template

```bash
gh repo create my-new-lab \
  --template rhpds/rhdp-publishing-house-template \
  --private --clone
cd my-new-lab
```

### 2. Start the orchestrator

From inside your project repo (or anywhere — see note below):

```
/rhdp-publishing-house
```

The orchestrator finds your project, syncs the repo, and walks you through intake.

> **Works from anywhere.** The orchestrator searches up from your current directory, like `git` does. You can run it from inside any subdirectory of your project, from a workspace root, or from an IDE where the CWD isn't your project. It will find the manifest.

### 3. Answer the intake questions

The intake agent asks what you're building, what it's for, and how you plan to deploy it. If you already have a design doc, Google Doc, or rough outline, hand it over and the agent extracts answers from it instead of asking.

You'll be asked:

- **What are you building?** — name, type (workshop or demo), target audience
- **Deployment mode** — RHDP Published or Self-Published (see below)
- **Showroom and automation repos** — the agent helps you create them if needed
- **Modules** — how many, rough titles, estimated duration
- **Automation** — whether the lab needs infrastructure pre-configured

### 4. Approve the spec

After intake, the agent produces `publishing-house/spec/design.md` and per-module outlines. Review and approve. This is the only hard gate before writing starts.

### 5. Write, automate, edit

From here, the orchestrator guides you. Say what you want to do and it routes to the right agent:

- `"write module 1"` — writer agent generates AsciiDoc from the module outline
- `"build automation"` — automation agent captures requirements, creates the catalog, writes code
- `"edit all"` — editor agent reviews content against Red Hat standards and your spec
- `"what's next"` — status summary from the manifest, no heavy loading

### 6. End the session

Say `"I'm done for today"` or `"session summary"`. The orchestrator writes a worklog entry, commits the manifest and worklog, and pushes. Next session, `git pull` and the worklog happens automatically.

---

## Deployment Modes

Set during intake. Determines the automation path and publishing target.

| Mode | Description | Automation | Published In RHDP? |
|------|-------------|------------|-------------------|
| **RHDP Published** (`rhdp_published`) | Full pipeline. Goes through all review gates, creates its own AgnosticV catalog item. | Ansible, GitOps, or both | Yes — standalone catalog item |
| **Self-Published** (`self_published`) | You manage deployment. Uses the generic Field Source CI (`agd_v2/ocp-field-asset-cnv`). | GitOps only (Helm + ArgoCD) | No — you order the Field Source CI with your repo URL |

You can run the full content pipeline (intake, writing, editing) regardless of mode. The fork is where the output lands, not how the work gets done.

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

Say `"skip writing"`, `"I already have content"`, or `"skip automation"` to jump ahead. The orchestrator confirms before skipping anything.

---

## Collaborating on a Project

The manifest is the source of truth. Push your repo; a colleague runs `/rhdp-publishing-house` and picks up exactly where you left off.

The orchestrator **pulls before reading and pushes after writing** — session start syncs, session end commits. You don't need to remember to do this.

For async handoffs, use the worklog:

```
"leave a note: check with Prakhar on pool sizing before creating the catalog"
"what's outstanding"
"resolve item 2026-04-14-001"
```

The worklog lives in `publishing-house/worklog.yaml` and is committed with every update.

---

## Resuming a Session

Just run `/rhdp-publishing-house` from anywhere in your project. The orchestrator:

1. Finds the manifest (walks up from CWD)
2. Pulls latest changes
3. Reads manifest and worklog
4. Presents current status and open items
5. Asks what you want to do

---

## Tips

- **Invest in module outlines.** The writer agent generates content from `publishing-house/spec/modules/` — the more detailed the outline, the better the output.
- **Human edits are expected.** Edit content, specs, and automation files freely between sessions. All agents read fresh and respect what's there.
- **The worklog is for notes, not tasks.** Manifest tracks phases; worklog tracks decisions, handoffs, and context that doesn't fit in structured fields.
- **RCARS not available?** Skip vetting and come back to it later — it's optional.
- **Automation testing gate.** After the automation agent writes code, you deploy it yourself. Tell the agent `"testing done"` when you've verified it works on a real environment.
