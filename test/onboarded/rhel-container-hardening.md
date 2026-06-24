# Test Prompt: Onboarded — RHEL Container Hardening (Hummingbird)

## Repo

TBD — will be created as `publishing-house-example-rhel`

## Reference

Existing Showroom content (for context, not to copy): https://rhpds.github.io/hummingbird-showroom/modules/index.html

## Notes

This lab already exists as LB2865 in RHDP. The test exercises intake for a lab that has prior art — RCARS vetting should surface the existing catalog item. The RHEL-only portion (Module 1 in the original) is the focus; ignore the OpenShift/Shipwright module.

## Initial Prompt

I want to build a hands-on workshop on container hardening using Red Hat's Hardened Images — the distroless, zero-CVE base images from Project Hummingbird. This is for developers and platform engineers who build container images today but don't think much about supply chain security. The goal is to take them from "I just use the base UBI image" to "I build minimal, signed, scanned images with full provenance." RHDP Published.

## Follow-up Details (feed in when asked)

- Focus on the RHEL developer workflow only — no OpenShift, no Shipwright, no Buildpacks
- Audience: developers and platform engineers who use containers daily, comfortable with Podman and Dockerfiles, but haven't thought deeply about image minimization or supply chain security
- Level: intermediate — they know how to build images, we're teaching them to build them better
- Module 1: Introduction to hardened images — what they are, why they exist, how they compare to standard UBI images. Show the size and CVE count difference.
- Module 2: Multi-stage builds with hardened images — build a real app using a standard UBI builder stage and a hardened runtime stage. Show the resulting image is tiny and has near-zero CVEs.
- Module 3: Vulnerability scanning and SBOMs — scan images with grype, generate SBOMs with syft, compare results between standard and hardened images
- Module 4: Image signing and attestation — sign images with cosign, verify signatures, attach attestations. Complete the supply chain security story.
- Each module 15-20 minutes, total workshop ~75 minutes hands-on
- Tools: Podman (rootless), Buildah, Skopeo, cosign, syft, grype — all pre-installed
- Sample app: a simple Python or Go web app (doesn't matter much, it's the vehicle)
- Registry: Red Hat Quay (pre-configured per user)
- Environment: RHEL 9 VM with all tools pre-installed, VS Code Server or terminal access via Showroom
- Automation needed: VM provisioning with tools, Quay org/repos per user, sample app source in a local Git repo

## Expected Outcomes

After a successful intake run, the spec should contain:

- **4 modules** progressing from concepts through building to full supply chain security
- **Problem statement** about container image bloat and supply chain risk
- **Learning objectives** tied to hands-on actions (build multi-stage, scan, generate SBOM, sign, verify)
- **Products** listing Red Hat Hardened Images, Podman, Buildah, Skopeo, Red Hat Quay, plus open-source tools (cosign, syft, grype)
- **Infrastructure requirements** specifying RHEL 9 VMs (not OCP clusters)
- Vetting should flag LB2865 (hummingbird) as related content if RCARS is available

After a successful run through the approval gate:

- Manifest should show intake completed, vetting completed (with RCARS findings if available), spec refinement completed, approval completed
- Design spec in `publishing-house/spec/design.md`
- Four module outlines in `publishing-house/spec/modules/`
- Manifest `writing.modules` should list all 4 modules with pending status
