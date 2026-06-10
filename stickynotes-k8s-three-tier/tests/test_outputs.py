"""
Tests for StickyNotes three-tier Kubernetes application.
Validates all generated files under /app/ for existence, structure, and correctness.
"""
import os
import json

import yaml

BASE = "/app"
K8S = os.path.join(BASE, "k8s")
API = os.path.join(BASE, "api")
FRONTEND = os.path.join(BASE, "frontend")
DB = os.path.join(BASE, "db")


def _load_yaml_docs(filepath):
    """Load all YAML documents from a file."""
    assert os.path.isfile(filepath), f"File not found: {filepath}"
    with open(filepath) as f:
        content = f.read()
    assert content.strip(), f"File is empty: {filepath}"
    docs = list(yaml.safe_load_all(content))
    return [d for d in docs if d is not None]


def _load_yaml(filepath):
    """Load a single YAML document."""
    docs = _load_yaml_docs(filepath)
    assert len(docs) >= 1, f"No YAML documents in {filepath}"
    return docs[0]


def _read(filepath):
    """Read file content as string."""
    assert os.path.isfile(filepath), f"File not found: {filepath}"
    with open(filepath) as f:
        content = f.read()
    assert content.strip(), f"File is empty: {filepath}"
    return content


# ============================================================================
# 1. FILE EXISTENCE
# ============================================================================

REQUIRED_FILES = [
    "k8s/namespace.yaml",
    "k8s/secrets.yaml",
    "k8s/configmap.yaml",
    "k8s/mysql-statefulset.yaml",
    "k8s/api-deployment.yaml",
    "k8s/api-service.yaml",
    "k8s/frontend-deployment.yaml",
    "k8s/frontend-service.yaml",
    "k8s/api-hpa.yaml",
    "k8s/frontend-hpa.yaml",
    "k8s/clusterissuer.yaml",
    "k8s/certificate.yaml",
    "k8s/ingress.yaml",
    "api/Dockerfile",
    "api/package.json",
    "api/server.js",
    "frontend/Dockerfile",
    "frontend/nginx.conf",
    "frontend/index.html",
    "db/init.sql",
]


def test_all_required_files_exist():
    missing = []
    for rel in REQUIRED_FILES:
        full = os.path.join(BASE, rel)
        if not os.path.isfile(full):
            missing.append(rel)
    assert not missing, f"Missing files: {missing}"


# ============================================================================
# 2. NAMESPACE
# ============================================================================

def test_namespace_yaml():
    doc = _load_yaml(os.path.join(K8S, "namespace.yaml"))
    assert doc["kind"] == "Namespace"
    assert doc["apiVersion"] == "v1"
    assert doc["metadata"]["name"] == "stickynotes"


# ============================================================================
# 3. SECRETS
# ============================================================================

def test_secrets_yaml():
    doc = _load_yaml(os.path.join(K8S, "secrets.yaml"))
    assert doc["kind"] == "Secret"
    assert doc["apiVersion"] == "v1"
    assert doc["metadata"]["name"] == "stickynotes-secret"
    assert doc["metadata"]["namespace"] == "stickynotes"
    assert doc["type"] == "Opaque"
    data = doc.get("data", {})
    assert "MYSQL_ROOT_PASSWORD" in data, "Secret must contain MYSQL_ROOT_PASSWORD key"
    # Value must be base64-encoded (non-empty string)
    val = data["MYSQL_ROOT_PASSWORD"]
    assert isinstance(val, str) and len(val) > 0, "MYSQL_ROOT_PASSWORD must be a non-empty base64 string"


# ============================================================================
# 4. CONFIGMAP
# ============================================================================

def test_configmap_yaml():
    doc = _load_yaml(os.path.join(K8S, "configmap.yaml"))
    assert doc["kind"] == "ConfigMap"
    assert doc["apiVersion"] == "v1"
    assert doc["metadata"]["name"] == "stickynotes-config"
    assert doc["metadata"]["namespace"] == "stickynotes"
    data = doc.get("data", {})
    assert "MYSQL_HOST" in data, "ConfigMap must contain MYSQL_HOST"
    assert "MYSQL_DATABASE" in data, "ConfigMap must contain MYSQL_DATABASE"


# ============================================================================
# 5. MYSQL STATEFULSET
# ============================================================================

