# RCARS Service Auth Admin Guide

## Overview

The PH portal backend authenticates to the RCARS API using its Kubernetes ServiceAccount (SA) token. This is a cluster-internal, zero-configuration authentication mechanism -- Kubernetes manages token creation, rotation, and injection automatically.

RCARS validates incoming SA tokens via the Kubernetes TokenReview API and checks the authenticated identity against a configured allowlist. No secrets need to be created or rotated manually.

## How It Works

1. Kubernetes auto-mounts a projected SA token into the PH backend pod at `/var/run/secrets/kubernetes.io/serviceaccount/token`
2. The PH `RCARSClient` reads this token from the filesystem on every request (never cached, because K8s rotates tokens automatically)
3. The client sends the token as `Authorization: Bearer <sa-token>` to RCARS
4. RCARS middleware submits the token to the Kubernetes TokenReview API for validation
5. If the token is valid, RCARS checks the authenticated identity against its SA allowlist
6. If the identity is in the allowlist, the request proceeds; otherwise it is rejected

## SA Allowlist Configuration

The SA allowlist controls which service accounts are permitted to call the RCARS API directly (bypassing the OAuth proxy auth path).

### Current PH entry

```
system:serviceaccount:publishing-house-dev:default
```

This is the `default` ServiceAccount in the `publishing-house-dev` namespace, which the PH backend pod runs under.

### Adding or removing entries

Edit `ansible/vars/dev.yml` in the `rcars-advisory` repo:

```yaml
rcars_sa_allowlist:
  - "system:serviceaccount:publishing-house-dev:default"
  # Add additional SAs as needed:
  # - "system:serviceaccount:other-namespace:service-name"
```

The format for each entry is:

```
system:serviceaccount:<namespace>:<serviceaccount-name>
```

### Deploying changes

After editing the allowlist vars, run the RCARS Ansible deployer:

```bash
cd rcars-advisory/ansible && ansible-playbook deploy.yml -e @vars/dev.yml
```

This updates the `RCARS_SA_ALLOWLIST_STR` environment variable in the RCARS deployment and triggers a pod restart.

## Cross-Namespace DNS

The PH backend reaches RCARS via standard Kubernetes cross-namespace service DNS:

```
http://rcars-api.rcars-dev.svc.cluster.local:8080
```

This is the RCARS API ClusterIP Service in the `rcars-dev` namespace. No external Route is needed -- the call stays within the cluster.

### DNS pattern

```
<service-name>.<namespace>.svc.cluster.local:<port>
```

## Verification

### Verify cross-namespace connectivity

From the PH backend pod, test that RCARS is reachable:

```bash
oc exec deployment/ph-portal-backend -n publishing-house-dev -- \
  curl -s http://rcars-api.rcars-dev.svc.cluster.local:8080/api/v1/health
```

Expected response:

```json
{"status": "ok"}
```

### Verify SA token is being mounted

```bash
oc exec deployment/ph-portal-backend -n publishing-house-dev -- \
  cat /var/run/secrets/kubernetes.io/serviceaccount/token | head -c 50
```

This should print the first 50 characters of a JWT-formatted token.

### Verify SA identity

Check what SA the backend pod is running as:

```bash
oc get deployment ph-portal-backend -n publishing-house-dev \
  -o jsonpath='{.spec.template.spec.serviceAccountName}'
```

If empty, the pod uses the `default` SA.

### Verify RCARS allowlist includes PH SA

```bash
oc exec deployment/rcars-api -n rcars-dev -- env | grep SA_ALLOWLIST
```

The output should include `system:serviceaccount:publishing-house-dev:default`.

### Verify authenticated RCARS call

From the PH backend pod, test authentication end-to-end:

```bash
oc exec deployment/ph-portal-backend -n publishing-house-dev -- \
  bash -c 'TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token) && \
  curl -s -H "Authorization: Bearer $TOKEN" \
  http://rcars-api.rcars-dev.svc.cluster.local:8080/api/v1/health'
```

### NetworkPolicy checks

Verify no NetworkPolicies are blocking cross-namespace traffic:

```bash
# Check for NetworkPolicies in the RCARS namespace
oc get networkpolicy -n rcars-dev

# Check for NetworkPolicies in the PH namespace
oc get networkpolicy -n publishing-house-dev
```

If restrictive policies exist, ensure they allow ingress from the `publishing-house-dev` namespace to the `rcars-api` service on port 8080.

## Troubleshooting

### "Authentication required" from RCARS

**Cause:** The SA token is not being sent, or RCARS is not recognizing the token format.

**Check:**
1. Verify the SA token file exists in the pod (see verification commands above)
2. Verify the `RCARS_INTERNAL_URL` environment variable is set correctly in the PH backend deployment
3. Check RCARS logs for auth-related errors:
   ```bash
   oc logs deployment/rcars-api -n rcars-dev --tail=50 | grep -i auth
   ```

### "SA not in allowlist" from RCARS

**Cause:** The PH SA identity is not in the `RCARS_SA_ALLOWLIST_STR` environment variable.

**Fix:**
1. Verify the allowlist value (see verification commands above)
2. Ensure the entry matches exactly: `system:serviceaccount:publishing-house-dev:default`
3. If missing, add it to `rcars_sa_allowlist` in `ansible/vars/dev.yml` and redeploy RCARS

### DNS resolution failure

**Cause:** The cross-namespace service DNS name is incorrect, or the RCARS service does not exist.

**Check:**
```bash
# Verify RCARS service exists
oc get svc rcars-api -n rcars-dev

# Test DNS resolution from PH pod
oc exec deployment/ph-portal-backend -n publishing-house-dev -- \
  nslookup rcars-api.rcars-dev.svc.cluster.local
```

### Token rotation issues

SA tokens are automatically rotated by Kubernetes. The PH `RCARSClient` re-reads the token from the filesystem on every request, so rotation is transparent.

If you see intermittent auth failures that resolve on their own, this is likely a brief window during token rotation. No action is needed -- the next request will use the new token.

### Connection timeout to RCARS

**Cause:** RCARS pod is not running, or there is a network issue between namespaces.

**Check:**
```bash
# Verify RCARS pods are running
oc get pods -l app=rcars -n rcars-dev

# Check RCARS pod logs
oc logs deployment/rcars-api -n rcars-dev --tail=20
```

The PH `RCARSClient` retries transient failures 3 times with exponential backoff (1s, 2s, 4s). If RCARS is down for an extended period, the MCP tool returns a structured error and the intake skill offers to skip vetting.

## Related Documentation

- [RCARS Integration Architecture](../architecture/rcars-integration.md)
- [MCP Auth Admin Guide](mcp-auth.md)
- [Portal Deployment](portal-deployment.md)
