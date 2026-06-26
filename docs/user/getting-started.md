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

### 3. Connect to the Publishing House MCP server

The MCP server gives Claude Code access to RCARS content advisory, session continuity, project tracking, and express mode tools. You need an API key from a PH admin.

Add the PH MCP server to your Claude Code global config (`~/.claude.json`). Add the `publishing-house` entry to the `mcpServers` block (create the block if it doesn't exist -- this is the same file where other MCP servers like GitHub and context7 are configured):

```json
{
  "mcpServers": {
    "publishing-house": {
      "type": "http",
      "url": "https://ph-mcp.apps.<cluster-domain>/mcp/",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

Replace:
- `<cluster-domain>` with the OpenShift cluster apps domain (ask your admin for the exact URL)
- `<your-api-key>` with the raw API key provided by your admin

Restart Claude Code after saving. The PH MCP tools will be available in every session automatically.

**Verify the connection:** After restarting, Claude Code should show `publishing-house` as an available MCP server. Test by asking Claude: "List PH projects" -- if the connection is working, you will see a list of projects (or an empty list if none exist yet).

> **Troubleshooting:**
>
> - **"Connection refused"** -- Verify the URL matches `https://ph-mcp.apps.<cluster-domain>/mcp/`. Check with your admin that the backend is deployed and the route is active. VPN may be required.
> - **401 "Authentication required"** -- Verify the `headers` block exists with `"Authorization": "Bearer <your-api-key>"`. Ensure `type` is `"http"` (not `"sse"` or `"stdio"`).
> - **Invalid key** -- Your API key may have been rotated. Contact your PH admin for a new one.
> - **Tool not found** -- Restart Claude Code and check that `publishing-house` appears in the MCP server list. Verify your config is valid JSON.
> - **"RCARS unavailable"** -- The RCARS service is temporarily down. The intake skill can proceed without vetting -- it will offer to skip the check.

### 4. Create your project repo from the template

**Option A -- GitHub web UI (no extra tools required):**

1. Go to `https://github.com/rhpds/rhdp-publishing-house-template`
2. Click **Use this template -> Create a new repository**
3. Set it to **Private**, give it a name, and create it
4. Clone it:
   ```bash
   git clone git@github.com:your-org/your-repo.git
   cd your-repo
   ```

**Option B -- `gh` CLI:**

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

### 5. Answer the intake questions

The intake agent asks what you're building, what it's for, and how you plan to deploy it. If you already have a design doc, Google Doc, or rough outline, provide it and the agent extracts answers from it instead of asking every question.

You'll cover:

- **What are you building?** -- name, type (workshop or demo), target audience
- **Deployment mode** -- RHDP Published, Self-Published, or Express (see [Deployment Modes](deployment-modes.md))
- **Modules** -- how many, rough titles, estimated duration
- **Automation** -- whether the lab needs infrastructure pre-configured

### 6. Approve the spec

After intake, the agent produces `publishing-house/spec/design.md` and per-module outlines. Review and approve. This is the only hard gate before writing starts.

### 7. Write, automate, edit

From here, the orchestrator guides you. Say what you want to do and it routes to the right agent:

- `"write module 1"` -- writer agent generates AsciiDoc from the module outline
- `"build automation"` -- automation agent captures requirements, creates the catalog, writes code
- `"edit all"` -- editor agent reviews content against Red Hat standards and your spec
- `"what's next"` -- lightweight status summary, no heavy loading

### 8. End the session

Say `"I'm done for today"` or `"session summary"`. The orchestrator writes a worklog entry, commits the manifest and worklog, and pushes. Next session, the pull happens automatically.

---

## Deployment Modes

Set during intake. Determines the automation path and publishing target. See the full [Deployment Modes](deployment-modes.md) guide for details.

| Mode | Description | Automation | Published In RHDP? |
|------|-------------|------------|-------------------|
| **RHDP Published** (`onboarded`) | Full pipeline. Review gates, AgnosticV catalog, published as a standalone item. | Ansible, GitOps, or both | Yes |
| **Self-Published** (`self_published`) | You manage deployment. Uses the generic Field Source CI with your GitOps repo URL. | GitOps only (Helm + ArgoCD) | No |
| **Express** (`express`) | Fast path for one-off demo environments. No git repo, no review gates. See [Deployment Modes](deployment-modes.md). | Live cluster customization | No |

The content pipeline (intake, writing, editing) is the same for onboarded and self-published modes. Express mode is a separate fast path -- it runs through intake, identifies a base CI from the RCARS catalog, and then gates on environment provisioning. See [Deployment Modes](deployment-modes.md) for the full lifecycle.

---

## Autonomy Levels

Control how much review you want at each step:

```
/rhdp-publishing-house              # guided (default) -- review everything
/rhdp-publishing-house assisted     # review at phase gates only
/rhdp-publishing-house autonomous   # review at phase completion
```

Switch any time mid-session: `"switch to assisted"`

---

## Required vs. Optional Phases

**Required** (cannot be skipped):
- **Intake** -- shortcuttable with a pre-existing spec, but always runs
- **Approval** -- you review and sign off on the spec; never auto-advanced
- **Technical Editing** -- runs regardless of how content was produced
- **Code & Security Review** -- required for `rhdp_published`; recommended for `self_published`
- **Final Review** -- holistic check before marking ready

**Optional** (skip if handled another way):
- **Vetting** -- check against existing RHDP content via RCARS
- **Spec Refinement** -- clean up spec before writing starts
- **Writing** -- skip if you wrote content manually
- **Automation** -- skip if environment setup is handled externally

Say `"skip writing"`, `"I already have content"`, or `"skip automation"` to jump ahead.

---

## Collaborating on a Project

The manifest is the source of truth. Push your repo; a colleague runs `/rhdp-publishing-house` and picks up exactly where you left off.

The orchestrator **pulls at session start and pushes at session end** -- you don't need to manage this manually.

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

- **Invest in module outlines.** The writer agent generates content from `publishing-house/spec/modules/` -- the more detailed the outline, the better the output.
- **Human edits are expected.** Edit content, specs, and automation files freely between sessions. All agents read fresh and respect what's there.
- **The worklog is for notes, not tasks.** Manifest tracks phases; worklog tracks decisions, handoffs, and context that doesn't fit in structured fields.
- **RCARS not available?** Skip vetting and come back to it later -- it's optional.
- **Automation testing gate.** After the automation agent writes code, you deploy it yourself and confirm with `"testing done"`.

---

## Related Documentation

- [Overview](../overview.md) -- How Publishing House works end-to-end
- [Deployment Modes](deployment-modes.md) -- Full details on onboarded, self-published, and express modes
- [Central Backend](../architecture/central.md) -- MCP tool reference and gate service details
- [MCP Auth Setup](../admin/mcp-auth.md) -- Admin guide for managing API keys
