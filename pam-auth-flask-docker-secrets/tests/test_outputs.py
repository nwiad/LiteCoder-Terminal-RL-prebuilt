"""
Tests for PAM-Auth Flask Docker Secrets task.
Validates that all required project files exist under /app/ with correct
content, structure, and configuration as specified in instruction.md.
"""

import os
import re
import stat

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

APP_DIR = "/app"


def _read(relpath):
    """Read a file relative to APP_DIR, return its text content."""
    full = os.path.join(APP_DIR, relpath)
    assert os.path.isfile(full), f"Expected file not found: {full}"
    with open(full, "r") as f:
        return f.read()


def _exists(relpath):
    return os.path.isfile(os.path.join(APP_DIR, relpath))


# ===================================================================
# 1. FILE EXISTENCE
# ===================================================================

REQUIRED_FILES = [
    "app.py",
    "Dockerfile",
    "docker-stack.yml",
    "generate_certs.sh",
    "entrypoint.sh",
    "fail2ban/jail.local",
    "fail2ban/filter.d/flask-auth.conf",
    "README.md",
]


def test_all_required_files_exist():
    """Every file listed in the project structure must be present."""
    missing = [f for f in REQUIRED_FILES if not _exists(f)]
    assert not missing, f"Missing required files: {missing}"


# ===================================================================
# 2. app.py — Flask application
# ===================================================================

class TestAppPy:

    def setup_method(self):
        self.src = _read("app.py")

    # -- Routes ----------------------------------------------------------

    def test_health_route_defined(self):
        """GET /health endpoint must exist."""
        assert re.search(r"""['"]/health['"]""", self.src), \
            "app.py must define a /health route"

    def test_login_route_defined(self):
        """POST /login endpoint must exist."""
        assert re.search(r"""['"]/login['"]""", self.src), \
            "app.py must define a /login route"

    def test_login_is_post(self):
        """The /login route must accept POST."""
        assert re.search(r"""methods\s*=\s*\[.*?['"]POST['"].*?\]""", self.src), \
            "/login must accept POST method"

    # -- Response format -------------------------------------------------

    def test_health_returns_healthy_json(self):
        """Health endpoint must return {"status": "healthy"}."""
        assert re.search(r"""["']status["']\s*:\s*["']healthy["']""", self.src), \
            "Health endpoint must return status: healthy"

    def test_login_success_returns_ok(self):
        """Successful login must return {"status": "ok", "user": ...}."""
        assert re.search(r"""["']status["']\s*:\s*["']ok["']""", self.src), \
            "Successful login must return status: ok"

    def test_login_failure_returns_401_message(self):
        """Failed login must return {"status": "error", "message": "authentication failed"}."""
        assert re.search(r"""["']authentication failed["']""", self.src, re.IGNORECASE), \
            "Failed login must include 'authentication failed' message"

    def test_login_success_status_200(self):
        assert re.search(r"""\b200\b""", self.src), \
            "app.py must return HTTP 200 on success"

    def test_login_failure_status_401(self):
        assert re.search(r"""\b401\b""", self.src), \
            "app.py must return HTTP 401 on auth failure"

    # -- PAM authentication ----------------------------------------------

    def test_uses_pam(self):
        """Must authenticate via PAM."""
        assert re.search(r"""import\s+pam|from\s+pam""", self.src), \
            "app.py must import pam for authentication"

    def test_pam_authenticate_call(self):
        assert re.search(r"""\.authenticate\(""", self.src), \
            "app.py must call pam authenticate"

    # -- Logging ---------------------------------------------------------

    def test_logs_failed_login(self):
        """Failed logins must be logged to /var/log/flask-auth.log."""
        assert "/var/log/flask-auth.log" in self.src, \
            "app.py must log to /var/log/flask-auth.log"

    def test_log_format_contains_failed_login(self):
        """Log line must contain 'FAILED LOGIN'."""
        assert "FAILED LOGIN" in self.src, \
            "Log format must include 'FAILED LOGIN'"

    # -- HTTPS / Docker Secrets paths ------------------------------------

    def test_tls_cert_secret_path(self):
        assert "/run/secrets/tls_cert" in self.src, \
            "app.py must reference /run/secrets/tls_cert"

    def test_tls_key_secret_path(self):
        assert "/run/secrets/tls_key" in self.src, \
            "app.py must reference /run/secrets/tls_key"

    def test_ssl_context_usage(self):
        """App must create an SSL context for HTTPS."""
        assert re.search(r"""ssl[._]context|SSLContext|ssl_context""", self.src), \
            "app.py must use an SSL context for HTTPS"

    # -- Port ------------------------------------------------------------

    def test_listens_on_port_5000(self):
        assert re.search(r"""port\s*=\s*5000|:5000""", self.src), \
            "app.py must listen on port 5000"


