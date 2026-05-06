# Test Prompt: Onboarded — AI

## Initial Prompt

> Here's a CFP abstract I submitted. Can you build this as an RHDP Published lab?
>
> "From Foundation Model to Production Endpoint: A Practitioner's Guide to OpenShift AI"
>
> Large language models are transforming enterprise applications, but the path from a downloaded foundation model to a reliable, scalable production endpoint remains unclear for most teams. This workshop bridges that gap using Red Hat OpenShift AI. Participants will fine-tune a foundation model on domain-specific data, deploy it as a scalable inference endpoint, and integrate it into a working application — all on a managed Kubernetes platform they don't need to be experts in. We'll also explore retrieval-augmented generation (RAG) to ground model responses in organizational knowledge. Attendees leave with a repeatable pattern for operationalizing LLMs on OpenShift.

## Follow-up Details (feed in when asked)

- Audience: data scientists and ML engineers, comfortable with Python and Jupyter but not Kubernetes
- Use InstructLab for fine-tuning with synthetic data generation
- Model serving via vLLM on RHOAI model serving
- GPU nodes required — at least 1x A10G or equivalent
- The "build an app" module should use LangChain to wire the model into a simple chatbot
- Targeting RH1 content
