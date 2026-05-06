# Publishing House — Development Worklog

Session notes and handoff context for the PH dev team. Use this to communicate between developers what was done, what's in progress, and what the next person should pick up.

Clear periodically — the backlog ([BACKLOG.md](BACKLOG.md)) is the persistent roadmap.

---

## 2026-05-06 — Documentation overhaul + template restructuring (Nate, pre-PTO)

### Documentation accuracy review
- Cross-referenced all docs/ against actual code in all 4 repos (portal, skills, template, main)
- Fixed 12 files: broken links, wrong parameter types, missing MCP tools, stale branch refs
- Replaced 7 ASCII art diagrams with Mermaid (exec summary, how-it-works, portal, rcars-integration, portal-deployment)
- Added Mermaid custom_fences config to mkdocs.yml
- Updated CLAUDE.md MCP tools table: added 3 missing tools (`ph_get_launch_instructions`, `ph_store_validation_results`, `ph_get_validation_results`)
- Fixed `ph_get_launch_instructions` param type (int → str), advisor poll interval (3s → 10s), `ph_list_projects` return shape
- Removed stale `gsd-project` branch references from portal-deployment.md

### Portal cleanup
- Renamed `_ph_dashboard_oauth` cookie → `_ph_portal_oauth`
- Fixed "from the dashboard" → "from the portal" in delete dialog
- Built and deployed frontend to dev

### Template restructuring
- Embedded Showroom scaffold in PH template (site.yml, ui-config.yml, content/antora.yml, nav.adoc, index.adoc)
- Removed submodule pattern: content/ and automation/ are now regular directories, not separate repos
- Removed `integrations.showroom_repo` and `integrations.automation_repo` from manifest template
- Removed 84 lines of submodule gate logic from orchestrator SKILL.md
- Updated template CLAUDE.md, README.md, .gitignore
- Updated how-it-works.md project template section

### Housekeeping
- Removed `.planning/` directory (replaced by backlog + docs as source of truth)
- Added `.claude/` to .gitignore, restored `.superpowers/`

### Test prompts
- Created 15 intake test prompts in test/ (3 modes × 5 tech areas)
- Mix of direct asks and CFP abstract styles for realistic intake testing

### What's next
- **Test intake end-to-end** using the test prompts against live MCP server
- **Phase 3: Jira integration** — spec done, ready for implementation planning (blocked on Jira SA)
- **Phase 4: Portal chatbot** — needs brainstorm
- **Express skill** — unblocked, needs design
- See [BACKLOG.md](BACKLOG.md) for full roadmap