# ===================================================================
# 3. Dockerfile
# ===================================================================

class TestDockerfile:

    def setup_method(self):
        self.src = _read("Dockerfile")
        self.src_lower = self.src.lower()

    def test_base_image_ubuntu_2204(self):
        assert re.search(r"""FROM\s+ubuntu\s*:\s*22\.04""", self.src, re.IGNORECASE), \
            "Dockerfile must use ubuntu:22.04 base image"

    def test_installs_python3(self):
        assert "python3" in self.src_lower, \
            "Dockerfile must install python3"

    def test_installs_libpam(self):
        assert "libpam" in self.src_lower, \
            "Dockerfile must install libpam0g-dev"

    def test_installs_fail2ban(self):
        assert "fail2ban" in self.src_lower, \
            "Dockerfile must install fail2ban"

    def test_installs_openssl(self):
        assert "openssl" in self.src_lower, \
            "Dockerfile must install openssl"

    def test_installs_flask(self):
        assert "flask" in self.src_lower, \
            "Dockerfile must install flask"

    def test_installs_python_pam(self):
        assert re.search(r"""python.pam""", self.src_lower), \
            "Dockerfile must install python-pam"

    def test_exposes_port_5000(self):
        assert re.search(r"""EXPOSE\s+5000""", self.src, re.IGNORECASE), \
            "Dockerfile must EXPOSE 5000"

    def test_entrypoint_set(self):
        assert re.search(r"""ENTRYPOINT|CMD""", self.src, re.IGNORECASE), \
            "Dockerfile must set an ENTRYPOINT or CMD"

    def test_entrypoint_references_entrypoint_sh(self):
        assert "entrypoint.sh" in self.src, \
            "Dockerfile must use entrypoint.sh"

    def test_copies_app_py(self):
        assert re.search(r"""COPY.*app\.py""", self.src, re.IGNORECASE), \
            "Dockerfile must COPY app.py"

    def test_copies_fail2ban_config(self):
        assert re.search(r"""COPY.*fail2ban""", self.src, re.IGNORECASE), \
            "Dockerfile must COPY fail2ban configuration"


# ===================================================================
# 4. docker-stack.yml
# ===================================================================

class TestDockerStackYml:

    def setup_method(self):
        self.raw = _read("docker-stack.yml")
        self.data = yaml.safe_load(self.raw)

    def test_is_valid_yaml(self):
        assert self.data is not None, "docker-stack.yml must be valid YAML"

    def test_services_key_exists(self):
        assert "services" in self.data, "Stack must define 'services'"

    def test_dashboard_service_exists(self):
        assert "dashboard" in self.data["services"], \
            "Stack must define a service named 'dashboard'"

    def test_port_mapping_8443_to_5000(self):
        svc = self.data["services"]["dashboard"]
        ports = svc.get("ports", [])
        port_strs = [str(p) for p in ports]
        matched = any("8443" in p and "5000" in p for p in port_strs)
        assert matched, "dashboard service must map host 8443 to container 5000"

    def test_secrets_declared_on_service(self):
        svc = self.data["services"]["dashboard"]
        secrets = svc.get("secrets", [])
        secret_names = set()
        for s in secrets:
            if isinstance(s, str):
                secret_names.add(s)
            elif isinstance(s, dict):
                secret_names.add(s.get("source", s.get("name", "")))
        for required in ("tls_cert", "tls_key", "shadow_file"):
            assert required in secret_names, \
                f"dashboard service must declare secret '{required}'"

    def test_top_level_secrets_external(self):
        secrets = self.data.get("secrets", {})
        for name in ("tls_cert", "tls_key", "shadow_file"):
            assert name in secrets, f"Top-level secrets must include '{name}'"
            sec = secrets[name]
            assert sec.get("external") is True, \
                f"Secret '{name}' must be declared as external: true"


# ===================================================================
# 5. generate_certs.sh
# ===================================================================

