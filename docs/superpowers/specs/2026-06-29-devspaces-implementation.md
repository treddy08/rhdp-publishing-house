# Dev Spaces Integration — Implementation Spec

**Date:** 2026-06-29
**Status:** Implementation Ready
**Parent Spec:** [2026-05-15-hosted-workspace-design.md](./2026-05-15-hosted-workspace-design.md)
**Jira:** [RHDPCD-44](https://redhat.atlassian.net/browse/RHDPCD-44)

## Purpose

This spec defines the **concrete implementation** of the Dev Spaces integration for Publishing House. The parent spec (2026-05-15) established the overall design. This spec details the database schema, service architecture, API contracts, and deployment approach based on how AgnosticV currently deploys Dev Spaces.

---

## Architecture Overview

### Simple Flow

```
User clicks "Launch Workspace" on project page
  ↓
Portal backend:
  1. Creates MaaS API key via LiteLLM
  2. Creates DevWorkspace CR in Kubernetes
  3. Saves mapping to database
  ↓
User redirected to browser VS Code
Claude Code pre-configured and ready
```

### The 3 Core Components

1. **Custom UDI Image** — VS Code + Claude Code CLI + PH skills (pre-baked container)
2. **Portal Backend Services** — Orchestrates workspace creation and key provisioning
3. **PostgreSQL Database** — Stores workspace → user → key mappings

---

## Database Schema

### New Table: `workspaces`

```sql
CREATE TABLE workspaces (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Project reference
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- User identification
    user_id VARCHAR NOT NULL,              -- e.g., "treddy"
    user_email VARCHAR NOT NULL,           -- e.g., "treddy@redhat.com"
    
    -- Dev Spaces workspace references
    workspace_id VARCHAR NOT NULL,         -- DevWorkspace UID from K8s
    workspace_namespace VARCHAR NOT NULL,  -- e.g., "devworkspace-treddy"
    workspace_name VARCHAR NOT NULL,       -- e.g., "ph-abc123ef"
    workspace_url VARCHAR NOT NULL,        -- Browser URL for redirect
    
    -- MaaS key references (for revocation)
    maas_key_id VARCHAR NOT NULL,          -- LiteLLM key ID
    maas_key_alias VARCHAR NOT NULL,       -- e.g., "ph-treddy-abc123ef"
    
    -- Audit trail
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uq_workspace_project_user UNIQUE(project_id, user_id)
);

-- Indexes for lookups
CREATE INDEX ix_workspace_user_id ON workspaces(user_id);
CREATE INDEX ix_workspace_user_email ON workspaces(user_email);
CREATE INDEX ix_workspace_maas_key_alias ON workspaces(maas_key_alias);
```

### New Table: `workspace_key_history`

**Purpose:** Maintain audit trail of all MaaS keys provisioned for a workspace, including expired/rotated keys.

```sql
CREATE TABLE workspace_key_history (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Workspace reference
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Key details
    maas_key_id VARCHAR NOT NULL,          -- LiteLLM key ID
    maas_key_alias VARCHAR NOT NULL,       -- e.g., "ph-treddy-abc123ef"
    
    -- Lifecycle tracking
    provisioned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expired_at TIMESTAMP,                  -- When key expired (null if still active)
    revoked_at TIMESTAMP,                  -- When key was manually revoked (null if expired naturally)
    revocation_reason VARCHAR,             -- "expired", "workspace_deleted", "user_requested", "security_rotation"
    
    -- Key metadata snapshot
    duration VARCHAR NOT NULL,             -- "30d", "7d"
    models JSONB NOT NULL,                 -- List of models this key had access to
    
    -- Audit info
    is_current BOOLEAN NOT NULL DEFAULT TRUE,  -- Only one current key per workspace
    
    -- Constraints
    CONSTRAINT uq_one_current_key_per_workspace 
        EXCLUDE USING gist (workspace_id WITH =) 
        WHERE (is_current = TRUE)
);

-- Indexes for audit queries
CREATE INDEX ix_key_history_workspace_id ON workspace_key_history(workspace_id);
CREATE INDEX ix_key_history_maas_key_id ON workspace_key_history(maas_key_id);
CREATE INDEX ix_key_history_is_current ON workspace_key_history(is_current) WHERE is_current = TRUE;
CREATE INDEX ix_key_history_expired_at ON workspace_key_history(expired_at) WHERE expired_at IS NOT NULL;
```

### Why Each Field

#### `workspaces` Table

| Field | Purpose | Used For |
|-------|---------|----------|
| `user_id` | Short username from OAuth | K8s namespace naming, lookups |
| `user_email` | Full email for identification | Support, audit trail, LiteLLM metadata |
| `workspace_namespace` | K8s namespace where DevWorkspace lives | Deletion without K8s list query |
| `workspace_name` | K8s resource name | Direct CR deletion |
| `maas_key_id` | **Current active** LiteLLM key ID | Primary deletion method |
| `maas_key_alias` | Human-readable key name | Fallback deletion, troubleshooting |

#### `workspace_key_history` Table

| Field | Purpose | Used For |
|-------|---------|----------|
| `provisioned_at` | When key was created | Audit trail, lifespan calculation |
| `expired_at` | **Natural expiration** (reached TTL) | Distinguish natural expiry from manual revocation |
| `revoked_at` | **Manual revocation** (LiteLLM API call) | Track when key was actively revoked |
| `revocation_reason` | Why key was revoked/expired | Security audits, compliance |
| `is_current` | Only one current key per workspace | Fast lookup of active key |
| `models` | Snapshot of model access | Audit what models were available |

**Timestamp semantics:**

- **`expired_at` only**: Key reached natural TTL (30d), not yet revoked from LiteLLM
- **`revoked_at` only**: Key manually revoked before expiration (workspace deleted, security rotation)
- **Both set**: Key expired naturally, then revoked from LiteLLM during rotation

**Key lifecycle scenarios:**

| Scenario | `expired_at` | `revoked_at` | `revocation_reason` |
|----------|-------------|-------------|---------------------|
| **Natural expiry + auto-rotation** | `NOW()` | `NOW()` (after revoke call) | `"expired"` |
| **Workspace deleted before expiry** | `NULL` | `NOW()` | `"workspace_deleted"` |
| **Security incident rotation** | `NULL` | `NOW()` | `"security_rotation"` |
| **User-requested rotation** | `NULL` | `NOW()` | `"user_requested"` |
| **Key still active** | `NULL` | `NULL` | `NULL` |

**Key rotation flow (natural expiration):**
1. User resumes workspace → Key validation fails (expired)
2. Mark old key: `is_current=false`, `expired_at=NOW()`, `revocation_reason='expired'`
3. Provision new key → New row in `workspace_key_history` with `is_current=true`
4. Update workspace table → `maas_key_id` points to new key
5. Revoke old key via LiteLLM → Set `revoked_at=NOW()` on old key record
6. Update DevWorkspace env vars → Workspace gets new key without restart

**Deletion flow (manual revocation):**
1. User deletes workspace
2. Mark current key: `is_current=false`, `revoked_at=NOW()`, `revocation_reason='workspace_deleted'`
3. Revoke key via LiteLLM
4. Delete workspace CR and namespace
5. Delete workspace record (cascades to history if configured, or keep for audit)

This maintains **complete audit trail** distinguishing natural expiration from manual revocation.

### Alembic Migration

```python
# alembic/versions/xxx_add_workspaces_table.py

"""Add workspaces table for Dev Spaces integration

Revision ID: xxx
Revises: yyy
Create Date: 2026-06-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None

def upgrade():
    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('user_email', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('workspace_namespace', sa.String(), nullable=False),
        sa.Column('workspace_name', sa.String(), nullable=False),
        sa.Column('workspace_url', sa.String(), nullable=False),
        sa.Column('maas_key_id', sa.String(), nullable=False),
        sa.Column('maas_key_alias', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_workspace_project_user')
    )
    
    op.create_index('ix_workspace_user_id', 'workspaces', ['user_id'])
    op.create_index('ix_workspace_user_email', 'workspaces', ['user_email'])
    op.create_index('ix_workspace_maas_key_alias', 'workspaces', ['maas_key_alias'])
    
    # Create workspace_key_history table for audit trail
    op.create_table(
        'workspace_key_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('maas_key_id', sa.String(), nullable=False),
        sa.Column('maas_key_alias', sa.String(), nullable=False),
        sa.Column('provisioned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expired_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revocation_reason', sa.String(), nullable=True),
        sa.Column('duration', sa.String(), nullable=False),
        sa.Column('models', postgresql.JSONB(), nullable=False),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )
    
    op.create_index('ix_key_history_workspace_id', 'workspace_key_history', ['workspace_id'])
    op.create_index('ix_key_history_maas_key_id', 'workspace_key_history', ['maas_key_id'])
    op.create_index('ix_key_history_is_current', 'workspace_key_history', ['is_current'], 
                    postgresql_where=sa.text('is_current = true'))
    op.create_index('ix_key_history_expired_at', 'workspace_key_history', ['expired_at'],
                    postgresql_where=sa.text('expired_at IS NOT NULL'))

def downgrade():
    op.drop_table('workspace_key_history')
    op.drop_table('workspaces')
```

### SQLAlchemy Models

```python
# app/models/workspace.py

from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    workspace_id = Column(String, nullable=False)
    workspace_namespace = Column(String, nullable=False)
    workspace_name = Column(String, nullable=False)
    workspace_url = Column(String, nullable=False)
    maas_key_id = Column(String, nullable=False)  # Current active key
    maas_key_alias = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    key_history = relationship("WorkspaceKeyHistory", back_populates="workspace", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_workspace_project_user"),
    )


class WorkspaceKeyHistory(Base):
    __tablename__ = "workspace_key_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    maas_key_id = Column(String, nullable=False, index=True)
    maas_key_alias = Column(String, nullable=False)
    provisioned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expired_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String, nullable=True)  # "expired", "workspace_deleted", "user_requested", "security_rotation"
    duration = Column(String, nullable=False)  # "30d", "7d"
    models = Column(JSONB, nullable=False)  # ["claude-sonnet-4-5"]
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="key_history")
```

**Usage example:**

```python
# Get current key for a workspace
workspace = db.query(Workspace).filter_by(project_id=pid, user_id=uid).first()
current_key = db.query(WorkspaceKeyHistory).filter_by(
    workspace_id=workspace.id,
    is_current=True
).first()

# Get full key rotation history
all_keys = db.query(WorkspaceKeyHistory).filter_by(
    workspace_id=workspace.id
).order_by(WorkspaceKeyHistory.provisioned_at.desc()).all()

# Audit query: Find all expired keys in last 30 days
from datetime import timedelta
expired_keys = db.query(WorkspaceKeyHistory).filter(
    WorkspaceKeyHistory.expired_at >= datetime.utcnow() - timedelta(days=30),
    WorkspaceKeyHistory.revocation_reason == "expired"
).all()
```

---

## Backend Services

### Service Architecture

Three new service classes following existing Central patterns (`RCARSClient`, `GitHubClient`):

```
WorkspaceManager (orchestrator)
    ├─→ LiteLLMClient (MaaS key provisioning)
    ├─→ DevSpacesClient (K8s DevWorkspace management)
    └─→ Database (workspace record CRUD)
```

### 1. LiteLLMClient

**Purpose:** Interact with LiteLLM REST API for virtual key management

**Pattern:** Mirrors `rhpds.litellm_virtual_keys` Ansible role API calls

```python
# app/services/litellm_client.py

import httpx
from typing import Optional
from app.core.config import settings
from app.core.exceptions import KeyExpired

class LiteLLMClient:
    """Client for LiteLLM REST API (MaaS virtual key management)"""
    
    def __init__(self):
        self.base_url = settings.LITELLM_URL
        self.master_key = settings.LITELLM_MASTER_KEY
        self.timeout = 30.0
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Authorization": f"Bearer {self.master_key}"}
        )
    
    async def provision_key(
        self,
        alias: str,
        user_id: str,
        user_email: str,
        duration: str,  # "7d", "30d"
        models: list[str],
        metadata: dict
    ) -> dict:
        """
        Provision a new virtual key via LiteLLM
        
        POST /key/generate
        
        Returns:
            {
                "key": "sk-...",           # The actual API key
                "key_id": "key_123...",    # LiteLLM internal ID
                "expires": "2026-07-29T..."
            }
        """
        response = await self.client.post(
            f"{self.base_url}/key/generate",
            json={
                "key_alias": alias,
                "duration": duration,
                "models": models,
                "metadata": {
                    **metadata,
                    "owner": user_email,
                    "created_by": "publishing-house"
                },
                "max_budget": None  # Unlimited for PH users
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def validate_key(self, key_id: str) -> bool:
        """
        Check if a key is still valid
        
        GET /key/info?key_id={key_id}
        
        Raises KeyExpired if key is not found or expired
        """
        response = await self.client.get(
            f"{self.base_url}/key/info",
            params={"key_id": key_id}
        )
        
        if response.status_code == 404:
            raise KeyExpired(f"Key {key_id} expired or not found")
        
        response.raise_for_status()
        return True
    
    async def revoke_key(self, key_id: str):
        """
        Revoke a virtual key
        
        POST /key/delete
        """
        response = await self.client.post(
            f"{self.base_url}/key/delete",
            json={"keys": [key_id]}
        )
        response.raise_for_status()
    
    async def revoke_by_alias(self, alias: str):
        """
        Revoke key by alias (fallback method)
        
        Uses the same endpoint but with alias lookup
        """
        # Implementation depends on LiteLLM version
        # May need to list keys by alias first, then delete by ID
        pass
```

**Configuration (app/core/config.py):**

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # LiteLLM (MaaS) settings
    LITELLM_URL: str
    LITELLM_MASTER_KEY: str  # Loaded from K8s Secret
    LITELLM_KEY_DURATION: str = "30d"
    LITELLM_MODELS: list[str] = ["claude-sonnet-4-5"]
```

**Security: LiteLLM Master Key Storage**

The LiteLLM master key is **never stored in code or environment variables**. It is securely stored in an OpenShift Secret with access restricted to the Publishing House application pod only.

```yaml
# manifests/secrets/litellm-credentials.yaml
apiVersion: v1
kind: Secret
metadata:
  name: litellm-credentials
  namespace: publishing-house-central-dev
type: Opaque
stringData:
  master-key: "sk-1234..."  # LiteLLM master key (set manually or via Ansible vault)
```

**Secret mounted to backend pod:**

```yaml
# manifests/deployment-backend.yaml (excerpt)
spec:
  template:
    spec:
      containers:
      - name: backend
        env:
        - name: LITELLM_MASTER_KEY
          valueFrom:
            secretKeyRef:
              name: litellm-credentials
              key: master-key
```

**Access control:**

- Secret accessible only to pods in `publishing-house-central-dev` namespace
- No other applications can read this Secret
- Secret not logged or exposed in pod specs
- Rotation: Update Secret, restart pods (no code changes required)

### 2. DevSpacesClient

**Purpose:** Manage DevWorkspace CRs via Kubernetes API

**Pattern:** Based on AgnosticV `ocp4_workload_devspaces` role

```python
# app/services/devspaces_client.py

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Optional

class DevSpacesClient:
    """Client for Dev Spaces API (DevWorkspace CR management)"""
    
    def __init__(self):
        # Use in-cluster config (ServiceAccount token)
        config.load_incluster_config()
        self.custom_api = client.CustomObjectsApi()
        self.core_api = client.CoreV1Api()
    
    async def create_workspace(
        self,
        name: str,
        namespace: str,
        repo_url: str,
        repo_branch: str,
        env_vars: dict
    ) -> dict:
        """
        Create a DevWorkspace CR
        
        Returns:
            {
                "workspace_id": "uid-from-k8s",
                "workspace_url": "https://..."
            }
        """
        
        # 1. Create namespace if not exists
        try:
            self.core_api.create_namespace(
                body=client.V1Namespace(
                    metadata=client.V1ObjectMeta(name=namespace)
                )
            )
        except ApiException as e:
            if e.status != 409:  # 409 = Already exists
                raise
        
        # 2. Create DevWorkspace CR
        devworkspace_manifest = {
            "apiVersion": "workspace.devfile.io/v1alpha2",
            "kind": "DevWorkspace",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {
                    "app.kubernetes.io/managed-by": "publishing-house"
                }
            },
            "spec": {
                "routingClass": "che",
                "started": True,
                "contributions": [
                    {
                        "name": "ide",
                        "uri": "http://devspaces-dashboard.openshift-devspaces.svc.cluster.local:8080/dashboard/api/editors/devfile?che-editor=che-incubator/che-code/latest"
                    }
                ],
                "template": {
                    "projects": [
                        {
                            "name": "project",
                            "git": {
                                "remotes": {"origin": repo_url},
                                "checkoutFrom": {"revision": repo_branch}
                            }
                        }
                    ],
                    "components": [
                        {
                            "name": "dev",
                            "container": {
                                "image": "quay.io/rhpds/ph-udi:latest",
                                "memoryLimit": "4Gi",
                                "cpuLimit": "2",
                                "env": [
                                    {"name": k, "value": v}
                                    for k, v in env_vars.items()
                                ]
                            }
                        }
                    ],
                    "commands": [
                        {
                            "id": "post-start",
                            "exec": {
                                "component": "dev",
                                "commandLine": "/opt/ph/scripts/workspace-startup.sh",
                                "workingDir": "/projects"
                            }
                        }
                    ],
                    "events": {
                        "postStart": ["post-start"]
                    }
                }
            }
        }
        
        result = self.custom_api.create_namespaced_custom_object(
            group="workspace.devfile.io",
            version="v1alpha2",
            namespace=namespace,
            plural="devworkspaces",
            body=devworkspace_manifest
        )
        
        workspace_id = result["metadata"]["uid"]
        workspace_url = self._construct_workspace_url(name, namespace)
        
        return {
            "workspace_id": workspace_id,
            "workspace_url": workspace_url
        }
    
    def _construct_workspace_url(self, name: str, namespace: str) -> str:
        """
        Construct workspace URL from Dev Spaces routing pattern
        
        Pattern: https://{name}-{namespace}.apps.{cluster-domain}
        """
        cluster_domain = "ocpv-infra01.dal12.infra.demo.redhat.com"
        return f"https://{name}-{namespace}.apps.{cluster_domain}"
    
    async def get_workspace_status(self, namespace: str, name: str) -> Optional[str]:
        """
        Get workspace status from K8s
        
        Returns: "Running", "Stopped", "Starting", or None if not found
        """
        try:
            ws = self.custom_api.get_namespaced_custom_object(
                group="workspace.devfile.io",
                version="v1alpha2",
                namespace=namespace,
                plural="devworkspaces",
                name=name
            )
            return ws.get("status", {}).get("phase", "Unknown")
        except ApiException as e:
            if e.status == 404:
                return None
            raise
    
    async def start_workspace(self, namespace: str, name: str):
        """
        Start a stopped workspace by patching started: true
        """
        patch = {"spec": {"started": True}}
        
        self.custom_api.patch_namespaced_custom_object(
            group="workspace.devfile.io",
            version="v1alpha2",
            namespace=namespace,
            plural="devworkspaces",
            name=name,
            body=patch
        )
    
    async def update_env_vars(self, namespace: str, name: str, env_vars: dict):
        """
        Update environment variables in a DevWorkspace
        
        Used for key rotation - updates MAAS_API_KEY after reprovisioning
        """
        # Get current DevWorkspace
        ws = self.custom_api.get_namespaced_custom_object(
            group="workspace.devfile.io",
            version="v1alpha2",
            namespace=namespace,
            plural="devworkspaces",
            name=name
        )
        
        # Update env vars in the dev container component
        components = ws["spec"]["template"]["components"]
        for component in components:
            if component["name"] == "dev" and "container" in component:
                env_list = component["container"].get("env", [])
                
                # Update or add each env var
                for key, value in env_vars.items():
                    # Find existing env var
                    found = False
                    for env_item in env_list:
                        if env_item["name"] == key:
                            env_item["value"] = value
                            found = True
                            break
                    
                    # Add new env var if not found
                    if not found:
                        env_list.append({"name": key, "value": value})
                
                component["container"]["env"] = env_list
        
        # Patch the DevWorkspace
        self.custom_api.patch_namespaced_custom_object(
            group="workspace.devfile.io",
            version="v1alpha2",
            namespace=namespace,
            plural="devworkspaces",
            name=name,
            body=ws
        )
    
    async def delete_workspace(self, namespace: str, name: str):
        """
        Delete DevWorkspace CR and namespace
        """
        # Delete DevWorkspace
        try:
            self.custom_api.delete_namespaced_custom_object(
                group="workspace.devfile.io",
                version="v1alpha2",
                namespace=namespace,
                plural="devworkspaces",
                name=name
            )
        except ApiException as e:
            if e.status != 404:
                raise
        
        # Delete namespace (will cascade delete workspace resources)
        try:
            self.core_api.delete_namespace(name=namespace)
        except ApiException as e:
            if e.status != 404:
                raise
