# Express Mode

## The Problem

Not every demo need justifies building a full lab. A field associate who needs a working demo environment for a customer meeting next Thursday shouldn't have to create a multi-module Showroom lab with GitOps automation, review gates, and a publishing pipeline. Today, the options are: order something off the shelf that's close but not quite right, or manually build an environment from scratch with no documentation, no reuse, and no visibility into what was built.

Express mode fills the gap between those two extremes.

## What Express Mode Is

Express mode is a fast path for one-off, disposable demo environments. Someone describes what they need, the system finds the closest existing infrastructure in the RHDP catalog to use as a starting point, provisions it, and then an AI agent customizes the live environment — installing operators, deploying apps, scaffolding demo artifacts — until it matches the requirements. The output is a working environment and a recap document, not a publishable lab.

**Key characteristics:**

- **No git repo, no stored automation, no review gates.** The customization work is throwaway by design.
- **Hours to days, not weeks.** The standard PH pipeline produces polished, permanent catalog items. Express trades durability for speed.
- **Builds on what exists.** RCARS searches the catalog for the closest base infrastructure, so the agent starts from a provisioned cluster with relevant operators already installed — not a blank slate.
- **Everything is documented.** The agent logs what it does, produces a recap of what was installed and what's left, and optionally generates a lightweight Showroom walkthrough of the finished environment.
- **OpenShift-focused initially.**

## Why It Matters

Express mode turns RHDP catalog content into reusable infrastructure. Instead of every field demo starting from zero — or settling for whatever's closest in the catalog — express starts from the best available base, customizes it to the specific need, and documents the result. The environment itself is throwaway, but the pattern creates a feedback loop: what people build in express reveals what the catalog is missing, which informs what should become a permanent catalog item through the standard pipeline.

## Lifecycle

Four phases, no review gates.

### 1. Intake

Conversational capture of what the user needs, for when, and for what audience. RCARS runs a vetting query against the catalog — if an existing CI already covers the need, the user can just order it and stop here. Reuse is always the best outcome.

If nothing fits and the user selects express, a second RCARS query runs. This one is broader, stripped of the unique parts of the request — focused on infrastructure requirements ("OpenShift cluster with Service Mesh and Crunchy Postgres installed") rather than demo-specific content. The result is a ranked list of candidate base CIs. The user picks one to order.

### 2. Environment (Gate)

The selected base CI is ordered and provisioned. Express gates here — no work proceeds until the environment is live and the agent has authenticated access to the cluster.

Babylon ordering automation is deferred. The initial implementation uses a manual gate: the user orders the CI, comes back with credentials, and the agent picks up.

### 3. Customize

This is the core of express mode. An AI agent:

- **Assesses** the provisioned cluster — what's already installed, what's running, what's available
- **Plans** customizations from the intake requirements — what operators to install, what apps to deploy, what demo data to create
- **Executes** live against the cluster — `oc` commands, operator installs, application deployments, ephemeral artifacts scaffolded on the fly
- **Converses** with the user throughout — asks questions when it hits decisions, reports progress, flags anything it can't handle

There are no Helm charts or GitOps repos involved. The agent works directly on the cluster. This is the most substantial piece of agent engineering in express mode and is scoped as its own separate design and implementation effort.

### 4. Handoff

The agent produces a **recap document**: what was installed, what was configured, what's working, and what's left for the user to finish manually. The recap is stored in the PH Central and, for local users, saved to their working directory.

Optionally, PH generates a **lightweight Showroom guide** — a simple walkthrough of the finished environment. This is created after the work is done. It describes the result; it doesn't drive the work.

## How RCARS Enables Express

Express uses RCARS for two distinct purposes through the same query interface:

| Query | Purpose | Example |
|-------|---------|---------|
| **Vetting** | Does something already exist that matches the full need? | "A lab demonstrating GitOps-based deployment of a microservices application on OpenShift with Service Mesh observability" |
| **Base-finding** | What existing CI provides the closest infrastructure foundation? | "OpenShift cluster with Service Mesh and a deployed sample application" |

The vetting query is identical to what the other PH modes use. The base-finding query is express-specific — it strips away the unique demo requirements and focuses on what infrastructure is already available in the catalog.

There is a dependency here: RCARS currently indexes Showroom content (what a lab teaches), not environment infrastructure (what operators and workloads each CI provisions). Full base-finding accuracy requires RCARS to develop infrastructure-aware catalog metadata by indexing AgnosticV definitions. Until then, content analysis serves as a functional proxy.

## State and Visibility

Express projects have no git repository. State lives in the PH Central database — intake data is stored via `ph_store_intake_results` and express run metrics via `ph_record_express_run`. Express projects are transient: they do not appear on Central kanban or have detail views. Aggregate metrics (how many express runs, which base CIs are popular) provide visibility into express usage patterns without per-project tracking overhead.

This is a meaningful shift from the other PH modes, where a git manifest is the source of truth. For express, Central stores intake data for session continuity, but the work itself is ephemeral.

## Who Uses It

Express mode is designed for field associates, SAs, and anyone who needs a tailored demo environment quickly and doesn't have the time or need to produce a permanent catalog item. Two access paths:

- **Claude Code users** run express through the PH skills plugin and authenticate to the cluster locally with `oc login`
- **Central users** (no Claude Code or Anthropic access required) interact through the hosted chatbot, providing cluster credentials through the browser

## What's Required to Build It

| Dependency | Status |
|------------|--------|
| PH MCP server with RCARS integration | Complete (Phase 1) |
| Central DB model for express (IntakeSession, ExpressMetric) | Complete (Phase 2) |
| Central MCP tools for session continuity | Complete (Phase 2) |
| Orchestrator awareness of Central-registered projects | Complete (Phase 2) |
| Intake three-mode routing with express flow | Complete (Phase 2) |
| Express skill (the cluster customization agent) | Needs its own design |
| RCARS infrastructure-aware metadata (for base-finding accuracy) | Backlogged in RCARS |
| Babylon ordering automation | Deferred (manual gate works) |

The framework is in place — MCP server, DB models, session tools, orchestrator discovery, and intake routing are all built. The express skill is the agent engineering effort that makes the mode actually useful, and it plugs into the framework when ready.
