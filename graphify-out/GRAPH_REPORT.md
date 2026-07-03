# Graph Report - /Users/psrivast/work/code/rhdp-publishing-house  (2026-07-03)

## Corpus Check
- 129 files · ~140,923 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 594 nodes · 1213 edges · 43 communities (28 shown, 15 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.63)
- Token cost: 8,500 input · 3,200 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Fixture Data Models & Validators|Fixture Data Models & Validators]]
- [[_COMMUNITY_Test Fixture Loading & YAML|Test Fixture Loading & YAML]]
- [[_COMMUNITY_Platform Architecture & Concepts|Platform Architecture & Concepts]]
- [[_COMMUNITY_Content Skills & Deployment Modes|Content Skills & Deployment Modes]]
- [[_COMMUNITY_Manifest-Driven Spec & Automation|Manifest-Driven Spec & Automation]]
- [[_COMMUNITY_Runner Test Harness|Runner Test Harness]]
- [[_COMMUNITY_CLI & Validation Pipeline|CLI & Validation Pipeline]]
- [[_COMMUNITY_E2E Test Agents & Prompts|E2E Test Agents & Prompts]]
- [[_COMMUNITY_Red Hat Product Test Fixtures|Red Hat Product Test Fixtures]]
- [[_COMMUNITY_RCARS Integration & MCP Tools|RCARS Integration & MCP Tools]]
- [[_COMMUNITY_MCP Mock & Runner Core|MCP Mock & Runner Core]]
- [[_COMMUNITY_Runner Internal Helpers|Runner Internal Helpers]]
- [[_COMMUNITY_MCP Tool Lookup Tests|MCP Tool Lookup Tests]]
- [[_COMMUNITY_Two-Agent Simulation Loop|Two-Agent Simulation Loop]]
- [[_COMMUNITY_Project Seeder Script|Project Seeder Script]]
- [[_COMMUNITY_RunResult Output Model|RunResult Output Model]]
- [[_COMMUNITY_MCPMock Callable Interface|MCPMock Callable Interface]]
- [[_COMMUNITY_Runner API Key Tests|Runner API Key Tests]]
- [[_COMMUNITY_MCPMock Isolation Tests|MCPMock Isolation Tests]]
- [[_COMMUNITY_Portal Infrastructure Stack|Portal Infrastructure Stack]]
- [[_COMMUNITY_MCPMock Init Tests|MCPMock Init Tests]]
- [[_COMMUNITY_Jira & Manifest Integration|Jira & Manifest Integration]]
- [[_COMMUNITY_Hub+Spoke Plugin Architecture|Hub+Spoke Plugin Architecture]]
- [[_COMMUNITY_Core Harness Types|Core Harness Types]]
- [[_COMMUNITY_RCARS Query Schema Tests|RCARS Query Schema Tests]]
- [[_COMMUNITY_Orchestrator & Autonomy Control|Orchestrator & Autonomy Control]]
- [[_COMMUNITY_Unknown Tool Error Tests|Unknown Tool Error Tests]]
- [[_COMMUNITY_Sync Manifest Schema Tests|Sync Manifest Schema Tests]]
- [[_COMMUNITY_MCP Mock Integration Tests|MCP Mock Integration Tests]]
- [[_COMMUNITY_Portal & RCARS MCP Tools|Portal & RCARS MCP Tools]]
- [[_COMMUNITY_Conftest & Module Test Suites|Conftest & Module Test Suites]]
- [[_COMMUNITY_Root Conftest|Root Conftest]]
- [[_COMMUNITY_Docs & CI Workflow|Docs & CI Workflow]]
- [[_COMMUNITY_Express OCP Test Prompts|Express OCP Test Prompts]]
- [[_COMMUNITY_Plugin Manifests|Plugin Manifests]]
- [[_COMMUNITY_Antora Build Config|Antora Build Config]]
- [[_COMMUNITY_Human Modifications Rule|Human Modifications Rule]]
- [[_COMMUNITY_Fixture Loader Module|Fixture Loader Module]]
- [[_COMMUNITY_ph-test CLI|ph-test CLI]]
- [[_COMMUNITY_Test Requirements|Test Requirements]]
- [[_COMMUNITY_Showroom UI Config|Showroom UI Config]]