```

### 3. WorkspaceManager

**Purpose:** Orchestrates LiteLLM + DevSpaces + Database

```python
# app/services/workspace_manager.py

from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.litellm_client import LiteLLMClient
from app.services.devspaces_client import DevSpacesClient
from app.models.workspace import Workspace
from app.core.config import settings
from app.core.exceptions import WorkspaceNotFound

class WorkspaceInfo(BaseModel):
    """Workspace info returned to API"""
    url: str
    status: str

class WorkspaceManager:
    """Orchestrates workspace lifecycle"""
    
    def __init__(
        self,
        litellm: LiteLLMClient,
        devspaces: DevSpacesClient,
        db: Session
    ):
        self.litellm = litellm
        self.devspaces = devspaces
        self.db = db
    
    async def create_workspace(
        self,
        project_id: str,
        user_id: str,
        user_email: str,
        repo_url: str,
        repo_branch: str = "main"
    ) -> WorkspaceInfo:
        """
        Create workspace + provision MaaS key + store in DB
        
        Steps:
          1. Provision MaaS key via LiteLLM
          2. Create DevWorkspace with key injected as env var
          3. Save record to database
          4. Return workspace URL for redirect
        """
        
        # 1. Provision MaaS key
        key_alias = f"ph-{user_id}-{project_id[:8]}"
        
        key_result = await self.litellm.provision_key(
            alias=key_alias,
            user_id=user_id,
            user_email=user_email,
            duration=settings.LITELLM_KEY_DURATION,
            models=settings.LITELLM_MODELS,
            metadata={
                "project_id": project_id,
                "user_id": user_id
            }
        )
        
        # 2. Create Dev Spaces workspace
        workspace_name = f"ph-{project_id[:8]}"
        workspace_namespace = f"devworkspace-{user_id}"
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        ws_result = await self.devspaces.create_workspace(
            name=workspace_name,
            namespace=workspace_namespace,
            repo_url=repo_url,
            repo_branch=repo_branch,
            env_vars={
                "MAAS_API_KEY": key_result["key"],
                "MCP_ENDPOINT": settings.MCP_ENDPOINT_URL,
                "LITELLM_URL": settings.LITELLM_URL,
                "PROJECT_ID": project_id,
                "PROJECT_REPO_NAME": repo_name
            }
        )
        
        # 3. Store in database
        workspace = Workspace(
            project_id=project_id,
            user_id=user_id,
            user_email=user_email,
            workspace_id=ws_result["workspace_id"],
            workspace_namespace=workspace_namespace,
            workspace_name=workspace_name,
            workspace_url=ws_result["workspace_url"],
            maas_key_id=key_result["key_id"],
            maas_key_alias=key_alias
        )
        
        self.db.add(workspace)
        self.db.flush()  # Get workspace.id
        
        # 4. Record key in audit history
        key_history = WorkspaceKeyHistory(
            workspace_id=workspace.id,
            maas_key_id=key_result["key_id"],
            maas_key_alias=key_alias,
            duration=settings.LITELLM_KEY_DURATION,
            models=settings.LITELLM_MODELS,
            is_current=True
        )
        
        self.db.add(key_history)
        self.db.commit()
        self.db.refresh(workspace)
        
        return WorkspaceInfo(
            url=ws_result["workspace_url"],
            status="starting"
        )
    
    async def get_workspace(
        self,
        project_id: str,
        user_id: str
    ) -> Optional[WorkspaceInfo]:
        """
        Get workspace info from database
        
        Returns None if workspace doesn't exist
        """
        workspace = self.db.query(Workspace).filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()
        
        if not workspace:
            return None
        
        # Optional: Query K8s for live status
        status = await self.devspaces.get_workspace_status(
            workspace.workspace_namespace,
            workspace.workspace_name
        )
        
        return WorkspaceInfo(
            url=workspace.workspace_url,
            status=status or "unknown"
        )
    
    async def resume_workspace(
        self,
        project_id: str,
        user_id: str
    ) -> WorkspaceInfo:
        """
        Resume a stopped workspace
        
        Steps:
          1. Get workspace record from DB
          2. Validate MaaS key (reprovision if expired)
          3. Start workspace
          4. Return URL
        """
        workspace = self.db.query(Workspace).filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()
        
        if not workspace:
            raise WorkspaceNotFound(f"No workspace for project {project_id}")
        
        # Validate key
        try:
            await self.litellm.validate_key(workspace.maas_key_id)
        except KeyExpired:
            # Key expired - rotate to new key with full audit trail
            
            # 1. Mark old key as expired in history
            old_key_record = self.db.query(WorkspaceKeyHistory).filter_by(
                workspace_id=workspace.id,
                is_current=True
            ).first()
            
            if old_key_record:
                old_key_record.is_current = False
                old_key_record.expired_at = datetime.utcnow()
                old_key_record.revocation_reason = "expired"
            
            # 2. Provision new key
            new_key = await self.litellm.provision_key(
                alias=workspace.maas_key_alias,  # Keep same alias
                user_id=user_id,
                user_email=workspace.user_email,
                duration=settings.LITELLM_KEY_DURATION,
                models=settings.LITELLM_MODELS,
                metadata={"project_id": project_id}
            )
            
            # 3. Update workspace with new key
            workspace.maas_key_id = new_key["key_id"]
            
            # 4. Record new key in history
            new_key_record = WorkspaceKeyHistory(
                workspace_id=workspace.id,
                maas_key_id=new_key["key_id"],
                maas_key_alias=workspace.maas_key_alias,
                duration=settings.LITELLM_KEY_DURATION,
                models=settings.LITELLM_MODELS,
                is_current=True
            )
            self.db.add(new_key_record)
            
            # 5. Revoke old key via LiteLLM
            if old_key_record:
                try:
                    await self.litellm.revoke_key(old_key_record.maas_key_id)
                    old_key_record.revoked_at = datetime.utcnow()
                except Exception as e:
                    # Log but don't fail - key already expired anyway
                    pass
            
            # 6. Update workspace env vars via K8s patch
            await self.devspaces.update_env_vars(
                workspace.workspace_namespace,
                workspace.workspace_name,
                {"MAAS_API_KEY": new_key["key"]}
            )
            
            self.db.commit()
        
        # Start workspace
        await self.devspaces.start_workspace(
            workspace.workspace_namespace,
            workspace.workspace_name
        )
        
        return WorkspaceInfo(
            url=workspace.workspace_url,
            status="starting"
        )
    
    async def delete_workspace(
        self,
        project_id: str,
        user_id: str
    ):
        """
        Delete workspace + revoke MaaS key + remove DB record
        
        Steps:
          1. Delete DevWorkspace CR
          2. Revoke MaaS key
          3. Remove database record
        """
        workspace = self.db.query(Workspace).filter_by(
            project_id=project_id,
            user_id=user_id
        ).first()
        
        if not workspace:
            return  # Already deleted
        
        # 1. Mark current key as revoked in history (before deletion)
        current_key_record = self.db.query(WorkspaceKeyHistory).filter_by(
            workspace_id=workspace.id,
            is_current=True
        ).first()
        
        if current_key_record:
            current_key_record.is_current = False
            current_key_record.revoked_at = datetime.utcnow()  # Manual revocation, NOT expired_at
            current_key_record.revocation_reason = "workspace_deleted"
            # Note: expired_at remains NULL - this was manual revocation, not natural expiration
        
        # 2. Delete workspace from K8s
        await self.devspaces.delete_workspace(
            workspace.workspace_namespace,
            workspace.workspace_name
        )
        
        # 3. Revoke key from LiteLLM
        #    This calls: POST /key/delete with {"keys": [key_id]}
        #    Effect:
        #      - Immediately disables the key (no more API calls accepted)
        #      - LiteLLM marks key as deleted in their database
        #      - Key removed from active keys list
        #      - Any in-flight requests with this key will fail
        #      - Key no longer counts against quota limits
        await self.litellm.revoke_key(workspace.maas_key_id)
        
        # 4. Commit key_history updates BEFORE deleting workspace
        #    This preserves audit trail even if workspace record is deleted
        self.db.commit()
        
        # 5. Remove workspace record (does NOT cascade to key_history - see note below)
        self.db.delete(workspace)
        self.db.commit()