class TestGenerateCerts:

    def setup_method(self):
        self.src = _read("generate_certs.sh")

    def test_is_bash_script(self):
        assert self.src.strip().startswith("#!"), \
            "generate_certs.sh must start with a shebang"
        assert "bash" in self.src.split("\n")[0], \
            "generate_certs.sh must be a bash script"

    def test_creates_certs_directory(self):
        assert re.search(r"""mkdir.*certs""", self.src), \
            "generate_certs.sh must create the certs directory"

    def test_uses_openssl(self):
        assert "openssl" in self.src, \
            "generate_certs.sh must use openssl"

    def test_generates_rsa_2048_or_higher(self):
        match = re.search(r"""rsa\s*:\s*(\d+)|newkey\s+rsa\s*:\s*(\d+)""", self.src)
        assert match, "generate_certs.sh must specify RSA key size"
        bits = int(match.group(1) or match.group(2))
        assert bits >= 2048, f"RSA key must be >= 2048 bits, got {bits}"

    def test_cert_output_path(self):
        assert re.search(r"""/app/certs/server\.crt|certs/server\.crt|\$CERT_DIR/server\.crt""", self.src), \
            "Must output certificate to /app/certs/server.crt"

    def test_key_output_path(self):
        assert re.search(r"""/app/certs/server\.key|certs/server\.key|\$CERT_DIR/server\.key""", self.src), \
            "Must output key to /app/certs/server.key"

    def test_cn_localhost(self):
        assert re.search(r"""CN\s*=\s*localhost""", self.src), \
            "Certificate CN must be localhost"

    def test_validity_365_days(self):
        assert re.search(r"""365""", self.src), \
            "Certificate must be valid for 365 days"

    def test_self_signed(self):
        assert re.search(r"""-x509""", self.src), \
            "Must generate self-signed certificate (-x509)"

    def test_is_executable(self):
        path = os.path.join(APP_DIR, "generate_certs.sh")
        st = os.stat(path)
        assert st.st_mode & stat.S_IXUSR, \
            "generate_certs.sh must be executable"


# ===================================================================
# 6. entrypoint.sh
# ===================================================================

class TestEntrypoint:

    def setup_method(self):
        self.src = _read("entrypoint.sh")

    def test_is_bash_script(self):
        assert "bash" in self.src.split("\n")[0], \
            "entrypoint.sh must be a bash script"

    def test_copies_shadow_secret(self):
        """Must copy /run/secrets/shadow_file to /etc/shadow."""
        assert "/run/secrets/shadow_file" in self.src, \
            "entrypoint.sh must reference /run/secrets/shadow_file"
        assert "/etc/shadow" in self.src, \
            "entrypoint.sh must write to /etc/shadow"

    def test_shadow_permissions_640(self):
        assert re.search(r"""chmod\s+640\s+/etc/shadow|chmod\s+0640\s+/etc/shadow""", self.src), \
            "entrypoint.sh must set /etc/shadow permissions to 640"

    def test_starts_fail2ban(self):
        assert re.search(r"""fail2ban""", self.src), \
            "entrypoint.sh must start fail2ban"

    def test_launches_flask_app(self):
        assert re.search(r"""python3?\s+.*app\.py|flask\s+run""", self.src), \
            "entrypoint.sh must launch the Flask application"

    def test_secret_rotation_watcher(self):
        """Must have a mechanism to detect shadow_file changes."""
        has_inotify = "inotifywait" in self.src
        has_polling = re.search(r"""while.*true|sleep""", self.src) is not None
        assert has_inotify or has_polling, \
            "entrypoint.sh must have a watcher for secret rotation (inotifywait or polling loop)"

    def test_is_executable(self):
        path = os.path.join(APP_DIR, "entrypoint.sh")
        st = os.stat(path)
        assert st.st_mode & stat.S_IXUSR, \
            "entrypoint.sh must be executable"


# ===================================================================
# 7. fail2ban configuration
# ===================================================================

