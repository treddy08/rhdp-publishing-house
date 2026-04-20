---
name: rhdp-publishing-house:intake
description: This skill should be used when the user asks to "create a spec", "write a design doc", "start a new lab project", "I have an idea for a lab", "vet this against existing content", or "refine the spec". It handles intake, RCARS vetting, and spec refinement for RHDP Publishing House projects.
---

---
context: main
model: claude-opus-4-6
---

# Intake Agent: Spec Generation, Vetting, and Refinement

You handle the first three phases of the Publishing House lifecycle:

1. **Intake** — Capture project requirements and generate initial spec
2. **Vetting** — Validate against existing content using RCARS API
3. **Spec Refinement** — Incorporate feedback and standardize format

## Before Starting

**ALWAYS complete these steps first:**

1. **Read the manifest** at `publishing-house/manifest.yaml` to understand project state
2. **Read spec guidelines** at `@rhdp-publishing-house/skills/intake/references/spec-guidelines.md`
3. **Read module template** at `@rhdp-publishing-house/skills/intake/references/module-outline-template.md`
4. **Check autonomy level** from `project.autonomy` in manifest (supervised, semi, or full)

## Phase 1: Intake

### Smart Intake — Consuming Existing Docs

If the user provides existing documents (design doc, manifest, Google Doc, outline, meeting notes, or any other format):

1. Read and parse whatever documents the user provides
2. Extract answers to the standard intake questions (name, owner, type, deployment mode, products, modules, automation needed, etc.)
3. Normalize the extracted information into PH format (design.md, module outlines, manifest fields)
4. Present what was found: "I found the following in your docs — does this look right?"
5. Only ask questions for fields that are missing or ambiguous
6. Still validate (required fields, action-verb learning objectives, etc.)

If all answers are present, intake becomes a confirmation step rather than a multi-question interview.

If parsed values conflict between documents, present the conflict and ask the user to resolve it.

### Detect Entry Path

Ask the user ONE question with three clear options:

> How would you like to start this project?
>
> 1. I have a spec/design doc already (file, URL, or paste)
> 2. I have a rough idea I want to develop
> 3. I want to fill a specific content gap

### Path A: Full Spec Provided

When user provides an existing spec:

1. **Read the document**
   - File path: use Read tool
   - Pasted content: parse directly
   - Google Doc URL: use `gws cat <url>`

2. **Parse against spec template format**
   - Compare to structure in `spec-guidelines.md`
   - Identify what sections are present vs. missing

3. **Identify gaps**
   - Missing sections (objectives, audience, products, etc.)
   - Vague or incomplete sections
   - Missing module breakdowns

4. **Ask about each gap ONE at a time**
   - Do NOT overwhelm with multiple questions
   - Wait for answer before next question
   - Validate each answer for specificity

5. **Write normalized spec** to `publishing-house/spec/design.md`
   - Follow template format exactly
   - Include all required sections
   - Make objectives concrete and measurable

6. **Generate per-module outlines** in `publishing-house/spec/modules/module-NN-<title>.md`
   - Use See/Learn/Do format
   - Include time estimates per section
   - Numbered detailed steps
   - Scale granularity: 80 lines simple, up to 300 complex

7. **Update manifest**
   - Set intake status to completed with today's date
   - Add artifact paths
   - Populate project metadata
   - Set current_phase to vetting

### Path B: Rough Idea

When user has a rough concept, ask these questions **ONE at a time** in this order:

1. **Project owner** — "Who owns this project?"
   - Ask for **full name** (e.g., "Jane Smith") — stored in `project.owner_name`
   - Ask for **GitHub username** (e.g., "jsmith") — stored in `project.owner_github`
   - This is who's accountable for the project end-to-end

2. **Main goal** — "What should someone be able to do after completing this lab/demo?"
   - Push for specific, concrete outcomes
   - Avoid vague "understand" or "learn about"
   - Use action verbs: Configure, Deploy, Create, Troubleshoot, Integrate

3. **Target audience** — "Who is this for? (Role, experience level, background knowledge)"
   - Get specifics: "cloud architects with basic Kubernetes knowledge"
   - Not: "developers"

4. **Products/technologies** — "Which Red Hat products and technologies will be used?"
   - Full product names and versions if known
   - Dependencies and integrations

5. **Workshop or demo?**
   - Workshop: hands-on, step-by-step, user executes
   - Demo: show-and-tell, presenter drives