```

**Audit trail preservation:**

The `workspace_key_history` table uses `ON DELETE CASCADE` in the foreign key definition, which means deleting a workspace will cascade-delete its key history. For **compliance and audit purposes**, you may want to preserve key history even after workspace deletion.

**Two approaches:**

1. **Cascade delete (current spec)**: Key history deleted with workspace
   - Pros: Clean database, no orphaned records
   - Cons: Lose audit trail for compliance/security investigation

2. **Preserve history (recommended for production)**:
   - Change FK to `ON DELETE SET NULL` instead of `CASCADE`
   - Add `workspace_project_id` and `workspace_user_email` columns to `workspace_key_history` for orphaned record identification
   - Keep key history indefinitely for audit
   - Periodic cleanup job deletes history older than retention period (e.g., 90 days)

**Recommended for production:**

```sql
-- Modified FK constraint (no cascade)
ALTER TABLE workspace_key_history
  DROP CONSTRAINT workspace_key_history_workspace_id_fkey,
  ADD CONSTRAINT workspace_key_history_workspace_id_fkey 
    FOREIGN KEY (workspace_id) 
    REFERENCES workspaces(id) 
    ON DELETE SET NULL;

-- Add denormalized fields for orphaned records
ALTER TABLE workspace_key_history
  ADD COLUMN workspace_project_id UUID,
  ADD COLUMN workspace_user_email VARCHAR;
