# Test Prompt: Onboarded — OpenShift App Platform

## Initial Prompt

> I want to create a developer-focused workshop showing how to build and deploy a microservices application on OpenShift using Quarkus, Service Mesh, and GitOps. Developers should walk away understanding the inner loop and outer loop experience on OCP. RHDP Published.

## Follow-up Details (feed in when asked)

- Target audience: Java developers, comfortable with containers but new to OpenShift
- Inner loop: odo or Podman Desktop for local dev, push to OpenShift Dev Spaces
- Outer loop: Tekton pipelines, ArgoCD for GitOps delivery
- Service Mesh for observability between services, not just networking
- Sample app: 3-4 microservices, nothing too complex — a storefront or order system
- Would like a module on debugging with distributed tracing (Jaeger/Tempo)
- OCP 4.16+, Dev Spaces operator, OpenShift GitOps, OpenShift Pipelines, Service Mesh pre-installed
