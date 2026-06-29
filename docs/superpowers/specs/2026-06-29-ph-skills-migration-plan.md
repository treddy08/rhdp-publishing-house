# PH Skills Migration Plan — Marketplace → Publishing House

**Date:** 2026-06-29  
**Status:** Draft  
**Author:** Prakhar Srivastava  
**Scope:** Step-by-step plan to migrate showroom, agnosticv, and ftl plugins from rhdp-skills-marketplace into rhdp-publishing-house-skills. Covers transition period, backward compatibility, and marketplace cleanup.

---

## Goal

After this migration:
- PH users install ONE repo (`rhdp-publishing-house-skills`) and get all skills
- `rhdp-skills-marketplace` continues to serve `health` and `sandbox-cli` only
- showroom, agnosticv, ftl frozen in marketplace (no new features there)
- All future skill development for these 3 plugins happens in `rhdp-publishing-house-skills`

---

## Pre-Migration Checklist

Before starting:
- [ ] agnosticv v2.15.0 is merged to marketplace main ✅ (done 2026-06-29)
- [ ] showroom v2.14.0 is merged to marketplace main ✅ (done 2026-05-31)
- [ ] ftl current version documented (run `cat ~/work/code/rhdp-skills-marketplace/ftl/.claude-plugin/plugin.json`)
- [ ] Confirm no in-progress PRs against showroom/, agnosticv/, or ftl/ in marketplace
- [ ] PH plugin owner briefed — consolidation changes the repo structure
- [ ] Decide cutover date (suggestion: after current Sprint ends)

---

## Phase 1: Set Up Multi-Plugin Structure

**Branch:** `feature/consolidate-marketplace-plugins`  
**Repo:** `rhdp-publishing-house-skills` (the skills-plugin submodule)

### Step 1.1: Copy showroom plugin

```bash
cd ~/work/code/rhdp-publishing-house/skills-plugin

# Copy showroom plugin directory structure
cp -r ~/work/code/rhdp-skills-marketplace/showroom/ ./showroom/

# Verify the plugin.json name is still "showroom"
cat showroom/.claude-plugin/plugin.json
# Expected: "name": "showroom"
```

### Step 1.2: Copy agnosticv plugin

```bash
cp -r ~/work/code/rhdp-skills-marketplace/agnosticv/ ./agnosticv/

# Verify
cat agnosticv/.claude-plugin/plugin.json
# Expected: "name": "agnosticv"
```

### Step 1.3: Copy ftl plugin

```bash
cp -r ~/work/code/rhdp-skills-marketplace/ftl/ ./ftl/

# Verify
cat ftl/.claude-plugin/plugin.json
# Expected: "name": "ftl"
```

### Step 1.4: Update PH plugin.json with new version

```json
{
  "name": "rhdp-publishing-house",
  "version": "0.2.0",
  "description": "AI-powered content lifecycle management for RHDP — includes showroom, agnosticv, and ftl skill plugins",
  "author": {
    "name": "RHDP Team",
    "url": "https://github.com/rhpds/rhdp-publishing-house"
  },
  "bundledPlugins": [
    "showroom",
    "agnosticv",
    "ftl"
  ]
}
```

Note: `bundledPlugins` is a documentation field only — Claude Code doesn't read it. It's for human reference.

### Step 1.5: Add version gate to PH orchestrator

In `skills/orchestrator/SKILL.md`, add at the very top (before any routing):

```markdown
## Session Start — Plugin Version Check

Before doing anything, verify all required plugins are installed at the correct version.

Find the skills directory (default: the parent of the directory containing this SKILL.md).

Read each plugin's version:
- `<skills-dir>/.claude-plugin/plugin.json` → rhdp-publishing-house version
- `<skills-dir>/showroom/.claude-plugin/plugin.json` → showroom version
- `<skills-dir>/agnosticv/.claude-plugin/plugin.json` → agnosticv version
- `<skills-dir>/ftl/.claude-plugin/plugin.json` → ftl version

Minimum required versions:
- rhdp-publishing-house: 0.2.0
- showroom: 2.14.0
- agnosticv: 2.15.0
- ftl: 2.14.0 (or whatever current version is)

If any plugin is missing or below minimum:
→ Print a clear error: "❌ [plugin name] not found / below minimum version. Update: cd ~/rhdp-publishing-house-skills && git pull"
→ STOP — do not continue the session.

If all plugins are present and at correct versions → continue as normal.
```

### Step 1.6: Update README.md

New install instructions:
```markdown
## Installation

```bash
git clone git@github.com:rhpds/rhdp-publishing-house-skills.git ~/rhdp-publishing-house-skills
```

Add to Claude Code settings (`~/.claude/settings.json`):
```json
{
  "pluginDirectories": ["~/rhdp-publishing-house-skills"]
}
```

This installs 4 plugins in one step: rhdp-publishing-house, showroom, agnosticv, ftl.

**Updating:**
```bash
cd ~/rhdp-publishing-house-skills && git pull
```

## Included Plugins

| Plugin | Skills | Purpose |
|--------|--------|---------|
| rhdp-publishing-house | orchestrator, intake, writer, editor, automation, worklog | PH content lifecycle |
| showroom | create-lab, create-demo, verify-content, blog-generate | Showroom content authoring |
| agnosticv | catalog-builder, validator | AgnosticV catalog management |
| ftl | content-reader, solve-writer, validate-writer, rhdp-lab-validator | FTL E2E automation |
```

### Step 1.7: Verify all 4 plugins load

