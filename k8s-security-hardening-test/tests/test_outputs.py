"""
Tests for Kubernetes Security Hardening & Network Policy Testing task.

Validates the 11 output files produced by the agent under /app/.
Tests run AFTER the task is complete (cluster is torn down), so we
only inspect the captured output files.
"""

import os
import re
import yaml
import pytest

APP_DIR = "/app"


def read_file(filename):
    """Read a file from /app, return contents or None if missing."""
    path = os.path.join(APP_DIR, filename)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_file_strict(filename):
    """Read file, fail test if missing or empty."""
    content = read_file(filename)
    assert content is not None, f"/app/{filename} does not exist"
    stripped = content.strip()
    assert len(stripped) > 0, f"/app/{filename} is empty"
    return stripped


# ──────────────────────────────────────────────
# 1. File existence — all 11 output files
# ──────────────────────────────────────────────

REQUIRED_FILES = [
    "node-status.txt",
    "cluster-info.txt",
    "cert-manager-pods.txt",
    "certificate-status.yaml",
    "demo-services.txt",
    "network-policies.yaml",
    "netpol-list.txt",
    "connectivity-tests.txt",
    "metrics-output.txt",
    "k3s-security-lab-summary.txt",
    "teardown-check.txt",
]


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_output_file_exists(filename):
    """Every required output file must exist."""
    path = os.path.join(APP_DIR, filename)
    assert os.path.isfile(path), f"Missing output file: /app/{filename}"


# ──────────────────────────────────────────────
# 2. node-status.txt
# ──────────────────────────────────────────────

def test_node_status_contains_ready():
    """node-status.txt must show at least one node in Ready state."""
    content = read_file_strict("node-status.txt")
    # kubectl get nodes output has columns: NAME STATUS ROLES AGE VERSION
    assert "Ready" in content, "node-status.txt does not contain 'Ready'"
    # Should have a header line with NAME
    lower = content.lower()
    assert "name" in lower or "status" in lower, (
        "node-status.txt does not look like kubectl get nodes output"
    )


def test_node_status_not_notready():
    """The node should not be in NotReady state."""
    content = read_file_strict("node-status.txt")
    lines = content.strip().splitlines()
    # Check data lines (skip header)
    for line in lines[1:]:
        if line.strip():
            # NotReady is a failure; Ready alone is success
            # But "NotReady" also contains "Ready", so check specifically
            fields = line.split()
            if len(fields) >= 2:
                status_field = fields[1]
                assert status_field != "NotReady", (
                    f"Node is in NotReady state: {line}"
                )


# ──────────────────────────────────────────────
# 3. cluster-info.txt
# ──────────────────────────────────────────────

def test_cluster_info_has_api_server():
    """cluster-info.txt must reference the Kubernetes API server."""
    content = read_file_strict("cluster-info.txt")
    lower = content.lower()
    assert "kubernetes" in lower, (
        "cluster-info.txt does not mention 'kubernetes'"
    )
    # Should contain a URL or IP reference to the control plane
    assert re.search(r"https?://", content), (
        "cluster-info.txt does not contain an API server URL"
    )


# ──────────────────────────────────────────────
# 4. cert-manager-pods.txt
# ──────────────────────────────────────────────

def test_cert_manager_pods_running():
    """cert-manager-pods.txt must show at least 3 Running pods."""
    content = read_file_strict("cert-manager-pods.txt")
    running_count = len(re.findall(r"\bRunning\b", content))
    assert running_count >= 3, (
        f"Expected at least 3 Running cert-manager pods, found {running_count}"
    )


def test_cert_manager_pods_components():
    """All three cert-manager components must be present."""
    content = read_file_strict("cert-manager-pods.txt")
    # The three core pods (names may have random suffixes)
    for component in ["cert-manager-webhook", "cert-manager-cainjector"]:
        assert component in content, (
            f"cert-manager component '{component}' not found in pods output"
        )
    # The main cert-manager pod — match "cert-manager-" but exclude webhook/cainjector
    lines = content.strip().splitlines()
    has_main = any(
        "cert-manager-" in line
        and "webhook" not in line
        and "cainjector" not in line
        for line in lines
    )
    assert has_main, "Main cert-manager pod not found in pods output"


