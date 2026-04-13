# How It Works

## Architecture: Hub + Spoke

RHDP Publishing House uses a Hub + Spoke plugin architecture. A thin orchestrator (hub) manages project state and dispatches specialized agent skills (spokes) for each lifecycle phase.

```
/rhdp-publishing-house [supervised|semi|full]
         |
    Orchestrator (reads manifest, determines phase, dispatches)
         |
    +----+----+--------+----------+---------+--------+
    |         |        |          |         |        |
 Intake    Writer   Editor   Automation  Security  Review
    |         |        |          |
  RCARS    showroom  showroom  agnosticv
  API      :create-  :verify-  :catalog-
           lab/demo  content   builder
```

Each agent is a separate skill file -- focused, testable, independently iterable. Adding a new phase means adding a new spoke, not rewriting a monolith.

## Content Lifecycle

```
Intake* --> Vetting --> Spec Refinement --> [Approval*] --> Writing --> Editing*
  --> Automation (Catalog Item --> Requirements --> Code --> Testing)
  --> Security Review* --> Final Review* --> Ready for Publishing

* = required    (unmarked = optional, skip if handled another way)
```

### Required Phases

| Phase | Agent | What It Does |
|-------|-------|-------------|
| **Intake** | Intake Agent (Opus) | Generates or ingests the project spec and module outlines. Shortcuttable with a pre-existing design doc. |
| **Approval** | Human | Owner reviews and approves the spec. Hard gate -- never auto-advanced. |
| **Technical Editing** | Editor Agent (Sonnet) | Wraps `showroom:verify-content` + spec alignment checks. Quality gate regardless of how content was produced. |
| **Security Review** | Security Agent (Sonnet) | Content-level security audit. Checks for exposed credentials, hardcoded URLs, sensitive data. |
| **Final Review** | Review Agent (Sonnet) | Holistic check: spec alignment, completeness, cross-module consistency. |

### Optional Phases

| Phase | Agent | What It Does | Skip If... |
|-------|-------|-------------|------------|
| **Vetting** | Intake Agent | Checks against existing RHDP content via RCARS API | RCARS unavailable or uniqueness already validated |
| **Spec Refinement** | Intake Agent | Cleans up spec for downstream agent consumption | Spec is already clean and detailed |
| **Writing** | Writer Agent (Sonnet) | Wraps `showroom:create-lab` / `showroom:create-demo` to generate AsciiDoc | Content was written manually or with another tool |
| **Automation** | Automation Agent (Opus) | Creates AgnosticV catalog, generates automation requirements, writes code, and includes a testing gate | Environment setup handled externally |

## The Agents

### Orchestrator

The entry point. Reads the project manifest, presents current state, recommends the next action, and dispatches agent skills. Does not perform work itself -- purely state management and routing.

- **Model:** Opus 4.6
- **Invoked by:** `/rhdp-publishing-house [supervised|semi|full]`

### Intake Agent

Handles the first three phases: intake, vetting, and spec refinement.

- **Model:** Opus 4.6
- **Three entry paths:**
  1. **Full spec provided** -- experienced content dev brings a detailed spec, agent validates and fills gaps
  2. **Rough idea** -- "I need a lab on ServiceMesh." Agent builds the spec through conversation
  3. **RCARS gap** -- a single sentence gap description becomes the seed for a new project
- **Produces:** `publishing-house/spec/design.md` + per-module outlines in `publishing-house/spec/modules/`

### Writer Agent

Generates Showroom AsciiDoc content from approved module outlines.

- **Model:** Sonnet 4.6
- **Wraps:** `showroom:create-lab` (workshops) and `showroom:create-demo` (demos)
- **Works module-by-module** -- owner triggers which module to write
- **Respects human edits** -- if content was modified manually, builds on what exists
- **Produces:** AsciiDoc files in `content/`

### Editor Agent

Reviews content quality and spec alignment.

- **Model:** Sonnet 4.6
- **Wraps:** `showroom:verify-content` + Publishing House spec alignment checks
- **Checks:** AsciiDoc quality, Red Hat style, outline coverage, learning objectives, duration alignment, cross-module consistency, product names, version consistency
- **Produces:** Review reports in `publishing-house/reviews/`, direct edits to content
- **Fix loop:** Presents issues by severity, offers interactive or automated fixes