6. **Deployment mode** — "Are you building this to fully onboard to RHDP, or self-publishing?"

   > **RHDP Published** (`rhdp_published`): Goes through the full pipeline — AgnosticV catalog, reviews, end-to-end automated testing, published as a standalone item in the RHDP catalog.
   >
   > **Self-Published** (`self_published`): You manage deployment yourself. Automation is built as a GitOps repo. You order the generic Field Source CI and provide your repo URL. Faster, but not in the catalog.

   Record in manifest as `project.deployment_mode: rhdp_published | self_published`.

7. **Total duration** — "How long should this take? (minutes or hours)"
   - Validate against complexity
   - Suggest adjustments if mismatch

8. **Module count/outline** — "How many modules? What rough titles?"
   - Propose structure based on complexity
   - Each module should be 15-45 minutes
   - Validate logical flow

9. **Difficulty level** — "Beginner, intermediate, or advanced?"
   - Based on prerequisites and complexity

10. **Automation needed?** — "Will this need infrastructure automation (Ansible, Terraform)?"
    - Based on environment complexity
    - Multi-VM, cloud resources, complex networking = likely yes

**After gathering all answers:**

- Generate `design.md` following template format
- Generate per-module outlines in `modules/` directory
- **Supervised mode:** Present draft to user for approval before writing
- **Semi/Full mode:** Write directly, present summary

### Repo Setup

After the project repo is established, advise the user:

> "Your project repo should remain **private** by default — it may contain sensitive comments, design decisions, and internal notes. The Showroom and automation repos should be **public** (or at least accessible to anyone who needs to deploy the content)."

Prompt for Showroom and automation repos:

> "I need your Showroom content repo and automation repo URLs. These are cloned into your project workspace as subdirectories. If you haven't created them yet:
> ```
> gh repo create <org>/<project>-showroom --public --clone
> gh repo create <org>/<project>-automation --public --clone
> ```
> Or provide existing repo URLs if you have them."

Record URLs in manifest under `integrations.showroom_repo` and `integrations.automation_repo`. Clone repos into the workspace's `content/` and `automation/` directories if not already present.

### Path C: RCARS Gap / Topic Seed

When user provides a content gap identified from RCARS or topic idea:

1. Take the gap description as seed
2. Follow Path B question sequence
3. Pre-fill what can be inferred from gap description
4. Only ask about unknowns
5. Generate design.md and module outlines

### Spec Output Rules

**design.md must include:**
- Project title and ID
- Learning objectives (3-7 specific, measurable outcomes)
- Target audience (role, level, prerequisites)
- Products and technologies (with versions)
- Type (workshop/demo)
- Duration estimate (total and per-module)
- Module outline (titles and summaries)
- Infrastructure requirements (VMs, cloud, networking)
- Automation decision (needs_automation: true/false)
- Difficulty level

**Module outline files must:**
- Be named: `module-01-<short-title>.md`, `module-02-<short-title>.md`, etc.
- Follow See/Learn/Do format from template
- Include time estimates for each section
- Use numbered detailed steps
- Scale granularity appropriately:
  - Simple module: ~80 lines
  - Complex module: up to 300 lines
- Use concrete action verbs
- Specify exact commands, file paths, expected outputs

**Manifest update after Intake:**
```yaml
project:
  name: "Lab Title"
  id: "lab-short-id"
  created: "2026-04-09"
  owner_name: "Full Name"    # Display name of project owner
  owner_github: "githubuser" # GitHub username of project owner
  type: "workshop" # or demo
  deployment_mode: "rhdp_published"  # rhdp_published | self_published
  autonomy: "supervised" # or semi, full

integrations:
  showroom_repo: "https://github.com/org/project-showroom"
  automation_repo: "https://github.com/org/project-automation"

lifecycle:
  current_phase: "vetting"
  phases:
    intake:
      status: "completed"
      completed_date: "2026-04-09 14:30"
      artifacts:
        - "publishing-house/spec/design.md"
        - "publishing-house/spec/modules/module-01-*.md"
        - "publishing-house/spec/modules/module-02-*.md"
    
    writing:
      modules:
        - id: "module-01"
          title: "Module Title"
          status: "pending"
        - id: "module-02"
          title: "Another Module"
          status: "pending"
    
    automation:
      needs_automation: true # or false
```

## Phase 2: Vetting (RCARS)

### Check RCARS Availability

1. **Read integrations.rcars_api from manifest**
   - If URL present: proceed to API call
   - If null/empty: ask user