# ──────────────────────────────────────────────
# 5. certificate-status.yaml
# ──────────────────────────────────────────────

def test_certificate_yaml_is_valid():
    """certificate-status.yaml must be valid YAML."""
    content = read_file_strict("certificate-status.yaml")
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError as e:
        pytest.fail(f"certificate-status.yaml is not valid YAML: {e}")
    assert isinstance(doc, dict), "certificate-status.yaml root is not a mapping"


def test_certificate_resource_fields():
    """Certificate must have correct metadata and spec fields."""
    content = read_file_strict("certificate-status.yaml")
    doc = yaml.safe_load(content)
    # Kind
    assert doc.get("kind") == "Certificate", (
        f"Expected kind=Certificate, got {doc.get('kind')}"
    )
    # Name
    meta = doc.get("metadata", {})
    assert meta.get("name") == "demo-tls", (
        f"Expected certificate name 'demo-tls', got {meta.get('name')}"
    )
    # Namespace
    assert meta.get("namespace") == "demo-fintech", (
        f"Expected namespace 'demo-fintech', got {meta.get('namespace')}"
    )
    # Spec fields
    spec = doc.get("spec", {})
    assert spec.get("secretName") == "demo-tls-secret", (
        f"Expected secretName 'demo-tls-secret', got {spec.get('secretName')}"
    )
    dns_names = spec.get("dnsNames", [])
    assert "demo.fintech.local" in dns_names, (
        f"'demo.fintech.local' not in dnsNames: {dns_names}"
    )
    # IssuerRef
    issuer_ref = spec.get("issuerRef", {})
    assert issuer_ref.get("name") == "selfsigned-issuer", (
        f"Expected issuerRef name 'selfsigned-issuer', got {issuer_ref.get('name')}"
    )
    assert issuer_ref.get("kind") == "ClusterIssuer", (
        f"Expected issuerRef kind 'ClusterIssuer', got {issuer_ref.get('kind')}"
    )


def test_certificate_ready_status():
    """Certificate must have reached Ready=True condition."""
    content = read_file_strict("certificate-status.yaml")
    doc = yaml.safe_load(content)
    status = doc.get("status", {})
    conditions = status.get("conditions", [])
    ready_cond = [c for c in conditions if c.get("type") == "Ready"]
    assert len(ready_cond) > 0, "No 'Ready' condition found in certificate status"
    assert ready_cond[0].get("status") == "True", (
        f"Certificate Ready condition is not True: {ready_cond[0].get('status')}"
    )


# ──────────────────────────────────────────────
# 6. demo-services.txt
# ──────────────────────────────────────────────

def test_demo_services_pods_running():
    """All 3 microservice pods must be Running."""
    content = read_file_strict("demo-services.txt")
    for svc in ["frontend", "middle-tier", "backend"]:
        assert svc in content, (
            f"Microservice '{svc}' not found in demo-services.txt"
        )
    running_count = len(re.findall(r"\bRunning\b", content))
    assert running_count >= 3, (
        f"Expected at least 3 Running pods, found {running_count}"
    )


def test_demo_services_clusterip():
    """All 3 services must be ClusterIP type."""
    content = read_file_strict("demo-services.txt")
    clusterip_count = len(re.findall(r"\bClusterIP\b", content))
    assert clusterip_count >= 3, (
        f"Expected at least 3 ClusterIP services, found {clusterip_count}"
    )


# ──────────────────────────────────────────────
# 7. network-policies.yaml
# ──────────────────────────────────────────────

def _load_netpol_docs():
    """Load all YAML documents from network-policies.yaml."""
    content = read_file_strict("network-policies.yaml")
    docs = list(yaml.safe_load_all(content))
    # Filter out None docs (from trailing ---)
    return [d for d in docs if d is not None]