```

This allows querying key history even after workspace deletion: "Show all keys provisioned for user X in the last 90 days, including deleted workspaces."
```

---

## API Routes

**New endpoints:** `/api/v1/projects/{project_id}/workspace`

```python
# app/api/workspaces.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.workspace_manager import WorkspaceManager, WorkspaceInfo
from app.services.litellm_client import LiteLLMClient
from app.services.devspaces_client import DevSpacesClient
from app.models.project import Project

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/workspace",
    tags=["workspaces"]
)

def get_workspace_manager(db: Session = Depends(get_db)) -> WorkspaceManager:
    """Dependency injection for WorkspaceManager"""
    return WorkspaceManager(
        litellm=LiteLLMClient(),
        devspaces=DevSpacesClient(),
        db=db
    )

@router.post("", response_model=WorkspaceInfo)
async def create_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """
    Create and launch Dev Spaces workspace
    
    Returns workspace URL for redirect
    """
    # Get project repo URL
    project = manager.db.query(Project).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return await manager.create_workspace(
        project_id=project_id,
        user_id=current_user["user_id"],
        user_email=current_user["email"],
        repo_url=project.repo_url,
        repo_branch=project.repo_branch or "main"
    )

@router.get("", response_model=WorkspaceInfo)
async def get_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """
    Get workspace info + status
    
    Returns 404 if no workspace exists
    """
    workspace = await manager.get_workspace(
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return workspace

@router.post("/start", response_model=WorkspaceInfo)
async def resume_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """
    Resume stopped workspace
    
    Validates MaaS key and reprovisisions if expired
    """
    return await manager.resume_workspace(
        project_id=project_id,
        user_id=current_user["user_id"]
    )

@router.delete("", status_code=204)
async def delete_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    manager: WorkspaceManager = Depends(get_workspace_manager)
):
    """
    Delete workspace + revoke MaaS key
    """
    await manager.delete_workspace(
        project_id=project_id,
        user_id=current_user["user_id"]
    )

@router.get("/key-history", response_model=list[KeyHistoryInfo])
async def get_key_history(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get MaaS key rotation history for audit trail
    
    Returns all keys (current + expired/revoked) with timestamps
    """
    workspace = db.query(Workspace).filter_by(
        project_id=project_id,
        user_id=current_user["user_id"]
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    key_history = db.query(WorkspaceKeyHistory).filter_by(
        workspace_id=workspace.id
    ).order_by(WorkspaceKeyHistory.provisioned_at.desc()).all()
    
    return [
        KeyHistoryInfo(
            maas_key_id=key.maas_key_id,
            maas_key_alias=key.maas_key_alias,
            provisioned_at=key.provisioned_at,
            expired_at=key.expired_at,
            revoked_at=key.revoked_at,
            revocation_reason=key.revocation_reason,
            duration=key.duration,
            models=key.models,
            is_current=key.is_current
        )
        for key in key_history
    ]
```

