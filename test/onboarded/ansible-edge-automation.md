# Test Prompt: Onboarded — Ansible Edge Automation

## Repo

TBD — will be created as `publishing-house-example-ansible`

## Notes

Fictional lab for testing PH workflows. The specific content doesn't need to be perfect — this exercises intake, vetting, spec generation, and approval for an Ansible-focused workshop. Good test case because it's a different product domain from the AI and AppDev examples.

## Initial Prompt

I want to create a workshop that shows how Ansible Automation Platform can manage edge devices at scale. Think retail store kiosks or industrial IoT gateways — devices that are remote, numerous, and can't be individually SSHed into. The lab should demonstrate the full lifecycle: onboarding a new device, pushing configuration, deploying an application update, and remediating a security finding — all from a central AAP controller. RHDP Published.

## Follow-up Details (feed in when asked)

- Audience: sysadmins and infrastructure engineers who know basic Ansible (playbooks, inventory) but haven't used AAP for edge use cases
- Level: intermediate
- Module 1: Fleet onboarding — register simulated edge devices with AAP using auto-registration. Devices appear in a smart inventory grouped by location and role.
- Module 2: Configuration as code — push a standardized configuration (NTP, logging, firewall rules) to all kiosks using a job template. Show compliance drift detection with a follow-up audit job.
- Module 3: Application deployment — deploy a containerized POS application to edge devices using ansible-navigator and execution environments. Rolling update pattern (one location at a time).
- Module 4: Security remediation — AAP receives a webhook from a vulnerability scanner, triggers an automated remediation playbook that patches and reboots devices in a maintenance window.
- Each module 20-25 minutes, total ~90 minutes hands-on
- Products: Red Hat Ansible Automation Platform 2.5, Event-Driven Ansible, RHEL 9 on the edge devices
- The edge devices are simulated — RHEL 9 VMs acting as kiosks, not real hardware
- AAP Controller + Hub pre-deployed on a shared RHEL server or OCP cluster
- 5 simulated edge devices per user (RHEL 9 VMs with minimal config)
- Automation needed: AAP deployment, edge VM provisioning, pre-populated Automation Hub with required collections
- Execution environments pre-built with required collections (edge management, firewall, package management)

## Expected Outcomes

After a successful intake run, the spec should contain:

- **4 modules** covering the edge lifecycle (onboard, configure, deploy, remediate)
- **Problem statement** about managing distributed infrastructure at scale
- **Learning objectives** tied to AAP features (smart inventories, job templates, EDA webhooks, execution environments)
- **Products** listing AAP 2.5, Event-Driven Ansible, RHEL 9
- **Infrastructure requirements** specifying AAP Controller + simulated edge VMs
- Vetting may surface existing AAP labs in RCARS — that's fine, the edge angle should differentiate

After a successful run through the approval gate:

- Manifest should show intake completed, vetting completed, spec refinement completed, approval completed
- Design spec in `publishing-house/spec/design.md`
- Four module outlines in `publishing-house/spec/modules/`
- Manifest `writing.modules` should list all 4 modules with pending status