def test_network_policies_yaml_valid():
    """network-policies.yaml must be valid multi-doc YAML."""
    docs = _load_netpol_docs()
    assert len(docs) >= 3, (
        f"Expected at least 3 NetworkPolicy documents, found {len(docs)}"
    )


def test_network_policies_all_are_networkpolicy():
    """All documents must be NetworkPolicy kind in demo-fintech namespace."""
    docs = _load_netpol_docs()
    for doc in docs:
        assert doc.get("kind") == "NetworkPolicy", (
            f"Expected kind=NetworkPolicy, got {doc.get('kind')}"
        )
        ns = doc.get("metadata", {}).get("namespace", "")
        assert ns == "demo-fintech", (
            f"Expected namespace 'demo-fintech', got '{ns}'"
        )


def test_network_policies_default_deny():
    """A default-deny-all policy must exist with empty podSelector."""
    docs = _load_netpol_docs()
    names = {d.get("metadata", {}).get("name"): d for d in docs}
    assert "default-deny-all" in names, (
        f"'default-deny-all' policy not found. Found: {list(names.keys())}"
    )
    deny = names["default-deny-all"]
    spec = deny.get("spec", {})
    # podSelector should be empty (selects all pods)
    pod_sel = spec.get("podSelector", {})
    match_labels = pod_sel.get("matchLabels", None)
    assert match_labels is None or len(match_labels) == 0, (
        "default-deny-all should have empty podSelector (select all pods)"
    )
    # Must cover both Ingress and Egress
    policy_types = spec.get("policyTypes", [])
    assert "Ingress" in policy_types, "default-deny-all must include Ingress"
    assert "Egress" in policy_types, "default-deny-all must include Egress"


def _find_policy_by_name(docs, name):
    """Find a NetworkPolicy doc by name, or collect all docs that start with name."""
    exact = [d for d in docs if d.get("metadata", {}).get("name") == name]
    if exact:
        return exact
    # Some agents may split into sub-policies like allow-frontend-to-middle-egress
    prefix = [d for d in docs if d.get("metadata", {}).get("name", "").startswith(name)]
    return prefix


def _collect_label_refs(doc):
    """Collect all app label values referenced in a NetworkPolicy spec."""
    labels = set()
    spec = doc.get("spec", {})
    # podSelector
    ps = spec.get("podSelector", {}).get("matchLabels", {})
    if "app" in ps:
        labels.add(ps["app"])
    # ingress rules
    for rule in spec.get("ingress", []):
        for fr in rule.get("from", []):
            ml = fr.get("podSelector", {}).get("matchLabels", {})
            if "app" in ml:
                labels.add(ml["app"])
    # egress rules
    for rule in spec.get("egress", []):
        for to in rule.get("to", []):
            ml = to.get("podSelector", {}).get("matchLabels", {})
            if "app" in ml:
                labels.add(ml["app"])
    return labels


def test_network_policies_frontend_to_middle():
    """Policies must allow frontend->middle-tier traffic on port 80."""
    docs = _load_netpol_docs()
    policies = _find_policy_by_name(docs, "allow-frontend-to-middle")
    assert len(policies) > 0, (
        "No policy named 'allow-frontend-to-middle' (or prefix match) found"
    )
    # Collect all label references across matching policies
    all_labels = set()
    has_port_80 = False
    for pol in policies:
        all_labels.update(_collect_label_refs(pol))
        spec = pol.get("spec", {})
        for rule in spec.get("egress", []) + spec.get("ingress", []):
            for p in rule.get("ports", []):
                if p.get("port") == 80:
                    has_port_80 = True
    assert "frontend" in all_labels, (
        "allow-frontend-to-middle must reference app=frontend"
    )
    assert "middle-tier" in all_labels, (
        "allow-frontend-to-middle must reference app=middle-tier"
    )
    assert has_port_80, "allow-frontend-to-middle must specify port 80"