def test_mysql_statefulset_yaml():
    docs = _load_yaml_docs(os.path.join(K8S, "mysql-statefulset.yaml"))
    # Find the StatefulSet and Service among the documents
    statefulsets = [d for d in docs if d.get("kind") == "StatefulSet"]
    services = [d for d in docs if d.get("kind") == "Service"]

    assert len(statefulsets) >= 1, "Must contain a StatefulSet"
    ss = statefulsets[0]
    assert ss["metadata"]["name"] == "mysql"
    assert ss["metadata"]["namespace"] == "stickynotes"
    assert ss["apiVersion"] == "apps/v1"

    spec = ss["spec"]
    assert spec["replicas"] == 1, "MySQL StatefulSet must have exactly 1 replica"

    # Container checks
    containers = spec["template"]["spec"]["containers"]
    assert len(containers) >= 1
    mysql_container = containers[0]
    img = mysql_container["image"]
    assert img.startswith("mysql:8") or img == "mysql:8" or "mysql:8" in img, \
        f"Image must reference mysql:8 (e.g. mysql:8, mysql:8.0, mysql:8.0.35), got {img}"

    # Check for MYSQL_ROOT_PASSWORD env from secret
    envs = mysql_container.get("env", [])
    env_names = [e["name"] for e in envs]
    assert "MYSQL_ROOT_PASSWORD" in env_names, "Must have MYSQL_ROOT_PASSWORD env var"
    pw_env = next(e for e in envs if e["name"] == "MYSQL_ROOT_PASSWORD")
    assert "valueFrom" in pw_env and "secretKeyRef" in pw_env["valueFrom"], \
        "MYSQL_ROOT_PASSWORD must be sourced from a Secret"

    # Check MYSQL_DATABASE env
    assert "MYSQL_DATABASE" in env_names, "Must have MYSQL_DATABASE env var"

    # VolumeClaimTemplates
    vcts = spec.get("volumeClaimTemplates", [])
    assert len(vcts) >= 1, "Must have at least one volumeClaimTemplate"
    vct = vcts[0]
    access_modes = vct["spec"]["accessModes"]
    assert "ReadWriteOnce" in access_modes
    storage = vct["spec"]["resources"]["requests"]["storage"]
    assert storage is not None, "Must specify storage request"


def test_mysql_headless_service():
    """Headless service for MySQL must exist (clusterIP: None)."""
    docs = _load_yaml_docs(os.path.join(K8S, "mysql-statefulset.yaml"))
    services = [d for d in docs if d.get("kind") == "Service"]
    # If not in the statefulset file, check for a separate file
    if not services:
        # Try loading from any other yaml that might contain it
        for fname in os.listdir(K8S):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                try:
                    extra_docs = _load_yaml_docs(os.path.join(K8S, fname))
                    for d in extra_docs:
                        if d.get("kind") == "Service" and d.get("metadata", {}).get("name") == "mysql":
                            services.append(d)
                except Exception:
                    pass

    assert len(services) >= 1, "Must have a headless Service named 'mysql'"
    svc = next((s for s in services if s["metadata"]["name"] == "mysql"), None)
    assert svc is not None, "Headless service must be named 'mysql'"
    assert svc["spec"]["clusterIP"] == "None" or svc["spec"].get("clusterIP") is None, \
        "MySQL service must be headless (clusterIP: None)"
    assert svc["metadata"]["namespace"] == "stickynotes"


# ============================================================================
# 6. API DEPLOYMENT
# ============================================================================

def test_api_deployment_yaml():
    doc = _load_yaml(os.path.join(K8S, "api-deployment.yaml"))
    assert doc["kind"] == "Deployment"
    assert doc["apiVersion"] == "apps/v1"
    assert doc["metadata"]["name"] == "api"
    assert doc["metadata"]["namespace"] == "stickynotes"

    spec = doc["spec"]
    assert spec["replicas"] >= 2, "API deployment must have at least 2 replicas"

    containers = spec["template"]["spec"]["containers"]
    assert len(containers) >= 1
    container = containers[0]

    # Check container port
    ports = container.get("ports", [])
    port_numbers = [p["containerPort"] for p in ports]
    assert 3000 in port_numbers, "API container must expose port 3000"

    # Check env vars reference secret for password
    envs = container.get("env", [])
    env_names = [e["name"] for e in envs]
    assert "MYSQL_ROOT_PASSWORD" in env_names or "MYSQL_PASSWORD" in env_names, \
        "API must have MySQL password env var"


# ============================================================================
# 7. API SERVICE
# ============================================================================

def test_api_service_yaml():
    doc = _load_yaml(os.path.join(K8S, "api-service.yaml"))
    assert doc["kind"] == "Service"
    assert doc["apiVersion"] == "v1"
    assert doc["metadata"]["name"] == "api"
    assert doc["metadata"]["namespace"] == "stickynotes"
    assert doc["spec"]["type"] == "ClusterIP"
    ports = doc["spec"]["ports"]
    port_vals = [p.get("port") for p in ports]
    assert 3000 in port_vals, "API service must target port 3000"


