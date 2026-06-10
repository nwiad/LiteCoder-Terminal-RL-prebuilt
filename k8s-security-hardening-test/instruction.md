## Kubernetes Security Hardening & Network Policy Testing

Build a k3s Kubernetes cluster inside the current Ubuntu container, harden it with Network Policies and cert-manager, deploy mock microservices, validate security controls, and then tear everything down cleanly.

### Technical Requirements

- Runtime: k3s (lightweight Kubernetes), installed as a single-node cluster
- Tools: kubectl (compatible with the installed k3s version)
- cert-manager: v1.14.x
- All work is performed inside the current container (privileged commands allowed)

### Step-by-step Requirements

**1. Install k3s and verify the node is Ready**

- Install k3s in single-node mode.
- The node must reach `Ready` status.
- Write the node status output to `/app/node-status.txt` using:
  ```
  kubectl get nodes
  ```

**2. Install kubectl and confirm API connectivity**

- Ensure `kubectl` is available and can communicate with the k3s API server.
- Write the output of `kubectl cluster-info` to `/app/cluster-info.txt`.

**3. Install cert-manager v1.14 in the cluster**

- Install cert-manager v1.14.x into the `cert-manager` namespace.
- All cert-manager pods (`cert-manager`, `cert-manager-cainjector`, `cert-manager-webhook`) must reach `Running` status.
- Write the output of `kubectl get pods -n cert-manager` to `/app/cert-manager-pods.txt`.

**4. Create a test certificate issuer and obtain a TLS certificate**

- Create a self-signed `ClusterIssuer` named `selfsigned-issuer`.
- Create a `Certificate` resource named `demo-tls` in namespace `demo-fintech` (create the namespace if it does not exist) that:
  - References the `selfsigned-issuer` ClusterIssuer
  - Has `secretName: demo-tls-secret`
  - Has `dnsNames` including `demo.fintech.local`
- The Certificate must reach `Ready=True` condition.
- Write the output of `kubectl get certificate demo-tls -n demo-fintech -o yaml` to `/app/certificate-status.yaml`.

**5. Deploy 3 microservices in namespace `demo-fintech`**

Deploy three Deployments and their corresponding ClusterIP Services in the `demo-fintech` namespace:

| Name         | Labels (`app=`)  | Container Image     | Container Port | Service Port |
|--------------|-------------------|----------------------|----------------|--------------|
| frontend     | frontend          | nginx:alpine         | 80             | 80           |
| middle-tier  | middle-tier       | nginx:alpine         | 80             | 80           |
| backend      | backend           | nginx:alpine         | 80             | 80           |

- Each Deployment should have `replicas: 1`.
- All pods must reach `Running` status.
- Write the output of `kubectl get pods,svc -n demo-fintech` to `/app/demo-services.txt`.

**6. Apply restrictive NetworkPolicies**

Create and apply NetworkPolicies in the `demo-fintech` namespace that enforce the following rules:

- A `default-deny-all` NetworkPolicy that denies all ingress and egress traffic for all pods in the namespace.
- A policy named `allow-frontend-to-middle` that allows `frontend` pods to send egress traffic to `middle-tier` pods on port 80, and allows `middle-tier` pods to receive ingress from `frontend` pods.
- A policy named `allow-middle-to-backend` that allows `middle-tier` pods to send egress traffic to `backend` pods on port 80, and allows `backend` pods to receive ingress from `middle-tier` pods.

Pod selection must use the label `app` (e.g., `app: frontend`).

- Write all NetworkPolicy manifests (as applied) to `/app/network-policies.yaml` (concatenated with `---` separators).
- Write the output of `kubectl get networkpolicies -n demo-fintech` to `/app/netpol-list.txt`.

**7. Verify NetworkPolicies by testing connectivity**

Run connectivity tests from a temporary debug pod (image: `busybox` or `nicolaka/netshoot`) in the `demo-fintech` namespace:

- Test 1 (SHOULD SUCCEED): `frontend` → `middle-tier` on port 80
- Test 2 (SHOULD SUCCEED): `middle-tier` → `backend` on port 80
- Test 3 (SHOULD FAIL): `frontend` → `backend` on port 80 (direct access denied)
- Test 4 (SHOULD FAIL): `backend` → `frontend` on port 80 (reverse access denied)

Write the test results to `/app/connectivity-tests.txt` with the following format (one line per test):

```
frontend -> middle-tier:80 : PASS
middle-tier -> backend:80 : PASS
frontend -> backend:80 : BLOCKED
backend -> frontend:80 : BLOCKED
```

**8. Enable metrics-server and confirm it serves metrics**

- Ensure the k3s built-in metrics-server is running in the `kube-system` namespace.
- Verify that `kubectl top nodes` returns data successfully.
- Write the output of `kubectl top nodes` to `/app/metrics-output.txt`.

**9. Document the cluster hardening summary**

Write a plain-text summary to `/app/k3s-security-lab-summary.txt` that contains at minimum the following sections (each as a heading line followed by descriptive content):

```
[Cluster Setup]
... description of k3s installation and node readiness ...

[Certificate Management]
... description of cert-manager installation and certificate issuance ...

[Network Policies]
... description of the deny-all + allow policies and test results ...

[Metrics]
... description of metrics-server enablement ...
```

**10. Tear down everything cleanly**

- Run the k3s uninstall script (`k3s-uninstall.sh` or equivalent).
- Confirm no Kubernetes processes (k3s, kubelet, containerd) remain running.
- Write the output of `ps aux | grep -E 'k3s|kubelet|containerd' | grep -v grep` to `/app/teardown-check.txt`. This file should be empty or contain no matching processes.

### Output Files Summary

| File                              | Format     |
|-----------------------------------|------------|
| /app/node-status.txt              | plain text |
| /app/cluster-info.txt             | plain text |
| /app/cert-manager-pods.txt        | plain text |
| /app/certificate-status.yaml      | YAML       |
| /app/demo-services.txt            | plain text |
| /app/network-policies.yaml        | YAML       |
| /app/netpol-list.txt              | plain text |
| /app/connectivity-tests.txt       | plain text |
| /app/metrics-output.txt           | plain text |
| /app/k3s-security-lab-summary.txt | plain text |
| /app/teardown-check.txt           | plain text |