**Response models:**

```python
# app/schemas/workspace.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class KeyHistoryInfo(BaseModel):
    maas_key_id: str
    maas_key_alias: str
    provisioned_at: datetime
    expired_at: Optional[datetime]
    revoked_at: Optional[datetime]
    revocation_reason: Optional[str]
    duration: str
    models: list[str]
    is_current: bool
```

**Register routes in `app/main.py`:**

```python
from app.api import workspaces

app.include_router(workspaces.router)
```

---

## LiteLLM Key Lifecycle Management

### Complete Key Lifecycle

Publishing House maintains **dual-system tracking** for MaaS keys:

1. **LiteLLM System** - Operational state (active/deleted)
2. **PH Database** - Complete audit trail (provisioned, expired, revoked)

### Key States Across Systems

| Event | LiteLLM State | PH Database State |
|-------|---------------|-------------------|
| **Workspace created** | Key active, accepting API calls | `workspace_key_history`: `is_current=true`, all timestamps NULL |
| **Key reaches TTL (30d)** | Key expired, rejects API calls | `expired_at=NOW()`, `revocation_reason='expired'` |
| **Auto-rotation on resume** | Old key deleted, new key active | Old: `revoked_at=NOW()`, `is_current=false`<br>New: `is_current=true` |
| **Workspace deleted** | Key deleted (POST /key/delete) | `revoked_at=NOW()`, `revocation_reason='workspace_deleted'` |