### Automation Agent

Creates AgnosticV catalog configuration and environment automation.

- **Model:** Opus 4.6
- **Five sub-phases:**
  - **7a: Catalog Item** -- wraps `agnosticv:catalog-builder` and `agnosticv:validator`
  - **7b: Automation Requirements** -- analyzes content to produce a reviewable automation manifest
  - **7c: Automation Code** -- writes Ansible collections or GitOps repos from approved requirements, runs its own code review cycle
  - **7d: Testing** -- human gate: deploy and verify the automation works on a real environment
  - **7e: E2E Checks** -- end-to-end validation *(deferred)*
- **Determines infrastructure type** (OCP, RHEL/VMs, Sandbox) from the design spec
- **Produces:** AgnosticV config + automation code in `automation/`

### Code & Security Review Agent *(not yet implemented)*

Code review of automation artifacts and security audit of both content and automation.

- **Checks:** Credentials in docs, hardcoded URLs, sensitive info in public-facing content, automation code quality
- **Produces:** `publishing-house/reviews/code-security-review.md`

### Final Review Agent *(not yet implemented)*

Holistic final check before marking ready for publishing.

- **Checks:** Spec alignment, completeness, cross-module consistency, all prior review items addressed
- **Produces:** Final review report

## Dashboard

The [RHDP Publishing House Dashboard](https://github.com/rhpds/rhdp-publishing-house-dashboard) provides cross-project visibility for managers and PMs. It reads `manifest.yaml` from each registered project's GitHub repo and presents:

- **Pipeline kanban** — projects flowing through lifecycle phases
- **Projects table** — searchable list with phase progress bars
- **Project detail** — phase accordions with dates, assignees, artifacts linked to GitHub

The dashboard is read-only — it never modifies the manifest. All state changes happen through the CLI skills.

See [docs/dashboard.md](dashboard.md) for full details.

## State Management

All project state lives in `publishing-house/manifest.yaml` -- a structured YAML file that the orchestrator reads and writes every session. It tracks:

- Project metadata (name, type, owner, autonomy level)
- Current lifecycle phase
- Status of every phase and sub-phase
- Module-level progress (pending, in_progress, drafted, approved)
- Artifact paths (specs, content files, review reports)
- Integration URLs (RCARS, Showroom repo, automation repo)

The manifest is the single source of truth. It enables collaboration without external coordination tools -- push your repo, a colleague picks up exactly where you left off.

## Autonomy Levels

Control how much review you want at each step:

| Level | Behavior |
|-------|----------|
| **supervised** (default) | Agent presents every artifact for approval before committing |
| **semi** | Agent commits to WIP branch, pauses at phase gates and decision points only |
| **full** | Agent works through entire phase, presents output at phase gate for review |

Switch mid-session by saying "switch to semi" or re-invoking with a different level.

## Existing Skills Reused

Publishing House wraps existing RHDP marketplace skills rather than reinventing them:

| Skill | Used By | Phase |
|-------|---------|-------|
| `showroom:create-lab` | Writer Agent | Writing |
| `showroom:create-demo` | Writer Agent | Writing |
| `showroom:verify-content` | Editor Agent | Technical Editing |
| `agnosticv:catalog-builder` | Automation Agent | Catalog Item (7a) |
| `agnosticv:validator` | Automation Agent | Catalog Item (7a) |
| `code-review:code-review` | Automation Agent | Automation Code (7c) |

## Project Template

New projects start from a GitHub template repo (`rhpds/rhdp-publishing-house-template`) that provides:

```
my-new-lab/
├── publishing-house/
│   ├── manifest.yaml                    # Pre-populated with empty phases
│   ├── journal.md                       # Work journal (experimental)
│   ├── spec/
│   │   ├── design.md                    # Master design spec
│   │   ├── modules/                     # Per-module outlines
│   │   └── automation-manifest.yaml     # Automation requirements (reviewable)
│   ├── reviews/                         # Agent review artifacts
│   └── decisions/                       # Decision records
├── content/                             # Showroom AsciiDoc (writer agent output)
├── automation/                          # Ansible/Helm (automation agent output)
└── CLAUDE.md                            # Points to manifest
```
