# Test Prompt: Onboarded — OpenShift Platform/Virt

## Initial Prompt

I want to build a workshop on OpenShift Virtualization for VM admins who are new to Kubernetes. The goal is to get them comfortable migrating and managing VMs on OpenShift. Should be RHDP Published, targeting Summit 2027.

## Follow-up Details (feed in when asked)

- Audience knows vSphere/RHV well but has never touched Kubernetes
- Should cover MTV for importing VMs, not just creating new ones
- Need a pre-staged Windows VM in vSphere to import — that's the "aha" moment
- Day 2 ops are important: backup, maintenance mode, live migration
- Multi-user lab, each learner gets their own namespace
- OCP 4.17+ with OCP Virt and MTV operators pre-installed
- Want the full pipeline: AgnosticV catalog, Ansible automation