## God Nodes (most connected - your core abstractions)
1. `Fixture` - 56 edges
2. `run()` - 44 edges
3. `load_fixture()` - 42 edges
4. `MCPMock` - 38 edges
5. `validate()` - 36 edges
6. `_make_fixture()` - 34 edges
7. `make_fixture()` - 33 edges
8. `setup_project_dir()` - 31 edges
9. `RunResult` - 27 edges
10. `write_yaml()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `run() Function (ph_test.runner)` --semantically_similar_to--> `Orchestrator Skill (Hub, State Management)`  [INFERRED] [semantically similar]
  test/test_runner.py → docs/how-it-works.md
- `Two-Agent Simulation: Tester Bot + PH Orchestrator via LiteMaaS` --semantically_similar_to--> `Content Lifecycle Phases: intake → vetting → writing → publishing`  [INFERRED] [semantically similar]
  src/ph_test/runner.py → CLAUDE.md
- `APPROVAL_GATE_REACHED Termination Signal` --conceptually_related_to--> `Content Lifecycle Phases: intake → vetting → writing → publishing`  [INFERRED]
  test/test_runner.py → CLAUDE.md
- `MCPMock — MCP Interceptor Returning YAML Fixture Responses` --conceptually_related_to--> `Portal Backend — FastAPI + FastMCP 3.2 Single Gateway`  [INFERRED]
  src/ph_test/mcp_mock.py → CLAUDE.md
- `Project Manifest (publishing-house/manifest.yaml) — Source of Truth` --semantically_similar_to--> `Worklog YAML (Human Context Bridge Between Sessions)`  [INFERRED] [semantically similar]
  CLAUDE.md → docs/superpowers/specs/2026-04-19-portal-redesign.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **PH E2E Test Harness — Four Coordinated Modules** — fixtures_py, mcp_mock_py, runner_py, validator_py [EXTRACTED 1.00]
- **Portal Dual Auth: External API Key + Internal SA Token via Single Gateway** — concept_api_key_auth, concept_sa_token_auth, concept_portal_backend [EXTRACTED 1.00]
- **Manifest-Driven Lifecycle: manifest controls phases, portal and Jira consume** — concept_manifest, concept_content_lifecycle, concept_portal_backend, concept_jira_integration [EXTRACTED 0.90]
- **Two-Boundary Auth Model (API Key + SA Token protecting MCP and RCARS)** — mcp_auth_apikey, rcars_auth_satoken, arch_rcars_integration [EXTRACTED 1.00]
- **Portal Backend Stack (FastAPI + FastMCP + PostgreSQL on OpenShift)** — concept_fastapi_backend, mcp_tools_server, concept_postgresql, concept_openshift [EXTRACTED 1.00]
- **PH State Management Core (Manifest + Orchestrator + Content Lifecycle)** — concept_manifest_yaml, concept_orchestrator_skill, concept_content_lifecycle [INFERRED 0.90]
- **PH Multi-Plugin Package (Four Plugins Consolidated in One Repo)** — concept_showroom, concept_agnosticv, concept_ftl, concept_plugin_consolidation [EXTRACTED 1.00]
- **Automation Phase 7 Pipeline (SKILL.md + Manifest + AgnosticV Form Automation Flow)** — skill_automation, concept_automation_manifest, concept_agnosticv [EXTRACTED 1.00]
- **Portal Integration Stack (Backend + MCP Server + RCARS Form External Gateway)** — concept_portal_backend, concept_mcp_server, concept_rcars [EXTRACTED 1.00]
- **PH Content Creation Lifecycle (intake → write → edit → orchestrate)** — skpl_orchestrator, skpl_intake, skpl_writer, skpl_editor [EXTRACTED 0.95]
- **Automation Sub-Phase Pipeline (requirements → catalog → code → test)** — sk_automation, ext_agnosticv_catalog_builder, ext_agnosticv_validator, concept_automation_manifest_yaml [EXTRACTED 0.90]
- **Spec Creation Reference Set (template + outline + guidelines → design spec)** — skpl_intake_design_template, skpl_intake_module_outline_template, skpl_intake_spec_guidelines [EXTRACTED 0.95]
- **Publishing House Content Lifecycle Pipeline (Orchestrator + Writer + Worklog + Phases)** — orchestrator_skill, writer_skill, worklog_skill, concept_lifecycle_phases [EXTRACTED 0.90]
- **E2E Test Harness Pattern (Testing Suite + Seeder + Tester Sub-Agents)** — testing_suite_skill, concept_seeder_agent, concept_tester_agent [EXTRACTED 1.00]
- **Showroom Antora Build Configuration (site.yml + ui-config.yml + antora.yml)** — template_site_yml, template_ui_config_yml, template_antora_yml [INFERRED 0.85]
- **Onboarded Mode Test Suite (Three Product Fixtures)** — fixture_onboarded_ocp_app_platform, fixture_onboarded_ocp_platform, fixture_onboarded_rhel [EXTRACTED 1.00]
- **Self-Published Mode Test Suite (Five Product Fixtures)** — fixture_selfpub_ai, fixture_selfpub_ansible, fixture_selfpub_ocp_app_platform, fixture_selfpub_ocp_platform, fixture_selfpub_rhel [EXTRACTED 1.00]
- **MCP Portal API Mock Contract (RCARS + Portal Tools)** — mock_mcp_responses, concept_rcars_tool, concept_mcp_portal_tools [EXTRACTED 1.00]

## Communities (43 total, 15 thin omitted)

### Community 0 - "Fixture Data Models & Validators"
Cohesion: 0.09
Nodes (34): BaseModel, ConversationOutcomes, ExpectedOutcomes, Fixture, Phase 1: conversation-level validation (API-only mode)., Describes the artifacts and state the PH is expected to produce., A single ph-test fixture that drives a tester-bot + PH-orchestrator run., Validate PH orchestrator output against a fixture's expected outcomes.      Chec (+26 more)

### Community 1 - "Test Fixture Loading & YAML"
Cohesion: 0.07
Nodes (17): load_fixture(), ph_test.fixtures — Fixture loader for the PH autonomous E2E test harness.  Loads, Read a YAML fixture file and return a validated :class:`Fixture`.      Args:, Path, Path, Tests for ph_test.fixtures — TDD (RED phase first).  Covers:   - load_fixture re, Write a YAML string to a temp file and return its path., A list with a whitespace-only file path must be rejected. (+9 more)

### Community 2 - "Platform Architecture & Concepts"
Cohesion: 0.07
Nodes (50): BACKLOG.md — Roadmap and Work Queue, CLAUDE.md — RHDP Publishing House Architecture Guide, ph-test CLI Entrypoint (installed command delegator), Bearer API Key Auth for External MCP Clients (SHA-256, K8s Secret), Content Lifecycle Phases: intake → vetting → writing → publishing, OpenShift Dev Spaces (Hosted Workspace for PH Users), Express Mode — Transient Projects Stored in Portal DB Only, Express Deployment Mode (Ephemeral One-Off Demo) (+42 more)

### Community 3 - "Content Skills & Deployment Modes"
Cohesion: 0.09
Nodes (43): AgnosticV Catalog System (catalog-builder + validator), Event-Driven Ansible (EDA) with Alertmanager and Rulebooks, Ansible Lightspeed with watsonx Code Assistant, Automation Manifest YAML (Human-Reviewable Automation Contract), Three Deployment Modes: rhdp_published, self_published, express, Editor Skill (Technical Editing, wraps verify-content), Field Source CI (Self-Published Lab Deployment Mechanism), FTL Testing System (Solve/Validate Playbooks) (+35 more)

### Community 4 - "Manifest-Driven Spec & Automation"
Cohesion: 0.11
Nodes (36): publishing-house/spec/automation-manifest.yaml, Automation Sub-Phases (7a requirements, 7b catalog, 7c code, 7d testing), Autonomy Levels (guided/semi/full), publishing-house/spec/design.md (project design spec), Module Outline Files (publishing-house/spec/modules/), ph_payload headless mode (showroom skill invocation), Publishing House Central (MCP gateway), publishing-house/worklog.yaml (session bridge) (+28 more)

### Community 5 - "Runner Test Harness"
Cohesion: 0.14
Nodes (13): _make_client_mock(), _make_fixture(), Fixture, Should stop after 1 tester response, not run all 20 turns., APPROVAL_GATE_REACHED anywhere in tester response should trigger., turns should reflect how many full tester+orchestrator pairs completed., Entries should interleave: tester, orchestrator, tester, orchestrator..., Build a minimal valid Fixture for runner tests. (+5 more)

### Community 6 - "CLI & Validation Pipeline"
Cohesion: 0.11
Nodes (20): Any, ph-test CLI entrypoint — delegates to scripts/ph-test.py logic. Installed as `ph, _navigate_dotted_path(), ph_test.validator — Structural validation of PH orchestrator output.  After the, Navigate a dotted-path key through a nested dict.      Parameters     ----------, Phase 1: validate conversation-level outcomes from a RunResult.      Parameters, validate_conversation(), RunResult (+12 more)

