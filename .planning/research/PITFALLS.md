# Pitfalls Research

**Domain:** AI-powered content lifecycle management -- MCP server integration, API key auth, cross-namespace K8s communication, express/disposable environment provisioning, Jira API integration, chatbot proxy UI
**Researched:** 2026-04-30
**Confidence:** HIGH (verified against Context7 FastMCP docs, official K8s docs, Atlassian developer docs, and multiple community post-mortems)

## Critical Pitfalls

### Pitfall 1: FastMCP Mount Path Double-Prefix (404 on /mcp/mcp)

**What goes wrong:**
The current `main.py` mounts FastMCP at `/mcp` via `app.mount("/mcp", mcp_server.streamable_http_app())`. FastMCP's `streamable_http_app()` internally registers its own `/mcp` route. The result is that the actual endpoint becomes `/mcp/mcp`, while clients attempting to reach `/mcp` get 404s. This is a documented, well-known issue (modelcontextprotocol/python-sdk#1367). The existing code has a fallback from `streamable_http_app()` to `http_app()` but neither solves the double-prefix problem without the correct `path` argument.

**Why it happens:**
FastMCP's ASGI sub-app pre-configures its own internal path prefix. When you mount a sub-app at `/mcp` in FastAPI/Starlette, the Starlette `Mount` strips `/mcp` from the request path before forwarding to the sub-app, but the sub-app then expects its own `/mcp` prefix on the remaining path. Developers assume the mount point IS the path.

**How to avoid:**
Use `mcp.http_app(path="/")` (not the default `/mcp`) when mounting at a prefix, OR use `mcp.http_app(path="/mcp")` and mount at `"/"`. The official FastMCP docs (Context7, verified) show the correct pattern:
```python
mcp_app = mcp.http_app(path="/")
app.mount("/mcp", mcp_app)
```
Alternatively, use `combine_lifespans` from `fastmcp.utilities.lifespan` to merge MCP and FastAPI lifespans properly.

**Warning signs:**
- CC users get 404 when hitting the configured MCP URL
- curl to `/mcp` returns "not found" but `/mcp/mcp` works
- MCP client logs show redirect loops (307 from trailing-slash normalization)

**Phase to address:**
Phase 1 (RCARS integration) -- this is the first thing that breaks when wiring up the MCP server for external access. Must be fixed before any API key auth or tool testing.

---

### Pitfall 2: FastMCP CORS Middleware Collision

**What goes wrong:**
The portal backend already has `CORSMiddleware` added to the top-level FastAPI app (see `main.py` line 49-55, currently allowing `http://localhost:3001`). When FastMCP is mounted as a sub-app, it adds its own CORS handling for OAuth discovery routes (`.well-known`). The two CORS layers conflict, producing duplicate headers, blocked OPTIONS preflight requests, and 404s on `.well-known` routes. This is documented in FastMCP issue #2139 and #2817.

**Why it happens:**
Starlette's CORS middleware processes ALL requests, including those destined for mounted sub-apps. FastMCP's internal CORS layer then adds a second set of headers. Browsers reject responses with duplicate `Access-Control-Allow-Origin` headers.

**How to avoid:**
Use the sub-app pattern: remove the top-level `CORSMiddleware` from the main FastAPI app. Instead, apply CORS middleware separately to each sub-app that needs it. FastMCP accepts a `middleware` parameter in `http_app()`:
```python
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

portal_middleware = [Middleware(CORSMiddleware, allow_origins=["http://localhost:3001"], ...)]
mcp_middleware = [Middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["Authorization", "mcp-protocol-version", "mcp-session-id", "Content-Type"], ...)]
mcp_app = mcp.http_app(path="/", middleware=mcp_middleware)
```
Apply `portal_middleware` to the FastAPI app's API routes via a sub-application or router-level middleware.

**Warning signs:**
- Browser console shows CORS errors when portal frontend calls backend API
- CC MCP connection fails with vague "network error" -- the OPTIONS preflight was rejected
- `.well-known/oauth-authorization-server` returns 404

