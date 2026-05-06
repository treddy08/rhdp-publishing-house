# Test Prompt: Onboarded — RHEL

## Initial Prompt

> Build a lab on RHEL Image Builder and automated provisioning. Sysadmins should be able to create custom RHEL images, publish them, and deploy VMs from those images automatically. RHDP Published.

## Follow-up Details (feed in when asked)

- Audience: Linux sysadmins, RHEL 8/9 experienced
- Cover both the cockpit/web UI and CLI (composer-cli) workflows
- Blueprints with custom packages, services, firewall rules
- Output formats: qcow2 for local KVM, AMI for AWS, VMDK for vSphere
- Integration with Satellite for content management
- Automated provisioning: kickstart + Ansible post-config
- Would be nice to show compliance profiles (CIS/STIG) baked into the image
- RHEL 9.4 target