### Community 7 - "E2E Test Agents & Prompts"
Cohesion: 0.15
Nodes (23): Content Lifecycle Phases (intake→writing→editing→…), Publishing House Central MCP Tools (ph_register, ph_list_projects, ph_request_gate, etc.), ph_payload Headless Mode for Deterministic Showroom Skill Invocation, Seeder Sub-Agent (Test Project Fixture Generator), Tester Sub-Agent (Simulates Content Developer in Tests), Express Test Prompt: RHOAI Model Inference Demo, Express Test Prompt: Ansible Automation Platform Demo, Express Test Prompt: RHEL Satellite CVE Remediation Demo (+15 more)

### Community 8 - "Red Hat Product Test Fixtures"
Cohesion: 0.14
Nodes (21): AgnosticV Catalog Item (Full RHDP Publishing Pipeline), GitOps Pipeline (ArgoCD, Tekton Pipelines), OpenShift Microservices App Platform (Quarkus, Service Mesh, GitOps, Inner/Outer Loop), OpenShift Cluster Troubleshooting (Break/Fix Scenarios, etcd, Certificates), Onboarded (RHDP Published) Deployment Mode, OpenShift Virtualization and VM Migration (OCP Virt, MTV, vSphere), RHEL Image Builder Golden Images and SCAP Compliance-as-Code, RHEL System Roles at Scale (Fleet Automation, AAP) (+13 more)

