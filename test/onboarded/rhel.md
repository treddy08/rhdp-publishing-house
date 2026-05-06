# Test Prompt: Onboarded — RHEL

## Initial Prompt

> I have a CFP submission I'd like to turn into a lab. RHDP Published.
>
> "Golden Images at Scale: RHEL Image Builder Meets Compliance-as-Code"
>
> Every organization has its own standard operating environment — hardened, compliant, pre-configured RHEL images that serve as the foundation for every deployment. But building and maintaining these golden images is typically a manual, error-prone process involving kickstart files and tribal knowledge. This workshop introduces RHEL Image Builder as a declarative, reproducible approach to golden image creation. Participants will build compliant RHEL images from blueprints, target multiple output formats, and automate the full lifecycle from image creation to provisioned VM. We'll integrate with SCAP compliance profiles to bake security in from the start.

## Follow-up Details (feed in when asked)

- Audience: Linux sysadmins, RHEL 8/9 experienced
- Cover both the cockpit/web UI and CLI (composer-cli) workflows
- Output formats: qcow2 for local KVM, AMI for AWS
- Automated provisioning: kickstart + Ansible post-config
- RHEL 9.4 target