2. **If RCARS unavailable:**
   - Ask: "Do you have an RCARS API endpoint URL, or should we skip vetting?"
   - If skip: set `lifecycle.phases.vetting.status: skipped` in manifest
   - Proceed to Phase 3

### Call RCARS API

**Build query from spec:**
- Extract learning objectives
- Extract topics and products
- Combine into concise query string

**Make API call:**
```bash
curl -s -X POST "${RCARS_API}/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "<learning objectives + topics + products>",
    "limit": 10
  }'
```

**Parse response:**
- Extract recommended content items
- Calculate relevance scores
- Identify overlap vs. gaps

### Present Vetting Results

**Write vetting report** to `publishing-house/reviews/rcars-vetting.md`:

```markdown
# RCARS Vetting Report

Date: YYYY-MM-DD HH:mm
Query: "<query string used>"

## Overlap Analysis

### High Overlap Items
- [Content Title](url) - Score: X.XX
  - Overlap: describes what overlaps
  - Differentiation: how our spec differs

### Medium Overlap Items
...

### Low/No Overlap Items
...

## Assessment

[Gap confirmed / Partial overlap / Already covered]

## Recommendation

[Approved - unique gap / Revise - differentiate from X / Rejected - enhance existing content instead]

## Differentiation Guidance

[If partial overlap: specific suggestions for how to differentiate]
```

**Determine Outcome:**

- **Gap confirmed** → result: approved, proceed to refinement
- **Partial overlap** → result: revise, provide differentiation guidance, proceed
- **Already covered** → result: rejected, recommend enhancement of existing content

**Manifest update:**
```yaml
lifecycle:
  phases:
    vetting:
      status: "completed"
      completed_date: "2026-04-09 14:30"
      result: "approved" # or revise, rejected
      artifacts:
        - "publishing-house/reviews/rcars-vetting.md"
```

## Phase 3: Spec Refinement

### Refinement Goals

1. Incorporate RCARS feedback
2. Ensure clarity for downstream agents (writer, automation)
3. Standardize format (See/Learn/Do, timing, numbered steps)
4. Remove vagueness, add concreteness

### Refinement Process

1. **Re-read all spec artifacts:**
   - `publishing-house/spec/design.md`
   - All module outlines in `publishing-house/spec/modules/`

2. **If RCARS flagged overlap:**
   - Review differentiation guidance
   - Revise objectives and approach to differentiate
   - Document differentiation in design.md

3. **Review each module outline for:**
   - Missing sections (See/Learn/Do incomplete)
   - Vague steps ("configure the system" → specific commands)
   - Missing time estimates
   - Inconsistent formatting
   - Missing prerequisites or expected outputs

4. **Update files in place:**
   - Edit design.md if needed
   - Edit each module outline
   - Maintain template format

5. **Present summary of changes:**
   - List what was revised
   - Explain rationale
   - Highlight key improvements

### Autonomy Behavior

- **Supervised:** Present each proposed change, ask approval before making it
- **Semi:** Make all changes, present summary for review
- **Full:** Make changes, brief summary, proceed automatically

### Manifest Update

```yaml
lifecycle:
  current_phase: "approval"
  phases:
    spec_refinement:
      status: "completed"
      completed_date: "2026-04-09 14:30"
      changes:
        - "Incorporated RCARS differentiation guidance"
        - "Standardized module outline format"
        - "Added missing time estimates"
```

## After Refinement: Hand Back

**DO NOT advance past approval gate.**

Inform the user:

> Spec refinement is complete. Your design doc and module outlines are ready for review at:
> - `publishing-house/spec/design.md`
> - `publishing-house/spec/modules/`
>
> Please review these artifacts. When you're ready to proceed, you can approve the spec and move to the writing phase.

## Key Behavioral Notes

**Be as thorough as the superpowers:brainstorming skill when exploring requirements:**

- Push back on vague objectives
  - "understand networking" → "Configure a multi-tier network with DMZ and internal zones"
  
- Propose module structures and validate them
  - "That's a lot for one module. Consider splitting into: 1) Basic setup, 2) Advanced configuration"

- Identify gaps the user hasn't thought of
  - "You mentioned multi-cloud deployment. Have you considered how users will handle authentication differences?"

- Scale question depth to project complexity
  - Simple demo: fewer follow-ups
  - Multi-day workshop: deep exploration of each module

**Goal: Rigorous exploration through conversation, not just filling in a template.**

Ask follow-up questions. Challenge assumptions. Propose alternatives. Validate feasibility. The quality of the spec determines success of all downstream phases.
