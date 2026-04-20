# Getting Started

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- A GitHub account with access to the `rhpds` org

## Install the Plugin

Clone the skills repo and point Claude Code at it. You only do this once.

```bash
git clone git@github.com:rhpds/rhdp-publishing-house-skills.git ~/rhdp-publishing-house-skills
```

Then start Claude Code with the plugin:

```bash
claude --plugin-dir ~/rhdp-publishing-house-skills
```

> **Tip:** Add `--plugin-dir ~/rhdp-publishing-house-skills` to your shell alias or Claude Code settings so you don't need the flag every time.

---

## Start a New Project

### 1. Start the orchestrator

Run this from anywhere — your home directory, a workspace, an IDE terminal:

```
/rhdp-publishing-house
```

The orchestrator will ask what you're building and give you the commands to set up a project repo. Follow those instructions, then come back and run `/rhdp-publishing-house` again once you're in the repo.

### 2. Create the project repo from the template

**Option A — GitHub web UI (recommended, no extra tools required):**

1. Go to `https://github.com/rhpds/rhdp-publishing-house-template`
2. Click **Use this template → Create a new repository**
3. Set it to **Private**, give it a name, create it
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

### 3. Run the orchestrator inside your project

```
/rhdp-publishing-house
```

The orchestrator finds the manifest, syncs the repo, and starts intake.

> **Works from anywhere.** The orchestrator walks up from your current directory like `git` does — you don't need to `cd` into the project root. It works from any subdirectory, a workspace root, or an IDE where the CWD isn't your project.

### 4. Answer the intake questions

The intake agent asks what you're building, what it's for, and how you plan to deploy it. If you already have a design doc, Google Doc, or rough outline, provide it and the agent extracts answers from it instead of asking every question.

You'll cover:

- **What are you building?** — name, type (workshop or demo), target audience
- **Deployment mode** — RHDP Published or Self-Published (see below)
- **Showroom and automation repos** — the agent helps you create them if needed
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
| **RHDP Published** (`rhdp_published`) | Full pipeline. Review gates, AgnosticV catalog, published as a standalone item. | Ansible, GitOps, or both | Yes |
| **Self-Published** (`self_published`) | You manage deployment. Uses the generic Field Source CI with your GitOps repo URL. | GitOps only (Helm + ArgoCD) | No |

The content pipeline (intake, writing, editing) is the same for both modes. The fork is where the output lands.

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

Run `/rhdp-publishing-house` from anywhere. The orchestrator:

1. Finds the manifest (walks up from CWD)
2. Pulls latest changes
3. Reads manifest and worklog
4. Presents current status and open items
5. Asks what you want to do next

---

## Tips

- **Invest in module outlines.** The writer agent generates content from `publishing-house/spec/modules/` — the more detailed the outline, the better the output.
- **Human edits are expected.** Edit content, specs, and automation files freely between sessions. All agents read fresh and respect what's there.
- **The worklog is for notes, not tasks.** Manifest tracks phases; worklog tracks decisions, handoffs, and context that doesn't fit in structured fields.
- **RCARS not available?** Skip vetting and come back to it later — it's optional.
- **Automation testing gate.** After the automation agent writes code, you deploy it yourself and confirm with `"testing done"`.