### LiteLLM API Operations

**Key Provisioning (Workspace Creation):**
```python
POST /key/generate
{
  "key_alias": "ph-treddy-abc123ef",
  "duration": "30d",
  "models": ["claude-sonnet-4-5"],
  "metadata": {
    "owner": "treddy@redhat.com",
    "project_id": "uuid",
    "created_by": "publishing-house"
  },
  "max_budget": null
}

Response:
{
  "key": "sk-...",           # Actual API key (injected to workspace)
  "key_id": "key_123...",    # LiteLLM internal ID (stored in DB)
  "expires": "2026-07-29"
}
```

**Key Validation (Workspace Resume):**
```python
GET /key/info?key_id=key_123

Response (valid):
{
  "key_id": "key_123",
  "alias": "ph-treddy-abc123ef",
  "status": "active",
  "expires": "2026-07-29"
}

Response (expired):
404 Not Found  # Triggers automatic rotation
```

**Key Revocation (Workspace Deletion):**
```python
POST /key/delete
{
  "keys": ["key_123"]
}

Effect on LiteLLM:
- Key immediately disabled (rejects all API calls)
- Key removed from active keys table
- Key marked as deleted in LiteLLM database
- Any in-flight requests fail with 401 Unauthorized
- Key no longer counts against quota/rate limits
- Deletion is permanent (cannot be undone)

Effect on PH Database:
- workspace_key_history.revoked_at = NOW()
- workspace_key_history.is_current = false
- workspace_key_history.revocation_reason = "workspace_deleted"
- Record preserved for audit (if using ON DELETE SET NULL)
```

### Why Dual Tracking?

**LiteLLM provides:**
- Operational key management (active/expired/deleted)
- API authentication and authorization
- Usage tracking and rate limiting
- Model access enforcement

**PH Database provides:**
- Complete audit trail (LiteLLM may not retain deleted key history)
- Compliance reporting (who provisioned what, when, why revoked)
- Security investigation (find all keys for a user/project)
- Retention policy enforcement (keep history 90+ days)
- Cross-workspace analytics (total keys provisioned, rotation frequency)

**Critical difference:** LiteLLM's `/key/delete` permanently removes the key from their system. Our `workspace_key_history` table preserves:
- When the key was provisioned
- What models it had access to
- When and why it was revoked
- Who owned it

This dual tracking ensures **compliance-ready audit trails** even after keys are deleted from LiteLLM.

---

## Custom UDI Image

### Base Image

```dockerfile
FROM registry.redhat.io/devspaces/udi-base-rhel10:latest
```

**Already includes:**
- VS Code Server
- oc CLI
- git
- Python 3.11+
- Node.js
- ansible (via pip)

### Containerfile

