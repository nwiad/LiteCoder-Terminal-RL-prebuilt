## Kubernetes Pod-to-Pod Communication with Network Policies

Set up a Kubernetes environment with network policies to control pod-to-pod communication between frontend and backend services, then validate the policy enforcement.

**Technical Requirements:**
- Kubernetes cluster with network policy support (Calico, Cilium, or similar CNI)
- kubectl CLI configured
- Two namespaces: `frontend` and `backend`

**Implementation Requirements:**

Create the following Kubernetes resources:

1. **Namespaces**: Create `frontend` and `backend` namespaces

2. **Pods**: Deploy two pods with these specifications:
   - Frontend pod: name `frontend-app`, namespace `frontend`, label `app=frontend`, image `nginx:alpine`
   - Backend pod: name `backend-app`, namespace `backend`, label `app=backend`, image `nginx:alpine` listening on port 80

3. **Network Policy**: Create a network policy in the `backend` namespace that:
   - Applies to pods with label `app=backend`
   - Allows ingress traffic only from pods with label `app=frontend` on TCP port 80
   - Denies all other ingress traffic by default

4. **Validation**: Test connectivity and output results to `/app/validation_results.json`

**Output Format:**

The validation results file must be a JSON object with this structure:
```json
{
  "frontend_to_backend": "allowed|denied",
  "backend_to_frontend": "allowed|denied",
  "external_to_backend": "allowed|denied",
  "policy_applied": true|false,
  "timestamp": "ISO-8601 timestamp"
}
```

**Success Criteria:**
- Frontend pod can successfully connect to backend pod on port 80
- Direct connections to backend from unauthorized sources are blocked
- Network policy is correctly applied and enforced
- Validation results file is created with accurate test results