def test_network_policies_middle_to_backend():
    """Policies must allow middle-tier->backend traffic on port 80."""
    docs = _load_netpol_docs()
    policies = _find_policy_by_name(docs, "allow-middle-to-backend")
    assert len(policies) > 0, (
        "No policy named 'allow-middle-to-backend' (or prefix match) found"
    )
    all_labels = set()
    has_port_80 = False
    for pol in policies:
        all_labels.update(_collect_label_refs(pol))
        spec = pol.get("spec", {})
        for rule in spec.get("egress", []) + spec.get("ingress", []):
            for p in rule.get("ports", []):
                if p.get("port") == 80:
                    has_port_80 = True
    assert "middle-tier" in all_labels, (
        "allow-middle-to-backend must reference app=middle-tier"
    )
    assert "backend" in all_labels, (
        "allow-middle-to-backend must reference app=backend"
    )
    assert has_port_80, "allow-middle-to-backend must specify port 80"


# ──────────────────────────────────────────────
# 8. netpol-list.txt
# ──────────────────────────────────────────────

def test_netpol_list_required_names():
    """netpol-list.txt must list the 3 required policy names."""
    content = read_file_strict("netpol-list.txt")
    for name in ["default-deny-all", "allow-frontend-to-middle", "allow-middle-to-backend"]:
        assert name in content, (
            f"Policy '{name}' not found in netpol-list.txt"
        )


# ──────────────────────────────────────────────
# 9. connectivity-tests.txt
# ──────────────────────────────────────────────

def test_connectivity_tests_file_has_4_results():
    """connectivity-tests.txt must have exactly 4 test result lines."""
    content = read_file_strict("connectivity-tests.txt")
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    assert len(lines) == 4, (
        f"Expected 4 connectivity test lines, found {len(lines)}"
    )


def test_connectivity_frontend_to_middle_pass():
    """frontend -> middle-tier must PASS."""
    content = read_file_strict("connectivity-tests.txt")
    lines = content.strip().splitlines()
    match = [l for l in lines if "frontend" in l and "middle-tier" in l]
    assert len(match) > 0, "No line for frontend -> middle-tier test"
    line = match[0].upper()
    assert "PASS" in line, (
        f"frontend -> middle-tier should PASS, got: {match[0]}"
    )
    assert "BLOCK" not in line, (
        f"frontend -> middle-tier should not be BLOCKED: {match[0]}"
    )


def test_connectivity_middle_to_backend_pass():
    """middle-tier -> backend must PASS."""
    content = read_file_strict("connectivity-tests.txt")
    lines = content.strip().splitlines()
    match = [l for l in lines if "middle-tier" in l and "backend" in l]
    assert len(match) > 0, "No line for middle-tier -> backend test"
    line = match[0].upper()
    assert "PASS" in line, (
        f"middle-tier -> backend should PASS, got: {match[0]}"
    )
    assert "BLOCK" not in line, (
        f"middle-tier -> backend should not be BLOCKED: {match[0]}"
    )


def test_connectivity_frontend_to_backend_blocked():
    """frontend -> backend must be BLOCKED."""
    content = read_file_strict("connectivity-tests.txt")
    lines = content.strip().splitlines()
    # Match lines with frontend and backend but NOT middle-tier
    match = [
        l for l in lines
        if "frontend" in l and "backend" in l and "middle" not in l
    ]
    assert len(match) > 0, "No line for frontend -> backend test"
    line = match[0].upper()
    assert "BLOCK" in line, (
        f"frontend -> backend should be BLOCKED, got: {match[0]}"
    )


def test_connectivity_backend_to_frontend_blocked():
    """backend -> frontend must be BLOCKED."""
    content = read_file_strict("connectivity-tests.txt")
    lines = content.strip().splitlines()
    match = [
        l for l in lines
        if "backend" in l and "frontend" in l and "middle" not in l
    ]
    assert len(match) > 0, "No line for backend -> frontend test"
    line = match[0].upper()
    assert "BLOCK" in line, (
        f"backend -> frontend should be BLOCKED, got: {match[0]}"
    )