### Community 9 - "RCARS Integration & MCP Tools"
Cohesion: 0.14
Nodes (20): Express Mode (Fast Path for Disposable Demo Environments), RCARS Integration Architecture, RCARS Content Advisory System (v2 API), MCP API Key Auth (SHA-256, K8s Secret), ph_rcars_catalog_item MCP Tool, ph_rcars_catalog_search MCP Tool, ph_get_intake_results MCP Tool, ph_get_validation_results MCP Tool (+12 more)

### Community 10 - "MCP Mock & Runner Core"
Cohesion: 0.13
Nodes (14): MCPMock, MCPMock — ph-test harness MCP interceptor.  Intercepts MCP tool calls during tes, Callable MCP interceptor that returns fixture responses by tool name.      Param, Return a deep copy of the fixture response for *tool_name*.          Parameters, _contains_approval_gate(), _load_skill_md(), _orchestrator_system_prompt(), ph_test.runner — Two-agent simulation loop for the PH autonomous E2E test harnes (+6 more)

### Community 11 - "Runner Internal Helpers"
Cohesion: 0.12
Nodes (10): _extract_text(), Pull plain text from an OpenAI-compatible chat completion response., _extract_text returns '' for empty choices list (OpenAI format)., _load_skill_md returns placeholder when SKILL.md does not exist., _read_manifest returns '' when manifest.yaml does not exist., verbose=True prints error message when orchestrator call fails., Error on tester's call (after orchestrator succeeded) sets termination_reason=er, verbose=True prints error when tester API call fails. (+2 more)

