FROM registry.redhat.io/devspaces/udi-rhel8:latest

USER root

# Install Claude Code CLI
RUN curl -fsSL https://desktop.claude.ai/install.sh | sh

# Install git-lfs (often needed for showroom repos)
RUN dnf install -y git-lfs && dnf clean all

# Create workspace startup script directory
RUN mkdir -p /opt/ph/scripts

# Copy startup script
COPY workspace-startup.sh /opt/ph/scripts/workspace-startup.sh
RUN chmod +x /opt/ph/scripts/workspace-startup.sh

USER 10001

WORKDIR /projects