# ──────────────────────────────────────────────
# 10. metrics-output.txt
# ──────────────────────────────────────────────

def test_metrics_output_has_data():
    """metrics-output.txt must contain node metrics with CPU/memory."""
    content = read_file_strict("metrics-output.txt")
    lower = content.lower()
    # kubectl top nodes header contains CPU and MEMORY columns
    assert "cpu" in lower, "metrics-output.txt does not contain CPU data"
    assert "memory" in lower, "metrics-output.txt does not contain memory data"


def test_metrics_output_has_numeric_values():
    """metrics-output.txt must contain actual numeric metric values."""
    content = read_file_strict("metrics-output.txt")
    # Metrics values typically contain numbers with units like "150m" (millicores)
    # or "512Mi" (mebibytes) or percentage like "5%"
    lines = content.strip().splitlines()
    data_lines = [l for l in lines if l.strip() and not l.strip().startswith("NAME")]
    assert len(data_lines) >= 1, "No data lines in metrics-output.txt"
    # At least one data line should contain a number
    has_number = any(re.search(r"\d+", l) for l in data_lines)
    assert has_number, "metrics-output.txt data lines contain no numeric values"


# ──────────────────────────────────────────────
# 11. k3s-security-lab-summary.txt
# ──────────────────────────────────────────────

REQUIRED_SECTIONS = [
    "[Cluster Setup]",
    "[Certificate Management]",
    "[Network Policies]",
    "[Metrics]",
]


def test_summary_has_required_sections():
    """Summary must contain all 4 required section headings."""
    content = read_file_strict("k3s-security-lab-summary.txt")
    for section in REQUIRED_SECTIONS:
        assert section in content, (
            f"Required section '{section}' not found in summary"
        )


def test_summary_sections_have_content():
    """Each section must have descriptive content (not just a heading)."""
    content = read_file_strict("k3s-security-lab-summary.txt")
    for i, section in enumerate(REQUIRED_SECTIONS):
        idx = content.find(section)
        assert idx >= 0, f"Section '{section}' not found"
        # Get text between this section and the next (or end of file)
        start = idx + len(section)
        if i + 1 < len(REQUIRED_SECTIONS):
            next_idx = content.find(REQUIRED_SECTIONS[i + 1])
            section_text = content[start:next_idx].strip()
        else:
            section_text = content[start:].strip()
        # Each section should have at least 20 chars of content
        assert len(section_text) >= 20, (
            f"Section '{section}' has insufficient content ({len(section_text)} chars)"
        )


def test_summary_minimum_length():
    """Summary should be a substantive document, not a stub."""
    content = read_file_strict("k3s-security-lab-summary.txt")
    assert len(content) >= 200, (
        f"Summary is too short ({len(content)} chars), expected >= 200"
    )


# ──────────────────────────────────────────────
# 12. teardown-check.txt
# ──────────────────────────────────────────────

def test_teardown_check_exists():
    """teardown-check.txt must exist (may be empty for clean teardown)."""
    path = os.path.join(APP_DIR, "teardown-check.txt")
    assert os.path.isfile(path), "teardown-check.txt does not exist"


def test_teardown_no_k8s_processes():
    """teardown-check.txt must not show running k3s/kubelet/containerd."""
    content = read_file("teardown-check.txt")
    if content is None:
        pytest.fail("teardown-check.txt does not exist")
    stripped = content.strip()
    # Empty file = clean teardown
    if len(stripped) == 0:
        return
    # If non-empty, lines should not contain active k3s/kubelet/containerd
    # (grep -v grep was already applied, so any remaining lines are real)
    lines = [l.strip() for l in stripped.splitlines() if l.strip()]
    active = [
        l for l in lines
        if re.search(r'\b(k3s|kubelet|containerd)\b', l)
        and "grep" not in l
        and "defunct" not in l
        and "zombie" not in l
    ]
    assert len(active) == 0, (
        f"Teardown incomplete — {len(active)} k8s processes still running:\n"
        + "\n".join(active[:5])
    )