```dockerfile
# Containerfile for PH UDI
FROM registry.redhat.io/devspaces/udi-base-rhel10:latest

USER 0

# Install Claude Code CLI (fallback version)
RUN npm install -g @anthropic-ai/claude-code@latest

# Install Ansible collections
RUN ansible-galaxy collection install kubernetes.core community.general

# Pre-clone PH skills plugin
RUN mkdir -p /opt/ph && \
    git clone https://github.com/rhpds/rhdp-publishing-house-skills.git /opt/ph/skills

# Add workspace startup script
COPY workspace-startup.sh /opt/ph/scripts/workspace-startup.sh
RUN chmod +x /opt/ph/scripts/workspace-startup.sh

# Pre-configure MCP endpoint (can be overridden by env var)
ENV MCP_ENDPOINT=https://publishing-house-central-dev.apps.ocpv-infra01.dal12.infra.demo.redhat.com/mcp

USER 1001

LABEL \
    io.openshift.tags="devspaces,publishing-house,claude-code" \
    summary="Publishing House Universal Developer Image" \
    description="Custom UDI with Claude Code, PH skills, and tooling for RHDP content development"
```

### Startup Script

```bash
#!/bin/bash
# /opt/ph/scripts/workspace-startup.sh
# Runs automatically on workspace startup via DevWorkspace postStart event

set -e

echo "[PH] =========================================="
echo "[PH] Publishing House Workspace Initialization"
echo "[PH] =========================================="

# 1. Update CC CLI to latest
echo "[PH] Updating Claude Code CLI..."
npm update -g @anthropic-ai/claude-code 2>/dev/null || {
    echo "[PH] WARNING: Failed to update CC CLI, using pre-installed version"
}

# 2. Update PH skills to latest
echo "[PH] Updating PH skills..."
cd /opt/ph/skills && git pull --rebase --autostash || {
    echo "[PH] WARNING: Failed to update skills, using pre-cloned version"
}

# 3. Sync project repo
if [ -n "$PROJECT_REPO_NAME" ] && [ -d "/projects/${PROJECT_REPO_NAME}" ]; then
    echo "[PH] Syncing project repository..."
    cd "/projects/${PROJECT_REPO_NAME}"
    git pull --rebase --autostash || {
        echo "[PH] WARNING: Failed to sync project repo"
    }
else
    echo "[PH] No project repo to sync"
fi

# 4. Validate MaaS key
if [ -n "$MAAS_API_KEY" ] && [ -n "$LITELLM_URL" ]; then
    echo "[PH] Validating MaaS API key..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${MAAS_API_KEY}" \
        "${LITELLM_URL}/health" 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "[PH] ✓ MaaS key is valid"
    else
        echo "[PH] ⚠ WARNING: MaaS key validation failed (HTTP ${HTTP_CODE})"
        echo "[PH]   Restart workspace from PH portal to provision new key"
    fi
else
    echo "[PH] ⚠ WARNING: MaaS key not configured"
fi

# 5. Configure Claude Code environment
echo "[PH] Configuring Claude Code..."
export ANTHROPIC_API_KEY="${MAAS_API_KEY}"
export ANTHROPIC_BASE_URL="${LITELLM_URL}/v1"

# Link skills to CC config directory
mkdir -p ~/.config/claude-code/skills
ln -sf /opt/ph/skills ~/.config/claude-code/skills/publishing-house || true

echo "[PH] =========================================="
echo "[PH] ✓ Workspace ready!"
echo "[PH] =========================================="
```

### Build & Push

```bash
# Build image
podman build -t quay.io/rhpds/ph-udi:latest -f Containerfile .

# Push to registry
podman push quay.io/rhpds/ph-udi:latest
```

---

## Deployment

### Prerequisites

1. **Dev Spaces Operator Installed**

```bash
# Deploy via AgnosticV workload
cd ~/gpte/rhpds/agnosticv
ansible-playbook -i localhost, \
  roles/ocp4_workload_devspaces/tasks/workload.yml \
  -e ocp4_workload_devspaces_namespace=openshift-devspaces \
  -e ocp4_workload_devspaces_channel=stable
```

2. **Custom UDI Image Built**

```bash
# Build and push
cd rhdp-publishing-house-central/docker/ph-udi
podman build -t quay.io/rhpds/ph-udi:latest .
podman push quay.io/rhpds/ph-udi:latest
```

3. **LiteLLM Master Key Secret Created**

```bash
# Create Secret with LiteLLM master key
oc create secret generic litellm-credentials \
  --from-literal=master-key='sk-1234...' \
  -n publishing-house-central-dev

# Or via Ansible vault (recommended for production)
ansible-playbook ansible/deploy.yml \
  -e env=dev \
  --tags secrets \
  -e litellm_master_key='{{ vault_litellm_master_key }}'
```

**Security notes:**
- Secret is namespace-scoped (only accessible to `publishing-house-central-dev`)
- Master key never stored in git, environment files, or ConfigMaps
- Ansible vault encrypts the key in playbooks
- Key rotation: Update Secret + restart pods (no code changes)

4. **LiteLLM Accessible**

Network policy or route to allow Central namespace to reach LiteLLM endpoint.

5. **Service Account Permissions**

```yaml
# Grant Central SA permissions to manage DevWorkspaces
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: devworkspace-manager
rules:
- apiGroups: ["workspace.devfile.io"]
  resources: ["devworkspaces"]
  verbs: ["create", "get", "list", "delete", "patch"]
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["create", "delete"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: central-devworkspace-manager
subjects:
- kind: ServiceAccount
  name: publishing-house-central
  namespace: publishing-house-central-dev
roleRef:
  kind: ClusterRole
  name: devworkspace-manager
  apiGroup: rbac.authorization.k8s.io
```

### Ansible Deployment

Add to existing `ansible/deploy.yml`:

```yaml
# ansible/deploy.yml

- name: Deploy workspace service dependencies
  hosts: localhost
  tasks:
  
  - name: Create LiteLLM credentials Secret
    kubernetes.core.k8s:
      state: present
      definition:
        apiVersion: v1
        kind: Secret
        metadata:
          name: litellm-credentials
          namespace: "{{ namespace }}"
        type: Opaque
        stringData:
          master-key: "{{ litellm_master_key }}"
    tags: [secrets, deploy]
    no_log: true  # Don't log the Secret content
  
  - name: Apply DevWorkspace RBAC
    kubernetes.core.k8s:
      state: present
      definition: "{{ lookup('file', 'manifests/rbac/devworkspace-manager.yaml') }}"
    tags: [apply, rbac]
  
  - name: Run database migration
    kubernetes.core.k8s_exec:
      namespace: "{{ namespace }}"
      pod: "{{ backend_pod_name }}"
      command: alembic upgrade head
    tags: [migrate, deploy]
```