### Community 13 - "Two-Agent Simulation Loop"
Cohesion: 0.17
Nodes (9): MCPMock, Execute a two-agent simulation loop.      Parameters     ----------     fixture:, run(), _tester_system_prompt(), Fixture, run() must not raise — it must return a RunResult with error info., Error on orchestrator's first call should still stop cleanly., TestAPIErrorHandling (+1 more)

### Community 14 - "Project Seeder Script"
Cohesion: 0.23
Nodes (14): clone_template(), generate_design_md(), generate_module_outline(), generate_with_llm(), load_env_from_creds(), main(), Path, ph-seed — Seed a PH project directory from a test fixture.  Reads a fixture YAML (+6 more)

### Community 15 - "RunResult Output Model"
Cohesion: 0.24
Nodes (3): Outcome of a single harness run., RunResult, TestRunResultDataclass

### Community 16 - "MCPMock Callable Interface"
Cohesion: 0.27
Nodes (5): make_mock(), params dict is forwarded without error (mock ignores params by design)., The mock returns the same fixture regardless of what params are passed., Import and instantiate MCPMock, forwarding any kwargs., TestCallableInterface

### Community 17 - "Runner API Key Tests"
Cohesion: 0.17
Nodes (7): _make_openai_message(), Tests for ph_test.runner — TDD (RED phase first).  Covers:   - RunResult datacla, All listed approval signals in orchestrator output should prompt tester to reply, Return a minimal mock that looks like an OpenAI ChatCompletion response., TestAPIKeyRequired, TestApprovalSignalDetection, TestTesterReceivesOrchestratorContext

### Community 18 - "MCPMock Isolation Tests"
Cohesion: 0.18
Nodes (7): Tests for MCPMock — ph-test harness MCP interceptor.  TDD: these tests are writt, Each __call__ must return a fresh copy so callers cannot pollute state., MCPMock() must find mcp_responses.yaml even when cwd is changed., A YAML file whose top-level is a list (not a mapping) raises ValueError., TestDefaultPathResolution, TestMalformedYaml, TestResponseImmutability

### Community 19 - "Portal Infrastructure Stack"
Cohesion: 0.27
Nodes (10): Hosted Workspace via OpenShift Dev Spaces, Publishing House Portal Architecture, FastAPI Backend (Portal Backend Service), Model as a Service (MaaS / LiteLLM) Platform, Next.js Frontend (PatternFly 6 UI), OpenShift Deployment Platform, PostgreSQL Database (Portal State Store), Dashboard POC Plan (FastAPI + Next.js + PatternFly) (+2 more)

### Community 20 - "MCPMock Init Tests"
Cohesion: 0.22
Nodes (5): MCPMock() with no args loads the bundled mcp_responses.yaml., MCPMock(responses_path=...) loads from the supplied path., responses_path may be a plain string, not just a Path., Passing a non-existent path raises FileNotFoundError, not a silent failure., TestMCPMockInit

### Community 21 - "Jira & Manifest Integration"
Cohesion: 0.29
Nodes (8): Jira Integration (Initiative/Epic/Task Hierarchy), Manifest as Source of Truth Rule, Intake Agent Skill, publishing-house/manifest.yaml (Single Source of Truth), ph_sync_manifest MCP Tool, Phase 1 Plan: Plugin Scaffold + Orchestrator + Intake, Dotted-Path Manifest Navigation, validate() Function (ph_test.validator)

