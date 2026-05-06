# Test Prompt: Self-Published — OpenShift App Platform

## Initial Prompt

I wrote this for an internal tech talk and now my manager wants it as a hands-on lab. Self-published, we'll run it ourselves.
"Strangler Fig in Practice: Incrementally Migrating Java Monoliths to OpenShift Microservices"
Everyone talks about breaking up monoliths but nobody shows you how to do it safely in production. This session walks through the strangler fig pattern using a real (simulated) legacy Java application. We'll extract services one at a time, route traffic between old and new with OpenShift, and keep everything running throughout the migration. No big-bang rewrites. No downtime. Just steady, measurable progress from monolith to microservices.

## Follow-up Details (feed in when asked)

- Customer has ~20 Spring Boot microservices, currently on VMs
- Containerization strategies: Dockerfile vs S2I vs Paketo buildpacks
- Config management: move from property files to ConfigMaps and Secrets
- Health checks, readiness probes, resource limits — the "production-ready" checklist
- No Service Mesh needed — keep it focused on the migration