# ============================================================================
# 8. FRONTEND DEPLOYMENT
# ============================================================================

def test_frontend_deployment_yaml():
    doc = _load_yaml(os.path.join(K8S, "frontend-deployment.yaml"))
    assert doc["kind"] == "Deployment"
    assert doc["apiVersion"] == "apps/v1"
    assert doc["metadata"]["name"] == "frontend"
    assert doc["metadata"]["namespace"] == "stickynotes"

    spec = doc["spec"]
    assert spec["replicas"] >= 2, "Frontend deployment must have at least 2 replicas"

    containers = spec["template"]["spec"]["containers"]
    assert len(containers) >= 1
    container = containers[0]
    ports = container.get("ports", [])
    port_numbers = [p["containerPort"] for p in ports]
    assert 80 in port_numbers, "Frontend container must expose port 80"


# ============================================================================
# 9. FRONTEND SERVICE
# ============================================================================

def test_frontend_service_yaml():
    doc = _load_yaml(os.path.join(K8S, "frontend-service.yaml"))
    assert doc["kind"] == "Service"
    assert doc["apiVersion"] == "v1"
    assert doc["metadata"]["name"] == "frontend"
    assert doc["metadata"]["namespace"] == "stickynotes"
    assert doc["spec"]["type"] == "ClusterIP"
    ports = doc["spec"]["ports"]
    port_vals = [p.get("port") for p in ports]
    assert 80 in port_vals, "Frontend service must target port 80"


# ============================================================================
# 10. HPA - API
# ============================================================================

def test_api_hpa_yaml():
    doc = _load_yaml(os.path.join(K8S, "api-hpa.yaml"))
    assert doc["kind"] == "HorizontalPodAutoscaler"
    assert doc["metadata"]["name"] == "api-hpa"
    assert doc["metadata"]["namespace"] == "stickynotes"

    spec = doc["spec"]
    ref = spec["scaleTargetRef"]
    assert ref["kind"] == "Deployment"
    assert ref["name"] == "api"
    assert spec["minReplicas"] == 2
    assert spec["maxReplicas"] == 10

    # Check CPU target utilization = 60
    metrics = spec.get("metrics", [])
    cpu_metrics = [m for m in metrics if m.get("type") == "Resource"
                   and m.get("resource", {}).get("name") == "cpu"]
    assert len(cpu_metrics) >= 1, "Must have CPU metric"
    cpu_target = cpu_metrics[0]["resource"]["target"]
    assert cpu_target.get("averageUtilization") == 60, "CPU target must be 60%"


# ============================================================================
# 11. HPA - FRONTEND
# ============================================================================

def test_frontend_hpa_yaml():
    doc = _load_yaml(os.path.join(K8S, "frontend-hpa.yaml"))
    assert doc["kind"] == "HorizontalPodAutoscaler"
    assert doc["metadata"]["name"] == "frontend-hpa"
    assert doc["metadata"]["namespace"] == "stickynotes"

    spec = doc["spec"]
    ref = spec["scaleTargetRef"]
    assert ref["kind"] == "Deployment"
    assert ref["name"] == "frontend"
    assert spec["minReplicas"] == 2
    assert spec["maxReplicas"] == 10

    metrics = spec.get("metrics", [])
    cpu_metrics = [m for m in metrics if m.get("type") == "Resource"
                   and m.get("resource", {}).get("name") == "cpu"]
    assert len(cpu_metrics) >= 1, "Must have CPU metric"
    cpu_target = cpu_metrics[0]["resource"]["target"]
    assert cpu_target.get("averageUtilization") == 60, "CPU target must be 60%"


# ============================================================================
# 12. CLUSTERISSUER
# ============================================================================

def test_clusterissuer_yaml():
    doc = _load_yaml(os.path.join(K8S, "clusterissuer.yaml"))
    assert doc["kind"] == "ClusterIssuer"
    assert "cert-manager" in doc["apiVersion"], "Must use cert-manager API"
    assert doc["metadata"]["name"] == "letsencrypt-staging"
    # ClusterIssuer is cluster-scoped, so namespace is NOT required
    acme = doc["spec"]["acme"]
    assert "acme-staging-v02.api.letsencrypt.org" in acme["server"], \
        "Must use Let's Encrypt staging URL"
    solvers = acme.get("solvers", [])
    assert len(solvers) >= 1, "Must have at least one solver"
    # Check for http01 solver
    has_http01 = any("http01" in s for s in solvers)
    assert has_http01, "Must use http01 solver"


