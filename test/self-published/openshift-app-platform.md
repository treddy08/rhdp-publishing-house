# Test Prompt: Self-Published — OpenShift App Platform

## Initial Prompt

> I'm putting together a hands-on session for a customer's dev team on migrating their Spring Boot apps to OpenShift. Self-published — I'll deploy it from my own repo.

## Follow-up Details (feed in when asked)

- Customer has ~20 Spring Boot microservices, currently on VMs
- Focus on the migration path, not greenfield development
- Containerization strategies: Dockerfile vs S2I vs Paketo buildpacks
- Config management: move from property files to ConfigMaps and Secrets
- Health checks, readiness probes, resource limits — the "production-ready" checklist
- No Service Mesh needed — keep it focused on the migration