### Community 22 - "Hub+Spoke Plugin Architecture"
Cohesion: 0.36
Nodes (8): Automation Agent Skill (wraps agnosticv skills), Editor Agent Skill (wraps showroom:verify-content), Hub+Spoke Claude Code Plugin Architecture Pattern, Writer Agent Skill (wraps showroom:create-lab), Executive Summary, How It Works (Hub+Spoke Architecture), Phase 2 Plan: Writer Agent + Editor Agent, Phase 3 Plan: Automation Agent

### Community 23 - "Core Harness Types"
Cohesion: 0.25
Nodes (8): Fixture Class (ph_test.fixtures), MCPMock Class, RunResult Dataclass, APPROVAL_GATE_REACHED Termination Signal, _extract_text Helper Function, _read_manifest Helper Function, run() Function (ph_test.runner), ExpectedOutcomes Dataclass

### Community 25 - "Orchestrator & Autonomy Control"
Cohesion: 0.43
Nodes (7): Autonomy Levels (supervised/semi/full), Phase Transition Rule (Orchestrator-Only), Orchestrator Skill (Hub, State Management), Phase-Gate Repo Creation (Orchestrator Pre-Dispatch Checks), Getting Started Guide, Orchestrator Discovery and Repo Gates Implementation Plan, Orchestrator Project Discovery and Phase-Gate Repo Creation Spec

### Community 29 - "Portal & RCARS MCP Tools"
Cohesion: 0.67
Nodes (3): Publishing House MCP Portal Tools (ph_sync_manifest, ph_store_intake_results, ph_list_projects, ph_record_express_run), RCARS Catalog Analysis MCP Tool (ph_rcars_query, ph_rcars_catalog_search), MCP Portal Mock Responses for ph-test Harness

### Community 30 - "Conftest & Module Test Suites"
Cohesion: 0.67
Nodes (3): Pytest Conftest — sys.path Fix for src-layout, Fixture Module Test Suite (TDD — frozen model, field validation), MCPMock Test Suite (schema validation, immutability, error cases)

## Knowledge Gaps
- **62 isolated node(s):** `ph-test`, `Path`, `Path`, `RHDP Publishing House Root Plugin Manifest`, `RHDP Publishing House Skills Plugin Manifest` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MCPMock` connect `MCP Mock & Runner Core` to `Runner Test Harness`, `CLI & Validation Pipeline`, `Runner Internal Helpers`, `MCP Tool Lookup Tests`, `Two-Agent Simulation Loop`, `RunResult Output Model`, `MCPMock Callable Interface`, `Runner API Key Tests`, `MCPMock Isolation Tests`, `MCPMock Init Tests`, `RCARS Query Schema Tests`, `Unknown Tool Error Tests`, `Sync Manifest Schema Tests`, `MCP Mock Integration Tests`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `Fixture` connect `Fixture Data Models & Validators` to `Test Fixture Loading & YAML`, `Runner Test Harness`, `CLI & Validation Pipeline`, `MCP Mock & Runner Core`, `Runner Internal Helpers`, `Two-Agent Simulation Loop`, `RunResult Output Model`, `Runner API Key Tests`, `MCP Mock Integration Tests`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `load_fixture()` connect `Test Fixture Loading & YAML` to `Fixture Data Models & Validators`, `CLI & Validation Pipeline`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `Fixture` (e.g. with `Any` and `MCPMock`) actually correct?**
  _`Fixture` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `MCPMock` (e.g. with `MCPMock` and `RunResult`) actually correct?**
  _`MCPMock` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Root conftest.py — ensures the project root and src/ are on sys.path so tests ca`, `ph-test`, `ph-seed — Seed a PH project directory from a test fixture.  Reads a fixture YAML` to the rest of the system?**
  _139 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Fixture Data Models & Validators` be split into smaller, more focused modules?**
  _Cohesion score 0.0886615515771526 - nodes in this community are weakly interconnected._