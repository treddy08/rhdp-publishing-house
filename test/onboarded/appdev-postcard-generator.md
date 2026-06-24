# Test Prompt: Onboarded — App Dev Quick Labs (5 modules, bring-your-own automation)

## Repo

`git@github.com:rhpds/publishing-house-example-appdev.git` (branch: `main`)

## Notes

This repo already contains a working `postcard-generator/` Flask app and full `automation/` directory (Helm charts for cluster, platform, and tenant tiers). The test exercises the "I have the app and automation, I need the content written" path. Intake should discover the existing app and automation rather than planning them from scratch.

## Initial Prompt

I have a set of five standalone quick-labs for OpenShift application development, each showcasing a different developer tool. They share a sample app — a Postcard Generator (Flask/Python) that's already in the repo. The automation (Helm charts for GitOps-based provisioning) is also done. I need RHDP Published content written for these. Each lab should be booth-friendly, completable in 20 minutes, and work independently.

## Follow-up Details (feed in when asked)

- Five labs, each starring one product: Developer Hub, Dev Spaces, Pipelines, GitOps, AI
- Lab 1 (Developer Hub): Scaffold the postcard app from a golden path template, see it running
- Lab 2 (Dev Spaces): Open the running app in Dev Spaces, modify styling and add a destination with live reload
- Lab 3 (Pipelines): Push a code change, watch Tekton build and deploy it automatically
- Lab 4 (GitOps): Cause configuration drift in a deployed app, watch ArgoCD detect and correct it
- Lab 5 (AI): Switch postcard taglines from canned text to AI-generated messages via a MaaS endpoint
- Audience: developers, sysadmins, platform engineers, architects — comfortable with terminals and containers but not necessarily software engineers
- Tone is marketing, not training: "look how easy this is" — no deep-dive explanations
- The postcard-generator app is already in the repo (Flask backend, Leaflet.js maps, retro travel poster aesthetic)
- Automation is already done — cluster/platform/tenant Helm charts in `automation/`. Each lab has its own tenant CI
- Pre-provisioned environments: Gitea repos, RHDH templates, ArgoCD apps, pipeline configs, Dev Spaces workspaces, MaaS credentials all pre-configured per user
- OCP 4.21+ shared cluster with RHDH, Dev Spaces, Pipelines, GitOps, and RHOAI operators
- Automation approach: GitOps (Helm + ArgoCD) — already implemented

## Expected Outcomes

After a successful intake run, the spec should contain:

- **5 modules** each with a clear "star product" and standalone structure
- **Problem statement** framing the gap between long training labs and quick booth/self-service experiences
- **Learning objectives** — one per lab tied to observable actions (scaffold, live-edit, trigger pipeline, observe drift correction, integrate AI)
- **The sample app** described as a vehicle, not the destination — engaging but simple
- **Design principles** emphasizing standalone labs, 20-minute hard ceiling, marketing tone
- **Infrastructure requirements** referencing the existing automation in the repo
- **Automation section** should note that automation already exists (not "needs to be built")

After a successful run through the approval gate:

- Manifest should show intake completed, vetting completed/skipped, spec refinement completed, approval completed
- Design spec in `publishing-house/spec/design.md`
- Five module outlines in `publishing-house/spec/modules/`
- Manifest `writing.modules` should list all 5 modules with pending status
- Manifest `automation.needs_automation` should be `true` with a note that code already exists