Test locally:
```bash
# Start Claude Code with the new combined plugin dir
claude --plugin-dir ~/work/code/rhdp-publishing-house/skills-plugin

# Verify all expected skills are available:
# /rhdp-publishing-house
# /rhdp-publishing-house:intake
# /showroom:create-lab
# /showroom:verify-content
# /agnosticv:catalog-builder
# /agnosticv:validator
# /ftl:content-reader
# etc.
```

---

## Phase 2: PR and Review

**PR target:** `rhdp-publishing-house-skills` repo (the published skills repo)  
**PR title:** `[RHDPCD-120] Consolidate showroom + agnosticv + ftl into PH skills plugin (v0.2.0)`

PR description should:
- Explain the multi-plugin architecture
- List all new directories added
- Confirm skill names unchanged (backward compatible)
- Include test evidence (Phase 1 Step 1.7 output)

Reviewers:
- PH platform owner — PH plugin structure review
- AgnosticV skill domain reviewer — agnosticv skills review

---

## Phase 3: Cutover Communication

After PR merges to main:

### User communication (Slack + README)
```
📢 Publishing House skills update

rhdp-publishing-house-skills now includes showroom, agnosticv, and ftl plugins.
You no longer need a separate rhdp-skills-marketplace install for PH.

If you have BOTH installed, remove rhdp-skills-marketplace from your
Claude Code pluginDirectories to avoid plugin name conflicts.

Update your install:
  cd ~/rhdp-publishing-house-skills && git pull
```

### What users need to do
1. Pull the latest `rhdp-publishing-house-skills` → `git pull`
2. Remove `rhdp-skills-marketplace` from their Claude Code `pluginDirectories` (REQUIRED to avoid plugin name conflicts — two `showroom` plugins = undefined behavior)
3. Test: run `/rhdp-publishing-house` and verify session starts without version gate errors

### What stays the same
- Skill call syntax unchanged: `showroom:create-lab`, `agnosticv:catalog-builder`, etc.
- All existing PH projects continue to work
- PH manifest, MCP tools, portal — all unchanged

---

## Phase 4: Freeze Marketplace Plugins

After cutover is confirmed stable (suggest: 2 weeks after Phase 3):

### In rhdp-skills-marketplace:
1. Add deprecation notice to `showroom/README.md`, `agnosticv/README.md`, `ftl/README.md`:
   ```
   ⚠️  This plugin has moved to rhdp-publishing-house-skills.
   No new features will be added here. See: github.com/rhpds/rhdp-publishing-house-skills
   ```

2. Pin versions in marketplace (no further bumps to these plugins):
   - showroom: frozen at v2.14.x
   - agnosticv: frozen at v2.15.x
   - ftl: frozen at current version

3. Marketplace `README.md` updated to redirect PH users to `rhdp-publishing-house-skills`

4. Marketplace `install.sh` updated to warn PH users

### What stays in marketplace (active, not frozen):
- `health/` plugin
- `sandbox-cli/` plugin

---

## Phase 5: Future FTL Alignment

FTL is moved in this migration but its role in PH is evolving:
- Today: FTL writes solve.yml/validate.yml (automation phase 7c)
- Graphify showed: no direct PH→FTL edges yet (FTL runs on content PH produces, not called by PH skills directly)
- Future: When PH automation skill starts directly invoking `ftl:rhdp-lab-validator`, the call path will be in-repo and version-safe

Track this as a separate spec once PH automation phase 7c→7d integration is designed.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| User has both marketplace + PH installed → plugin name conflict | High | Medium | Clear docs + orchestrator warning at session start |
| PR reviewer requests structural changes mid-migration | Medium | Medium | Pre-align with PH platform owner before opening PR |
| FTL plugin has undocumented dependencies on marketplace infra | Low | Medium | Read ftl plugin.json and SKILL.md before copying |
| agnosticv PRs now go to a different repo | Medium | Low | Update CODEOWNERS, brief domain reviewers |
| Claude Code plugin resolution order is different when same-named plugins in sub-dirs | Low | High | Test Phase 1 Step 1.7 carefully before any cutover |

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Plugin names may be renamed (Option B) — decided during consolidation PR | Renaming during consolidation is atomic and low-cost; doing it later requires a second migration event |
| If renaming: ALL call sites in PH SKILL.md must update in same commit | Partial rename causes broken installs mid-pull |
| Multi-plugin package in one repo (not monorepo) | Simpler than maintaining separate repos; one `git pull` updates all |
| Each plugin keeps its own `.claude-plugin/plugin.json` in its subdir | Claude Code discovers plugins by scanning pluginDirectories for plugin.json files — each subdir registers independently |
| Well-known clone path `~/rhdp-publishing-house-skills` | Simplifies version gate path detection; revisit if users report issues |
| Do NOT auto-update during session | Mid-session skill updates could cause inconsistent pipeline behavior |
| health + sandbox-cli stay in marketplace | Not PH-dependent; would add noise to PH repo |
| FTL included — all three (showroom + agnosticv + ftl) move to PH | FTL will integrate with PH automation in future; consolidate now for single install |
| Graphify confirmed: FTL has no direct PH→FTL call edges today | FTL operates on content PH produces (AsciiDoc), not called by PH skills directly — inclusion is forward-looking |
| agnosticv v2.15.0 is the baseline for PH — ph_payload headless mode required | agnosticv:catalog-builder and agnosticv:validator must support ph_payload for PH automation phase 7b |
| Version gate in orchestrator SKILL.md checks all 4 plugins at session start | Prevents silent failures from version skew; surfaces actionable `git pull` instruction |