# ============================================================================
# 13. CERTIFICATE
# ============================================================================

def test_certificate_yaml():
    doc = _load_yaml(os.path.join(K8S, "certificate.yaml"))
    assert doc["kind"] == "Certificate"
    assert "cert-manager" in doc["apiVersion"]
    assert doc["metadata"]["name"] == "stickynotes-tls"
    assert doc["metadata"]["namespace"] == "stickynotes"
    spec = doc["spec"]
    assert spec["secretName"] == "stickynotes-tls-secret"
    issuer_ref = spec["issuerRef"]
    assert issuer_ref["name"] == "letsencrypt-staging"
    assert issuer_ref["kind"] == "ClusterIssuer"
    dns_names = spec.get("dnsNames", [])
    assert "stickynotes.local" in dns_names


# ============================================================================
# 14. INGRESS
# ============================================================================

def test_ingress_yaml():
    doc = _load_yaml(os.path.join(K8S, "ingress.yaml"))
    assert doc["kind"] == "Ingress"
    assert doc["apiVersion"] == "networking.k8s.io/v1"
    assert doc["metadata"]["name"] == "stickynotes-ingress"
    assert doc["metadata"]["namespace"] == "stickynotes"

    spec = doc["spec"]

    # TLS
    tls = spec.get("tls", [])
    assert len(tls) >= 1, "Ingress must have TLS configured"
    tls_entry = tls[0]
    assert "stickynotes.local" in tls_entry.get("hosts", [])
    assert tls_entry.get("secretName") == "stickynotes-tls-secret"

    # Rules
    rules = spec.get("rules", [])
    assert len(rules) >= 1
    rule = rules[0]
    assert rule.get("host") == "stickynotes.local"

    paths = rule["http"]["paths"]
    path_map = {}
    for p in paths:
        path_map[p["path"]] = p

    # /api/ -> api:3000
    assert "/api/" in path_map or "/api" in path_map, "Must have /api/ path rule"
    api_path = path_map.get("/api/", path_map.get("/api"))
    api_backend = api_path["backend"]["service"]
    assert api_backend["name"] == "api"
    api_port = api_backend["port"]
    assert api_port.get("number") == 3000 or api_port.get("name") == "http"

    # / -> frontend:80
    assert "/" in path_map, "Must have / path rule"
    fe_backend = path_map["/"]["backend"]["service"]
    assert fe_backend["name"] == "frontend"
    fe_port = fe_backend["port"]
    assert fe_port.get("number") == 80 or fe_port.get("name") == "http"


# ============================================================================
# 15. DATABASE - init.sql
# ============================================================================

def test_init_sql():
    content = _read(os.path.join(DB, "init.sql")).lower()
    assert "create" in content and "table" in content, "init.sql must CREATE TABLE"
    assert "notes" in content, "Table must be named 'notes'"
    assert "stickynotes" in content, "Must reference database 'stickynotes'"

    # Required columns
    assert "id" in content, "Must have 'id' column"
    assert "title" in content, "Must have 'title' column"
    assert "content" in content, "Must have 'content' column"
    assert "created_at" in content, "Must have 'created_at' column"

    # Column constraints
    assert "auto_increment" in content or "autoincrement" in content, \
        "id must be auto-increment"
    assert "primary key" in content or "primary_key" in content, \
        "id must be primary key"
    assert "not null" in content, "title must be NOT NULL"
    assert "timestamp" in content, "created_at must be TIMESTAMP type"


# ============================================================================
# 16. API - server.js
# ============================================================================

def test_api_server_js():
    content = _read(os.path.join(API, "server.js"))

    # Express usage
    assert "express" in content, "Must use express"
    assert "mysql2" in content or "mysql" in content, "Must use mysql2 driver"

    # Required endpoints
    assert "GET" in content.upper() or "get(" in content or "app.get" in content, \
        "Must have GET endpoint"
    assert "/api/notes" in content, "Must have /api/notes route"
    assert "POST" in content.upper() or "post(" in content or "app.post" in content, \
        "Must have POST endpoint"
    assert "DELETE" in content.upper() or "delete(" in content or "app.delete" in content, \
        "Must have DELETE endpoint"

    # Port 3000
    assert "3000" in content, "Server must listen on port 3000"


# ============================================================================
# 17. API - package.json
# ============================================================================

def test_api_package_json():
    content = _read(os.path.join(API, "package.json"))
    pkg = json.loads(content)
    deps = pkg.get("dependencies", {})
    assert "express" in deps, "Must list express as dependency"
    assert "mysql2" in deps, "Must list mysql2 as dependency"


