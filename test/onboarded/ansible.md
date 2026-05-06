# Test Prompt: Onboarded — Ansible

## Initial Prompt

I submitted a CFP for an Ansible workshop at a customer event. Here's the abstract:
"Event-Driven Automation: From Alert to Resolution"
Traditional automation is powerful but reactive — someone has to trigger it. Event-Driven Ansible (EDA) closes the loop by automatically responding to events from monitoring systems, cloud providers, and IT service management platforms. In this hands-on workshop, participants will build an event-driven automation pipeline that detects infrastructure issues, triages them, and executes remediation — all without human intervention. We'll connect real monitoring alerts to Ansible rulebooks and watch automation respond in real time.
Can you build this as an RHDP Published lab?

## Follow-up Details (feed in when asked)

- AAP 2.5 with EDA controller
- Alertmanager as the event source (already firing test alerts)
- Scenarios: disk full remediation, service restart, scaling
- Should cover rulebook writing from scratch, not just using pre-built ones
- Include a ServiceNow integration module if possible — auto-create incident tickets
