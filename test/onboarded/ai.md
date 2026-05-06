# Test Prompt: Onboarded — AI

## Initial Prompt

> Workshop on fine-tuning and serving a custom LLM using Red Hat OpenShift AI. Should take someone from "I have a base model and some training data" to "I have a model endpoint my application can call." RHDP Published, targeting RH1 content.

## Follow-up Details (feed in when asked)

- Audience: data scientists and ML engineers, comfortable with Python and Jupyter but not Kubernetes
- Use InstructLab for fine-tuning with synthetic data generation
- Model serving via vLLM on RHOAI model serving
- Include a RAG module — connect the served model to a vector DB (pgvector or Milvus)
- GPU nodes required — at least 1x A10G or equivalent
- Should cover RHOAI dashboard, data science projects, pipelines
- The "build an app" module should use LangChain to wire the model into a simple chatbot