**Ansible vault for production:**

```yaml
# ansible/group_vars/dev/vault.yml (encrypted with ansible-vault)
vault_litellm_master_key: sk-production-master-key-here
```

Run deployment:

```bash
cd rhdp-publishing-house-central

# Full deploy with migration (includes Secret creation)
ansible-playbook ansible/deploy.yml \
  -e env=dev \
  -e litellm_master_key='sk-your-master-key' \
  --tags deploy

# Or use vault for production
ansible-playbook ansible/deploy.yml \
  -e env=prod \
  --ask-vault-pass \
  --tags deploy

# Just create/update Secret
ansible-playbook ansible/deploy.yml \
  -e env=dev \
  -e litellm_master_key='sk-your-master-key' \
  --tags secrets

# Just apply RBAC
ansible-playbook ansible/deploy.yml -e env=dev --tags rbac

# Just run migration
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

**Security checklist:**
- ✅ LiteLLM master key stored in K8s Secret (not git, not env files)
- ✅ Secret scoped to `publishing-house-central-dev` namespace only
- ✅ Production key encrypted with `ansible-vault`
- ✅ Secret not logged in Ansible output (`no_log: true`)
- ✅ Key rotation: update Secret + restart pods (no code deploy)

---

## Frontend Integration

### Project Detail Page

**Add button based on workspace state:**

```typescript
// components/ProjectDetail.tsx

interface WorkspaceButtonProps {
  projectId: string;
}

function WorkspaceButton({ projectId }: WorkspaceButtonProps) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    // Check if workspace exists
    fetch(`/api/v1/projects/${projectId}/workspace`)
      .then(res => res.ok ? res.json() : null)
      .then(setWorkspace)
      .catch(() => setWorkspace(null));
  }, [projectId]);
  
  const handleLaunch = async () => {
    setLoading(true);
    
    try {
      if (!workspace) {
        // Create new workspace
        const res = await fetch(`/api/v1/projects/${projectId}/workspace`, {
          method: 'POST'
        });
        const data = await res.json();
        window.location.href = data.url;
      } else {
        // Open existing workspace
        window.location.href = workspace.url;
      }
    } catch (err) {
      console.error('Failed to launch workspace:', err);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Button
      variant="secondary"
      onClick={handleLaunch}
      isLoading={loading}
    >
      {!workspace ? 'Launch Workspace' : 'Open Workspace'}
    </Button>
  );
}
```

**Button placement:** In the project header, next to "View in Git" button.

---

## Testing Plan

### Unit Tests

```python
# tests/services/test_workspace_manager.py

import pytest
from app.services.workspace_manager import WorkspaceManager

@pytest.mark.asyncio
async def test_create_workspace(mock_litellm, mock_devspaces, db_session):
    manager = WorkspaceManager(mock_litellm, mock_devspaces, db_session)
    
    result = await manager.create_workspace(
        project_id="test-uuid",
        user_id="treddy",
        user_email="treddy@redhat.com",
        repo_url="https://github.com/user/project.git"
    )
    
    assert result.url.startswith("https://")
    assert result.status == "starting"

@pytest.mark.asyncio
async def test_delete_workspace_revokes_key(mock_litellm, mock_devspaces, db_session):
    # Create workspace first
    manager = WorkspaceManager(mock_litellm, mock_devspaces, db_session)
    await manager.create_workspace(...)
    
    # Delete it
    await manager.delete_workspace(project_id="test-uuid", user_id="treddy")
    
    # Verify key was revoked
    assert mock_litellm.revoke_key.called
```

### Integration Tests

```python
# tests/integration/test_workspace_e2e.py

@pytest.mark.integration
async def test_workspace_creation_e2e(test_client, test_db):
    """Test full workspace creation flow"""
    
    # 1. Create workspace
    response = test_client.post("/api/v1/projects/test-id/workspace")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    
    # 2. Verify DB record
    workspace = test_db.query(Workspace).filter_by(project_id="test-id").first()
    assert workspace is not None
    assert workspace.maas_key_alias.startswith("ph-")
    
    # 3. Delete workspace
    response = test_client.delete("/api/v1/projects/test-id/workspace")
    assert response.status_code == 204
    
    # 4. Verify DB record removed
    workspace = test_db.query(Workspace).filter_by(project_id="test-id").first()
    assert workspace is None
```

---

## Open Questions & Future Work

### Out of Scope (Backlog)

From Jira ticket description:

- **Express mode lightweight execution** — Dev Spaces is heavy for one-off demos
- **Broader audience UX** — Onboarding for non-developers
- **Multi-project workspace support** — One workspace for all projects
- **Token usage dashboard** — Track MaaS consumption
- **Human-in-the-loop approval** — Approve destructive workspace actions
- **Mid-session key rotation** — Auto-reprovision expired keys without restart

### Implementation TODOs

- [ ] Workspace env var update mechanism (for key reprov isioning)
- [ ] Workspace idle timeout configuration
- [ ] Admin workspace cleanup job (delete stale workspaces)
- [ ] Metrics collection (workspace creation rate, MaaS usage)
- [ ] Error handling for K8s API failures
- [ ] Retry logic for LiteLLM API calls

---

## Success Criteria

**MVP is complete when:**

1. ✅ User can click "Launch Workspace" and land in browser VS Code
2. ✅ Claude Code CLI is pre-installed and configured
3. ✅ MaaS API key is provisioned automatically
4. ✅ PH skills plugin is available in workspace
5. ✅ Project git repo is cloned into workspace
6. ✅ User can delete workspace from portal
7. ✅ MaaS key is revoked on workspace deletion

**Success metrics:**

- Workspace creation time: <60 seconds from button click to VS Code ready
- Key provisioning success rate: >99%
- Database query latency: <10ms for workspace lookup
- Zero manual key management required by users

---

## References

- Parent spec: [2026-05-15-hosted-workspace-design.md](./2026-05-15-hosted-workspace-design.md)
- Jira ticket: [RHDPCD-44](https://redhat.atlassian.net/browse/RHDPCD-44)
- AgnosticV Dev Spaces workload: `core_workloads/roles/ocp4_workload_devspaces`
- LiteLLM virtual keys role: `rhpds.litellm_virtual_keys`