# ============================================================================
# 18. API - Dockerfile
# ============================================================================

def test_api_dockerfile():
    content = _read(os.path.join(API, "Dockerfile"))
    content_upper = content.upper()
    assert "FROM" in content_upper, "Dockerfile must have FROM instruction"
    assert "NODE" in content_upper or "node" in content, \
        "API Dockerfile must be based on a Node.js image"
    assert "EXPOSE" in content_upper, "Must EXPOSE a port"
    assert "3000" in content, "Must expose port 3000"


# ============================================================================
# 19. FRONTEND - index.html
# ============================================================================

def test_frontend_index_html():
    content = _read(os.path.join(FRONTEND, "index.html"))
    content_lower = content.lower()
    assert "<html" in content_lower, "Must be an HTML document"
    assert "fetch(" in content or "fetch (" in content, \
        "Must use fetch() to call API"
    assert "/api/notes" in content, "Must call /api/notes endpoint"

    # Must have both GET and POST fetch calls
    # GET is implicit (fetch without method), POST requires method specification
    assert "POST" in content or "post" in content, \
        "Must have POST method for creating notes"


# ============================================================================
# 20. FRONTEND - nginx.conf
# ============================================================================

def test_frontend_nginx_conf():
    content = _read(os.path.join(FRONTEND, "nginx.conf"))
    assert "listen" in content, "nginx.conf must have listen directive"
    assert "80" in content, "Must listen on port 80"

    # Reverse proxy for /api/
    assert "proxy_pass" in content, "Must have proxy_pass for reverse proxy"
    assert "/api/" in content or "/api" in content, "Must proxy /api/ path"
    # Must point to the API service internal DNS
    assert "api" in content and "3000" in content, \
        "Must proxy to api service on port 3000"


# ============================================================================
# 21. FRONTEND - Dockerfile
# ============================================================================

def test_frontend_dockerfile():
    content = _read(os.path.join(FRONTEND, "Dockerfile"))
    content_upper = content.upper()
    assert "FROM" in content_upper, "Dockerfile must have FROM instruction"
    assert "NGINX" in content_upper or "nginx" in content, \
        "Frontend Dockerfile must be based on nginx"
    assert "80" in content, "Must reference port 80"


# ============================================================================
# 22. CROSS-RESOURCE CONSISTENCY
# ============================================================================

def test_all_namespaced_resources_use_stickynotes():
    """Every K8s resource (except ClusterIssuer) must have namespace: stickynotes."""
    cluster_scoped_kinds = {"Namespace", "ClusterIssuer", "ClusterRole", "ClusterRoleBinding"}
    for fname in os.listdir(K8S):
        if not (fname.endswith(".yaml") or fname.endswith(".yml")):
            continue
        docs = _load_yaml_docs(os.path.join(K8S, fname))
        for doc in docs:
            kind = doc.get("kind", "")
            if kind in cluster_scoped_kinds:
                continue
            ns = doc.get("metadata", {}).get("namespace")
            assert ns == "stickynotes", \
                f"{fname}: {kind} '{doc['metadata']['name']}' must have namespace 'stickynotes', got '{ns}'"


def test_all_manifests_have_required_fields():
    """Every K8s manifest must have apiVersion, kind, and metadata.name."""
    for fname in os.listdir(K8S):
        if not (fname.endswith(".yaml") or fname.endswith(".yml")):
            continue
        docs = _load_yaml_docs(os.path.join(K8S, fname))
        for doc in docs:
            assert "apiVersion" in doc, f"{fname}: missing apiVersion"
            assert "kind" in doc, f"{fname}: missing kind"
            assert "metadata" in doc and "name" in doc["metadata"], \
                f"{fname}: missing metadata.name"


def test_secret_name_consistency():
    """The secret name referenced in deployments must match the one defined in secrets.yaml."""
    secret_doc = _load_yaml(os.path.join(K8S, "secrets.yaml"))
    secret_name = secret_doc["metadata"]["name"]

    # Check mysql statefulset references the same secret
    docs = _load_yaml_docs(os.path.join(K8S, "mysql-statefulset.yaml"))
    ss_list = [d for d in docs if d.get("kind") == "StatefulSet"]
    if ss_list:
        ss = ss_list[0]
        envs = ss["spec"]["template"]["spec"]["containers"][0].get("env", [])
        for e in envs:
            vf = e.get("valueFrom", {})
            skr = vf.get("secretKeyRef", {})
            if skr:
                assert skr["name"] == secret_name, \
                    f"StatefulSet references secret '{skr['name']}' but expected '{secret_name}'"

