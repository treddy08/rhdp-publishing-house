#!/usr/bin/env python3
"""
Publishing House - Minimal Workspace Provisioner
NO DATABASE - Just provisions workspace and returns metadata
Designed to be called by RHDH Software Template
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from kubernetes import client, config
from datetime import datetime

app = FastAPI(title="PH Workspace Provisioner (Stateless)")

# Environment variables (from K8s Secret)
LITELLM_URL = os.getenv("LITELLM_URL", "https://litellm.example.com")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY")


class ProvisionRequest(BaseModel):
    """Request from RHDH template"""
    project_name: str
    user_id: str
    user_email: str
    repo_url: str
    repo_branch: str = "main"


class ProvisionResponse(BaseModel):
    """Response to RHDH template (stored in catalog annotations)"""
    workspace_url: str
    workspace_name: str
    workspace_namespace: str
    maas_key_alias: str
    provisioned_at: str


@app.post("/provision", response_model=ProvisionResponse)
async def provision_workspace(req: ProvisionRequest):
    """
    Provision workspace with MaaS key.

    Steps:
    1. Call LiteLLM to provision key
    2. Create K8s namespace
    3. Create DevWorkspace CR with key injected
    4. Return metadata (RHDH stores in catalog)

    NO DATABASE - stateless operation
    """

    # 1. Use hardcoded MaaS key (TODO: implement dynamic provisioning)
    key_alias = f"ph-{req.user_id}-{req.project_name[:20].lower().replace(' ', '-')}"

    # Hardcoded for now - will implement dynamic provisioning later
    maas_key = os.getenv("MAAS_API_KEY", "sk-1234-hardcoded-key")

    # 2. Create K8s resources
    workspace_name = f"ph-{req.project_name[:30].lower().replace(' ', '-')}"
    workspace_namespace = f"devworkspace-{req.user_id}"

    try:
        # Load in-cluster K8s config (runs in pod)
        config.load_incluster_config()
        core_api = client.CoreV1Api()
        custom_api = client.CustomObjectsApi()

        # Create namespace (ignore if exists)
        try:
            core_api.create_namespace(
                body=client.V1Namespace(
                    metadata=client.V1ObjectMeta(
                        name=workspace_namespace,
                        labels={"app.kubernetes.io/managed-by": "publishing-house"}
                    )
                )
            )
        except client.rest.ApiException as e:
            if e.status != 409:  # 409 = already exists
                raise

        # Create DevWorkspace CR
        devworkspace = {
            "apiVersion": "workspace.devfile.io/v1alpha2",
            "kind": "DevWorkspace",
            "metadata": {
                "name": workspace_name,
                "namespace": workspace_namespace,
                "labels": {
                    "app.kubernetes.io/managed-by": "publishing-house",
                    "app.kubernetes.io/created-by": "rhdh"
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
                                "remotes": {"origin": req.repo_url},
                                "checkoutFrom": {"revision": req.repo_branch}
                            }
                        }
                    ],
                    "components": [
                        {
                            "name": "dev",
                            "container": {
                                "image": "quay.io/rhpds/publishing-house-udi:latest",
                                "memoryLimit": "4Gi",
                                "cpuLimit": "2",
                                "env": [
                                    {"name": "MAAS_API_KEY", "value": maas_key},
                                    {"name": "PROJECT_NAME", "value": req.project_name},
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
                    "events": {"postStart": ["post-start"]}
                }
            }
        }

        custom_api.create_namespaced_custom_object(
            group="workspace.devfile.io",
            version="v1alpha2",
            namespace=workspace_namespace,
            plural="devworkspaces",
            body=devworkspace
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DevWorkspace creation failed: {str(e)}"
        )

    # 3. Construct workspace URL
    # Pattern: https://{workspace-name}-{namespace}.apps.{cluster-domain}
    cluster_domain = "cluster-5hfx8.dynamic2.redhatworkshops.io"
    workspace_url = f"https://{workspace_name}-{workspace_namespace}.apps.{cluster_domain}"

    # 4. Return metadata (RHDH stores in catalog annotations)
    return ProvisionResponse(
        workspace_url=workspace_url,
        workspace_name=workspace_name,
        workspace_namespace=workspace_namespace,
        maas_key_alias=key_alias,
        provisioned_at=datetime.utcnow().isoformat()
    )


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "ph-workspace-provisioner"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