**Phase to address:**
Phase 1 (RCARS integration) -- must resolve before external MCP route goes live.

---

### Pitfall 3: FastMCP Lifespan Not Passed to FastAPI

**What goes wrong:**
FastMCP's `StreamableHTTPSessionManager` requires a lifespan context to initialize. If the MCP app's lifespan is not passed to the main FastAPI app, the session manager is never started. All MCP tool calls fail with "FastMCP's StreamableHTTPSessionManager task group was not initialized." The existing portal already has its own lifespan (for APScheduler), so it is not sufficient to just pass `mcp_app.lifespan` -- both lifespans must be combined.

**Why it happens:**
Starlette only supports one lifespan per application. When an MCP sub-app is mounted, its lifespan is silently ignored by the parent app. The portal's existing lifespan (APScheduler startup/shutdown) would be replaced if naively swapped.

**How to avoid:**
Use FastMCP's `combine_lifespans` utility to merge the portal lifespan with the MCP lifespan:
```python
from fastmcp.utilities.lifespan import combine_lifespans

app = FastAPI(lifespan=combine_lifespans(portal_lifespan, mcp_app.lifespan))
```
Where `portal_lifespan` is the existing `lifespan` function that manages APScheduler.

**Warning signs:**
- MCP tools work in unit tests (where lifespan is managed differently) but fail when deployed
- "task group was not initialized" errors in pod logs
- MCP endpoint responds to health checks but tool calls hang or crash

**Phase to address:**
Phase 1 (RCARS integration) -- fundamental wiring issue, must be resolved at MCP mount time.

---

### Pitfall 4: Auth Model Mismatch -- Keycloak Skeleton vs. API Key Design

**What goes wrong:**
The existing codebase has a `KeycloakTokenVerifier` in `app/mcp/auth.py` and Keycloak-related config settings (`keycloak_realm_url`, `mcp_auth_enabled`). The RCARS integration design spec calls for SHA256-hashed API key auth stored in a K8s Secret. If both auth models coexist without clear resolution, you end up with dead code paths, confusing config, and a false sense of security (Keycloak code exists but is not wired in, API key code is added alongside).

**Why it happens:**
The Keycloak auth was scaffolded early as forward-looking infrastructure. The API key design was chosen later as the simpler, more appropriate model for this milestone's needs (internal team, handful of users). Neither decision invalidated the other explicitly.

**How to avoid:**
Make a clean break: remove or clearly isolate the Keycloak auth code behind a feature flag. Implement API key auth as the primary MCP auth mechanism for this milestone. Document in `config.py` that Keycloak is reserved for a future milestone (portal user identity). Do not leave two half-implemented auth paths active simultaneously.

Specifically:
- Add `mcp_api_keys_secret_path` (or env var) to `Settings` for the mounted Secret
- Implement `verify_api_key()` using `hashlib.sha256` + `hmac.compare_digest` (timing-safe comparison)
- Guard only the `/mcp` mount point with API key middleware
- Keep internal API routes (`/api/v1/*`) unauthenticated (cluster-internal only)

**Warning signs:**
- Config has both `keycloak_realm_url` and `api_key_*` settings -- which is active?
- Auth failures in logs reference Keycloak when API keys are in use
- New developers cannot tell which auth model is canonical

**Phase to address:**
Phase 1 (RCARS integration) -- auth is a prerequisite for external MCP access.

---

### Pitfall 5: Timing-Vulnerable API Key Comparison

**What goes wrong:**
Using Python's `==` operator to compare the SHA256 hash of an incoming API key against stored hashes leaks timing information. An attacker can measure response times to determine how many characters of the hash match, progressively recovering the full hash. With the hash, they can forge valid API keys.

**Why it happens:**
String equality in Python short-circuits on the first non-matching character. Developers naturally reach for `==` because it is the obvious comparison operator.

