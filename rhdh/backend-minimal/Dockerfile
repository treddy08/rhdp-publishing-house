FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    httpx==0.26.0 \
    kubernetes==29.0.0 \
    pydantic==2.5.0

# Copy app
COPY workspace-provisioner.py .

# Run as non-root
RUN useradd -m -u 1001 provisioner
USER 1001

EXPOSE 8000

CMD ["python", "workspace-provisioner.py"]