class TestFail2banJail:

    def setup_method(self):
        self.src = _read("fail2ban/jail.local")

    def test_jail_enabled(self):
        assert re.search(r"""enabled\s*=\s*true""", self.src, re.IGNORECASE), \
            "Jail must be enabled"

    def test_monitors_flask_auth_log(self):
        assert "/var/log/flask-auth.log" in self.src, \
            "Jail must monitor /var/log/flask-auth.log"

    def test_maxretry_3(self):
        match = re.search(r"""maxretry\s*=\s*(\d+)""", self.src)
        assert match, "Jail must define maxretry"
        assert int(match.group(1)) == 3, "maxretry must be 3"

    def test_findtime_300(self):
        match = re.search(r"""findtime\s*=\s*(\d+)""", self.src)
        assert match, "Jail must define findtime"
        assert int(match.group(1)) == 300, "findtime must be 300 seconds"

    def test_bantime_600(self):
        match = re.search(r"""bantime\s*=\s*(\d+)""", self.src)
        assert match, "Jail must define bantime"
        assert int(match.group(1)) == 600, "bantime must be 600 seconds"

    def test_port_5000(self):
        assert re.search(r"""port\s*=\s*5000""", self.src), \
            "Jail must target port 5000"


class TestFail2banFilter:

    def setup_method(self):
        self.src = _read("fail2ban/filter.d/flask-auth.conf")

    def test_has_definition_section(self):
        assert re.search(r"""\[Definition\]""", self.src, re.IGNORECASE), \
            "Filter must have a [Definition] section"

    def test_has_failregex(self):
        assert re.search(r"""failregex\s*=""", self.src), \
            "Filter must define failregex"

    def test_failregex_matches_log_format(self):
        """The failregex must be able to extract HOST from the log format:
        YYYY-MM-DD HH:MM:SS FAILED LOGIN for <username> from <HOST>
        """
        assert "FAILED LOGIN" in self.src, \
            "failregex must match 'FAILED LOGIN' pattern"
        assert "<HOST>" in self.src, \
            "failregex must extract <HOST>"


# ===================================================================
# 8. README.md
# ===================================================================

class TestReadme:

    def setup_method(self):
        self.src = _read("README.md")
        self.src_lower = self.src.lower()

    def test_not_empty(self):
        assert len(self.src.strip()) > 100, \
            "README.md must contain substantial documentation"

    def test_mentions_docker_swarm(self):
        assert "swarm" in self.src_lower, \
            "README must mention Docker Swarm"

    def test_mentions_build(self):
        assert "docker build" in self.src_lower or "build" in self.src_lower, \
            "README must document how to build the image"

    def test_mentions_secret_creation(self):
        assert "docker secret" in self.src_lower or "secret create" in self.src_lower, \
            "README must document Docker secret creation"

    def test_mentions_stack_deploy(self):
        assert "stack deploy" in self.src_lower or "docker stack" in self.src_lower, \
            "README must document stack deployment"

    def test_mentions_login_test(self):
        assert "curl" in self.src_lower or "login" in self.src_lower, \
            "README must show how to test login"

    def test_mentions_secret_rotation(self):
        assert "rotat" in self.src_lower, \
            "README must document secret rotation procedure"

    def test_mentions_fail2ban_or_ban(self):
        assert "fail2ban" in self.src_lower or "ban" in self.src_lower, \
            "README must mention fail2ban / IP banning"


# ===================================================================
# 9. Cross-file consistency checks
# ===================================================================

class TestCrossFileConsistency:
    """Verify that different files reference each other correctly."""

    def test_dockerfile_and_stack_image_consistent(self):
        """The stack file should reference an image that the Dockerfile builds."""
        stack = _read("docker-stack.yml")
        data = yaml.safe_load(stack)
        svc = data["services"]["dashboard"]
        image = svc.get("image", "")
        # Image name should be non-empty (agent must specify what to build)
        # We just verify the service exists and has some image or build context
        assert image or "build" in svc, \
            "dashboard service must specify an image or build context"

    def test_log_path_consistent_across_files(self):
        """app.py, jail.local must all reference the same log path."""
        app_src = _read("app.py")
        jail_src = _read("fail2ban/jail.local")
        log_path = "/var/log/flask-auth.log"
        assert log_path in app_src, "app.py must log to /var/log/flask-auth.log"
        assert log_path in jail_src, "jail.local must monitor /var/log/flask-auth.log"

    def test_filter_name_consistent(self):
        """The jail filter name must match the filter config filename."""
        jail_src = _read("fail2ban/jail.local")
        # jail should reference filter = flask-auth (matching flask-auth.conf)
        match = re.search(r"""filter\s*=\s*(\S+)""", jail_src)
        assert match, "jail.local must specify a filter"
        filter_name = match.group(1).strip()
        filter_conf = f"fail2ban/filter.d/{filter_name}.conf"
        assert _exists(filter_conf), \
            f"Filter config file '{filter_conf}' must exist to match jail filter={filter_name}"