**How to avoid:**
Always use `hmac.compare_digest()` for secret comparisons:
```python
import hashlib, hmac

incoming_hash = hashlib.sha256(raw_key.encode()).hexdigest()
for stored_hash in known_hashes:
    if hmac.compare_digest(incoming_hash, stored_hash):
        return True
return False
```
This is a single-line fix that prevents a category of attack. There is no reason to skip it.

**Warning signs:**
- Code review shows `==` comparing hashes
- No import of `hmac` in auth module

**Phase to address:**
Phase 1 (RCARS integration) -- must be correct from day one; retrofitting auth is harder than getting it right initially.

---

### Pitfall 6: MCP Tool Timeout on RCARS Advisor Polling

**What goes wrong:**
The `ph_rcars_query` tool design calls for submitting a job to RCARS, then polling every 3 seconds until completion, with a 120-second timeout. FastMCP has a documented issue where tools exceeding ~5 seconds do not return results to the client (FastMCP issue #2845). The client times out, the server logs a `ClosedResourceError`, and subsequent requests may crash the server entirely.

**Why it happens:**
FastMCP's default tool timeout is shorter than most developers expect. The MCP protocol itself has client-side timeouts (Claude Code defaults vary). When the RCARS advisor job takes 20-60 seconds (common for complex queries involving embedding similarity + LLM analysis), the tool exceeds all default timeouts in the chain.

**How to avoid:**
1. Set explicit `timeout` on the MCP tool definition: `@mcp.tool(timeout=180)` (or use `task=True` for background execution if FastMCP version supports it)
2. Send progress notifications during polling to keep the connection alive
3. Set `request_timeout` on the FastMCP server config to at least 180 seconds
4. Document the expected latency range for CC users so they set appropriate `timeout` in their MCP client config
5. Implement a graceful degradation path: if the tool times out, return a partial result or a "query submitted, check portal for results" message rather than crashing

**Warning signs:**
- Tools that work locally with fast RCARS responses fail in production with full catalog
- Server pod logs show `ClosedResourceError` or `asyncio.CancelledError`
- CC users report "tool call timed out" errors during intake vetting

**Phase to address:**
Phase 1 (RCARS integration) -- the polling tool is the core integration deliverable.

---

### Pitfall 7: Cross-Namespace NetworkPolicy Blocking RCARS Calls

**What goes wrong:**
The PH backend in `publishing-house-dev` cannot reach `rcars-api.rcars-dev.svc.cluster.local:8080`. Calls hang or return connection refused. The DNS resolves correctly but TCP connections fail. This is because one or both namespaces have NetworkPolicies that restrict cross-namespace traffic, and the policy was not updated when the integration was deployed.

**Why it happens:**
OpenShift environments commonly have default-deny or restrictive NetworkPolicies applied by cluster admins or project templates. Developers test in environments without NetworkPolicies (local, dev clusters without SDN enforcement) and assume cross-namespace DNS resolution equals connectivity. It does not.

**How to avoid:**
Before writing any integration code:
1. Check both namespaces for NetworkPolicies: `oc get networkpolicy -n publishing-house-dev` and `oc get networkpolicy -n rcars-dev`
2. If restrictive policies exist, add explicit ingress rules to the RCARS namespace allowing traffic from the PH namespace:
   ```yaml
   ingress:
   - from:
     - namespaceSelector:
         matchLabels:
           kubernetes.io/metadata.name: publishing-house-dev
     ports:
     - port: 8080
       protocol: TCP
   ```
3. Also check egress policies in the PH namespace -- egress restrictions block outbound calls
4. Manage the NetworkPolicy via Ansible deployer, not manual `oc edit`
5. Add a connectivity smoke test to the deployment playbook: `oc exec` into the PH pod and `curl` the RCARS endpoint

**Warning signs:**
- `oc exec` into PH pod, `nslookup rcars-api.rcars-dev.svc.cluster.local` works but `curl` hangs
- PH backend logs show connection timeout to RCARS (not connection refused -- hanging means firewall/policy)
- Works in one cluster but not another (different NetworkPolicy defaults)

**Phase to address:**
Phase 1 (RCARS integration) -- this is a deployment/infrastructure concern that should be verified in the first Ansible deployer run.

---

### Pitfall 8: SA Token Auth Fails -- Missing system:auth-delegator ClusterRole

**What goes wrong:**
The PH backend sends its auto-mounted SA token to RCARS. RCARS attempts to validate the token via the K8s TokenReview API. The TokenReview request is rejected because the RCARS service account does not have the `system:auth-delegator` ClusterRole, which grants permission to submit TokenReview requests. Authentication fails with "service account unauthorized."

**Why it happens:**
The TokenReview API is a cluster-level authentication endpoint. A service account needs explicit permission (via ClusterRoleBinding to `system:auth-delegator`) to call it. This is not an obvious requirement -- developers assume that because their SA can read pods and services, it can also validate tokens. It cannot, unless explicitly granted.

**How to avoid:**
In the RCARS Ansible deployer, ensure the RCARS service account has a ClusterRoleBinding to `system:auth-delegator`:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: rcars-token-reviewer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system:auth-delegator
subjects:
- kind: ServiceAccount
  name: <rcars-sa-name>
  namespace: rcars-dev
```
If this binding already exists in the RCARS deployment (verify -- it should, since RCARS already validates SA tokens for its own allowlist), confirm it; do not assume.

**Warning signs:**
- RCARS logs show TokenReview 403 Forbidden
- PH backend gets 401 from RCARS even though the SA token is valid
- SA token works with `oc whoami --token=<token>` but RCARS rejects it

**Phase to address:**
Phase 1 (RCARS integration) -- SA token auth is the cluster-internal auth mechanism.

---

### Pitfall 9: Bound SA Token Expiration Breaks Long-Running Operations

**What goes wrong:**
OpenShift 4.11+ uses bound service account tokens that expire after 1 hour by default. The PH backend reads the SA token from `/var/run/secrets/kubernetes.io/serviceaccount/token` once at startup and caches it. After 1 hour, the cached token expires and all RCARS calls fail with 401. The pod appears healthy (liveness probes pass) but all RCARS integration is broken.

**Why it happens:**
Legacy K8s SA tokens were non-expiring. OpenShift 4.11+ adopted the `LegacyServiceAccountTokenNoAutoGeneration` feature gate, making all projected tokens time-bound (typically 1 hour). Developers who read the token once at app startup are using a pattern from the pre-bound-token era.

**How to avoid:**
Read the SA token from the filesystem on every RCARS request (or at most cache for a few minutes). The kubelet refreshes the token file before expiration. The file read is negligible overhead compared to the HTTP call:
```python
def get_sa_token() -> str:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
        return f.read().strip()
```
Do NOT read it once in a global variable or at app startup.

**Warning signs:**
- RCARS calls work immediately after pod restart but fail ~1 hour later
- RCARS logs show "token expired" or TokenReview returns "token is expired"
- Problem disappears when pod is restarted (fresh token)

**Phase to address:**
Phase 1 (RCARS integration) -- design the RCARS HTTP client to re-read the token per-request from the start.

---

### Pitfall 10: Express Mode State Divergence Between Portal DB and Agent Reality

**What goes wrong:**
The express project lifecycle stores state in the portal DB (phase, status, artifacts). The agent customizes a live cluster environment. If the agent crashes, the session disconnects, or the user closes the terminal mid-customization, the portal DB says "phase: customize, status: in_progress" but the environment is in an unknown state -- some operators installed, some apps half-deployed. There is no way to reconcile the two.

**Why it happens:**
Express mode explicitly chose portal DB over git manifest for state management because ephemeral projects do not justify git overhead. But the DB only tracks declared state (what phase the project is in), not observed state (what is actually installed on the cluster). There is no "drift detection."

**How to avoid:**
1. The express skill must log every mutation (operator install, app deploy, config change) as discrete artifacts in the portal DB via `ph_store_express_artifact`. This creates an audit trail the agent can replay or verify on reconnect.
2. On session resume, the agent should run an environment assessment (what is installed, what is running) before continuing -- never assume the previous session's work completed.
3. The recap document (Phase 4) must explicitly list "completed" vs. "attempted but unverified" items.
4. Accept that some express projects will be abandoned mid-customization. Add a cleanup policy (mark "in_progress" projects older than N days as "abandoned") and document that abandoned environments need manual teardown.

**Warning signs:**
- Users report "I reconnected but the agent started from scratch"
- Portal shows "in_progress" projects that have been idle for weeks
- Recap documents list items that were never actually installed

**Phase to address:**
Phase 2 (Express mode framework) -- the DB model and artifact storage must support session resumption. The express skill (separate spec) must implement assessment-before-continuation.

---

### Pitfall 11: Jira Custom Field ID Opacity

**What goes wrong:**
PH creates Jira issues with fields like "Product", "Target Audience", or "Deployment Mode" that map to custom fields in the Red Hat Jira instance. These fields are referenced by opaque IDs like `customfield_12345`. The IDs differ between Jira instances (dev vs. prod), between projects, and can change when an admin modifies the field configuration. Hardcoding these IDs causes silent failures when the integration moves between environments.

**Why it happens:**
Jira's REST API exposes custom fields only by their numeric ID, not by name. Developers discover the ID in one environment, hardcode it, and it works until deployment to a different Jira instance or until an admin restructures fields.

**How to avoid:**
1. On startup (or first Jira call), query `GET /rest/api/2/field` to fetch the full field list
2. Build a name-to-ID map and cache it (refresh daily or on error)
3. Reference fields by human-readable name in PH config; resolve to ID at runtime
4. If a field is not found, log a clear error and fail the Jira operation gracefully -- do not silently skip the field

**Warning signs:**
- Jira issues created with missing custom field values
- 400 errors from Jira API mentioning "Field 'customfield_XXXXX' does not exist"
- Integration works in dev Jira but fails in prod Jira

**Phase to address:**
Phase 3 (Jira integration) -- design the Jira client with runtime field resolution from the start.

---

### Pitfall 12: Chatbot Streaming Messages Lost on Disconnect/Refresh

**What goes wrong:**
The chatbot UI streams agent responses via SSE or WebSocket. User refreshes the page, WiFi drops for 30 seconds, or the backend pod restarts. The stream reconnects but all messages emitted during the gap are gone. The user sees a partial response or a gap in the conversation. There is no indication that anything was lost.

**Why it happens:**
SSE and WebSocket are transport layers, not durable message stores. They deliver messages in real-time with no replay capability. When the connection drops, events emitted during the gap are discarded. Most implementations do not persist the stream to a durable store.

**How to avoid:**
1. Persist all chat messages (user and agent) to the portal DB as they are emitted, not just at the end of a conversation
2. On reconnect/page load, fetch the full conversation history from the DB via REST API, then resume streaming from the current position
3. Assign a monotonic sequence number to each message; on reconnect, the client sends "last seen: N" and the server replays from N+1
4. Use SSE (not WebSocket) for the agent-to-client direction -- SSE is simpler, HTTP-native, and sufficient for unidirectional streaming. Reserve WebSocket for if/when bidirectional real-time features are needed.

**Warning signs:**
- Users report "the agent was talking and then it all disappeared"
- QA finds gaps in conversation transcripts
- Refreshing the chatbot page shows a blank conversation

**Phase to address:**
Phase 4 (Chatbot) -- the message persistence layer must be designed before the streaming transport.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Read SA token once at startup | Simpler code, one fewer file read per request | Breaks after 1 hour on OCP 4.11+ with bound tokens | Never on modern OpenShift |
| Hardcode Jira custom field IDs | Fast to implement, works in dev | Breaks when moving between Jira instances or on field config changes | Never -- always resolve at runtime |
| Single top-level CORSMiddleware | Works for portal-only routes | Conflicts with FastMCP's internal CORS handling once MCP is mounted | Only before MCP is added |
| Skip NetworkPolicy check during deploy | Saves 10 minutes of verification | Days of debugging "connection timeout" in production | Never -- add to deploy playbook |
| Store chatbot messages only in-memory | Fast, no DB writes during streaming | All messages lost on refresh, disconnect, or pod restart | Only during prototype/demo |
| Use `==` for hash comparison | Obvious, readable code | Timing side-channel vulnerability on auth endpoint | Never for secret comparison |
| Cache RCARS responses in portal DB | Reduces RCARS load, faster repeat queries | Stale data if RCARS catalog updates; cache invalidation complexity | Acceptable with TTL and clear staleness indicators |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastMCP mount | Mount at `/mcp` with default path -- creates `/mcp/mcp` | Use `http_app(path="/")` when mounting at `/mcp` |
| FastMCP lifespan | Forget to pass MCP lifespan to FastAPI -- session manager uninitialized | Use `combine_lifespans()` to merge portal + MCP lifespans |
| RCARS cross-namespace | Assume DNS resolution means connectivity | Check NetworkPolicies in both namespaces before coding |
| RCARS SA token | Read token once at startup, cache forever | Re-read from filesystem per request (kubelet refreshes it) |
| RCARS TokenReview | Assume RCARS can validate tokens without ClusterRole | Verify `system:auth-delegator` ClusterRoleBinding exists |
| Jira Data Center | Use Cloud API patterns (Basic auth with API token) | Use PAT with Bearer auth for Data Center; resolve custom fields at runtime |
| Jira pagination | Assume first page has all results | Always paginate; check `startAt`, `maxResults`, `total` |
| Jira rate limiting | No retry logic on 429 | Implement exponential backoff; respect `Retry-After` header |
| Chatbot SSE | Treat SSE as durable message delivery | Persist messages to DB; use sequence numbers for replay on reconnect |
| Chatbot proxy | Forward LLM responses 1:1 to UI | Batch token updates to avoid 25-35 React re-renders per second |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Polling RCARS every 3s for 120s per advisor query | Each intake vetting holds an HTTP connection and a polling loop for up to 2 minutes | Use async polling with `asyncio.sleep`, not thread-blocking `time.sleep`; set hard timeout | >5 concurrent intake sessions polling simultaneously |
| Re-rendering React UI on every SSE token | UI freezes, janky scrolling, high CPU in browser | Batch token updates with `requestAnimationFrame` or throttled state updates (e.g., every 50ms) | Any user with a moderate-length agent response |
| Loading all projects on chatbot page load | Slow initial render, unnecessary DB queries | Paginate project list; lazy-load project details on selection | >50 projects in portal DB |
| Synchronous Jira field resolution on every API call | Each Jira operation adds 200-500ms for the `/field` endpoint call | Cache field map on first call; refresh on 400 errors or daily | >10 Jira operations per session |
| Full catalog search through RCARS for every express base-finding query | RCARS advisor uses LLM analysis -- each query costs real compute | Cache recent query results with TTL; consider a simpler text-match pre-filter for base-finding | >20 express projects per day |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| API key stored in plaintext in K8s Secret `stringData` | Anyone with Secret read access can extract and use any API key | Store SHA256 hashes in the Secret, not raw keys; only raw keys go to users |
| `/mcp` route exposed without auth while internal `/api/v1` routes also exposed externally | Unauthenticated access to internal project data, DB writes via MCP tools | OpenShift Route should expose ONLY `/mcp` path; internal APIs remain cluster-internal via Service-only access |
| SA token logged in debug output | SA token appears in RCARS request logs, accessible to anyone with log access | Redact `Authorization` headers in all logging; never log token values |
| Express mode agent has cluster-admin context from user's `oc login` | Agent could accidentally (or be prompted to) delete critical resources | Scope the `oc` context to a specific namespace; use a dedicated SA with limited RBAC for express operations |
| Jira PAT with admin-level permissions | PH integration can modify any project, user, or config in Jira | Create a dedicated Jira service account with minimal permissions (create/update issues in specific projects only) |
| Chatbot proxies MCP tool calls without authorization scoping | Any chatbot user can invoke any MCP tool, including admin operations | Implement tool-level authorization: map chatbot users to allowed tool sets |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| RCARS vetting query returns no results and skill silently skips vetting | User does not know if vetting ran, failed, or found nothing | Always show the vetting result -- "no overlapping content found" is a valid, useful result |
| Express mode environment gate blocks without progress indication | User ordered a CI, is waiting, sees no feedback for 10-20 minutes | Poll environment status periodically; show "environment provisioning... estimated wait: 15 min" |
| Chatbot shows raw MCP tool errors to the user | User sees "ClosedResourceError" or JSON error blobs | Wrap all tool errors in human-readable messages; log the technical detail server-side |
| Jira ticket creation succeeds but link is not shown to the user | User has to search Jira manually to find the ticket PH created | Always return and display the Jira issue URL after creation |
| CC user's MCP config has wrong URL or expired API key | Vague "connection failed" error with no actionable guidance | Provide a `ph_health_check` MCP tool that tests connectivity and auth; include the URL to the admin guide in error messages |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **MCP Server:** Route created and responds to GET -- but lifespan not combined, so tool calls fail. Verify: call an actual MCP tool through CC, not just curl the endpoint.
- [ ] **API Key Auth:** Middleware rejects invalid keys -- but uses `==` comparison instead of `hmac.compare_digest()`. Verify: check the comparison function in code review.
- [ ] **Cross-Namespace Connectivity:** DNS resolves `rcars-api.rcars-dev.svc.cluster.local` -- but TCP connection hangs due to NetworkPolicy. Verify: `curl` from inside the PH pod, not just `nslookup`.
- [ ] **SA Token Auth:** PH sends token, RCARS returns 200 -- but tested with a manually-created non-expiring token, not the bound token. Verify: wait 2 hours after pod start and test again.
- [ ] **RCARS Polling Tool:** Works with fast queries (<5s) -- but times out on real catalog queries that take 30-60s. Verify: test with a complex query against the full RCARS catalog.
- [ ] **Express DB Model:** Migration runs, tables created -- but no cleanup policy for abandoned projects. Verify: check for "in_progress" projects older than 7 days.
- [ ] **Jira Integration:** Creates issues in dev Jira -- but custom field IDs are hardcoded and will fail in prod. Verify: deploy against a different Jira project and confirm fields populate.
- [ ] **Chatbot Streaming:** Agent responses stream beautifully -- but refresh the page and conversation is gone. Verify: refresh mid-response and confirm history loads.
- [ ] **Express Handoff Recap:** Recap document generated -- but lists "installed operator X" even though the install failed. Verify: compare recap against actual cluster state.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Double-prefix 404 on MCP | LOW | Fix `http_app(path="/")`, redeploy. No data loss. |
| CORS collision | LOW | Refactor to sub-app CORS, redeploy. No data loss. |
| Lifespan not combined | LOW | Add `combine_lifespans`, redeploy. No data loss. |
| Timing-vulnerable key comparison | LOW | Replace `==` with `hmac.compare_digest()`, redeploy. Rotate keys if breach suspected. |
| SA token cached and expired | LOW | Change to per-request file read, redeploy. Immediate fix. |
| NetworkPolicy blocking | MEDIUM | Identify missing policy rule, update via Ansible, redeploy. May need cluster admin assistance. |
| MCP tool timeout on RCARS | MEDIUM | Add explicit timeout config, implement progress notifications, redeploy. May require FastMCP version upgrade. |
| Express state divergence | HIGH | No automated recovery. Manual cluster assessment required. Prevent by designing assessment-on-resume from the start. |
| Chatbot messages lost | HIGH | If messages were not persisted, they are gone. Prevent by persisting from day one. Retrofitting persistence requires schema changes and backfill. |
| Jira field ID mismatch in prod | MEDIUM | Implement runtime field resolution, redeploy. Existing issues may need manual field correction. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| MCP mount double-prefix | Phase 1 (RCARS integration) | CC user successfully connects to `/mcp` and calls a tool |
| CORS middleware collision | Phase 1 (RCARS integration) | Portal frontend AND CC MCP client both work simultaneously |
| Lifespan not combined | Phase 1 (RCARS integration) | MCP tool call succeeds after fresh deployment (not just in tests) |
| Auth model mismatch | Phase 1 (RCARS integration) | Only one auth mechanism active; config is unambiguous |
| Timing-vulnerable comparison | Phase 1 (RCARS integration) | Code review confirms `hmac.compare_digest` usage |
| MCP tool timeout | Phase 1 (RCARS integration) | `ph_rcars_query` completes against full catalog (30-60s query) |
| NetworkPolicy blocking | Phase 1 (RCARS integration) | `curl` from PH pod to RCARS returns 200 |
| SA token expiration | Phase 1 (RCARS integration) | RCARS calls succeed 2+ hours after pod startup |
| system:auth-delegator | Phase 1 (RCARS integration) | TokenReview succeeds for PH SA token in RCARS logs |
| Express state divergence | Phase 2 (Express framework) | Resume interrupted express session; agent assesses before continuing |
| Jira custom field opacity | Phase 3 (Jira integration) | Jira integration works against two different Jira projects without config changes |
| Chatbot message loss | Phase 4 (Chatbot) | Refresh chatbot page mid-conversation; full history loads |

## Sources

- [FastMCP Official Docs - HTTP Deployment](https://gofastmcp.com/deployment/http) -- Context7 verified, mount path and CORS patterns
- [FastMCP Official Docs - FastAPI Integration](https://gofastmcp.com/integrations/fastapi) -- Context7 verified, lifespan combination
- [FastMCP Issue #2845 - Long-running tools fail](https://github.com/PrefectHQ/fastmcp/issues/2845) -- tool timeout behavior
- [FastMCP Issue #2817 - Auth in combined apps](https://github.com/PrefectHQ/fastmcp/issues/2817) -- auth header propagation
- [FastMCP Issue #2139 - CORS with Cognito](https://github.com/PrefectHQ/fastmcp/issues/2139) -- CORS middleware conflicts
- [MCP Python SDK Issue #1367 - Mount path double prefix](https://github.com/modelcontextprotocol/python-sdk/issues/1367) -- double `/mcp/mcp` problem
- [fastmcp-mount PyPI Package](https://pypi.org/project/fastmcp-mount/) -- community fix for mount path issues
- [Kubernetes Network Policy Recipes](https://github.com/ahmetb/kubernetes-network-policy-recipes) -- cross-namespace policy patterns
- [OpenShift Bound Service Account Tokens](https://docs.openshift.com/container-platform/4.8/authentication/bound-service-account-tokens.html) -- token expiration behavior
- [Kubernetes TokenReview API](https://kubernetes.io/docs/reference/access-authn-authz/authentication/) -- auth-delegator requirement
- [Atlassian Rate Limiting](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/) -- Jira rate limit model
- [Jira Data Center PAT Documentation](https://developer.atlassian.com/server/jira/platform/personal-access-token/) -- PAT auth patterns
- [Why Agent UIs Lose Messages on Refresh](https://starcite.ai/blog/why-agent-uis-lose-messages-on-refresh) -- chatbot durability patterns
- [MCP Async Tasks Spec](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1391) -- long-running operation handling

---
*Pitfalls research for: RHDP Publishing House -- MCP integration, auth, K8s cross-namespace, express provisioning, Jira, chatbot*
*Researched: 2026-04-30*
