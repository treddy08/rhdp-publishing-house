# Test Prompt: Onboarded — AI Observability (3 micro-labs)

## Repo

`git@github.com:rhpds/publishing-house-example-ai.git` (branch: `main`)

## Initial Prompt

I have an idea for a set of quick micro-labs showcasing OpenShift AI's observability and model lifecycle capabilities. Think event booth or self-service marketing portal — not a 2-hour training. Each lab should deliver one "wow moment" in under 10 minutes and work independently. I want this RHDP Published.

## Follow-up Details (feed in when asked)

- Three micro-labs, loosely connected but each independently completable
- Audience: data scientists, platform engineers, architects evaluating RHOAI at an event
- Level: beginner — no OpenShift or RHOAI experience required
- Lab 1: Drift detection — attendee sends drifted data to a deployed model, TrustyAI catches the drift, a Data Science Pipeline auto-triggers to retrain. The retraining uses a MaaS endpoint (no on-cluster GPU).
- Lab 2: Model serving — deploy a new model version via the RHOAI console, split traffic canary-style, watch serving metrics shift in real time. KServe under the hood.
- Lab 3: Model Registry — compare two versions side by side (accuracy, latency, drift score), promote the winner to Production stage, watch an automated pipeline swap serving traffic to it.
- Each lab is 5-10 minutes, UI-first (RHOAI console drives everything, CLI only for the drift simulation script)
- Pre-provisioned tenant per attendee — everything is ready before they log in, first step is always meaningful
- No YAML copy-pasting, no waiting for spin-up mid-lab
- Shared OCP 4.14+ cluster with RHOAI 2.x operator
- Per-tenant pre-config: deployed fraud detection model, TrustyAI enabled, pipeline defined, two model versions in registry with metadata
- Automation is required — tenant provisioning must happen before the event, not during lab execution
- Automation approach: GitOps (Helm + ArgoCD) for tenant provisioning

## Expected Outcomes

After a successful intake run, the spec should contain:

- **3 modules** with clear "wow moment" per lab (drift alert, canary deployment, registry promotion)
- **Problem statement** framing the gap between long training labs and quick event experiences
- **Learning objectives** tied to specific observable actions (trigger drift alert, deploy version, promote in registry)
- **Infrastructure requirements** specifying shared cluster, per-tenant namespace, pre-provisioned resources
- **Automation section** calling out tenant provisioning as a pre-event activity, not a lab-time activity
- **Design principles** emphasizing no-toil, UI-first, independent labs

After a successful run through the approval gate:

- Manifest should show intake completed, vetting completed (or skipped depending on RCARS availability), spec refinement completed, approval completed
- Design spec should be in `publishing-house/spec/design.md`
- Three module outlines should be in `publishing-house/spec/modules/`
- Manifest `writing.modules` should list all 3 modules with pending status
