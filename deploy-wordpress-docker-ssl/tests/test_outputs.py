"""
Tests for WordPress Docker SSL deployment task.
Validates file structure, configuration correctness, security hardening,
and script content — all via static analysis (no running containers).
"""

import os
import re
import stat
import yaml
import pytest

BASE_DIR = "/app"


# ============================================================================
# Helper utilities
# ============================================================================

def read_file(rel_path):
    """Read a file relative to BASE_DIR, return contents or None."""
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def is_executable(rel_path):
    """Check if a file has the executable bit set."""
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.isfile(full):
        return False
    return os.stat(full).st_mode & stat.S_IXUSR != 0


def load_compose():
    """Parse docker-compose.yml and return the dict."""
    content = read_file("docker-compose.yml")
    assert content is not None, "docker-compose.yml does not exist"
    return yaml.safe_load(content)


# ============================================================================
# 1. File existence tests
# ============================================================================

class TestFileStructure:
    """Verify all required files exist at the correct paths."""

    @pytest.mark.parametrize("path", [
        "docker-compose.yml",
        ".env.example",
        "README.md",
        "nginx/default.conf",
        "backup/backup.sh",
        "backup/restore.sh",
        "healthcheck.sh",
    ])
    def test_required_file_exists(self, path):
        full = os.path.join(BASE_DIR, path)
        assert os.path.isfile(full), f"Required file missing: {path}"
        # Also verify file is non-empty
        assert os.path.getsize(full) > 0, f"File is empty: {path}"

    @pytest.mark.parametrize("path", [
        "backup/backup.sh",
        "backup/restore.sh",
        "healthcheck.sh",
    ])
    def test_scripts_are_executable(self, path):
        assert is_executable(path), f"{path} must be executable"

    @pytest.mark.parametrize("path", [
        "backup/backup.sh",
        "backup/restore.sh",
        "healthcheck.sh",
    ])
    def test_scripts_have_shebang(self, path):
        content = read_file(path)
        assert content is not None
        assert content.strip().startswith("#!/bin/bash") or \
               content.strip().startswith("#!/usr/bin/env bash"), \
            f"{path} must start with a bash shebang"


# ============================================================================
# 2. docker-compose.yml tests
# ============================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and content."""

    def test_has_services_section(self):
        dc = load_compose()
        assert "services" in dc, "docker-compose.yml must have a 'services' section"

    @pytest.mark.parametrize("svc", [
        "wordpress1", "wordpress2", "db", "nginx", "minio", "certbot", "backup",
    ])
    def test_required_service_exists(self, svc):
        dc = load_compose()
        services = dc.get("services", {})
        assert svc in services, f"Service '{svc}' missing from docker-compose.yml"

    def test_wordpress_images(self):
        dc = load_compose()
        for svc in ("wordpress1", "wordpress2"):
            img = dc["services"][svc].get("image", "")
            assert "wordpress" in img.lower(), f"{svc} must use a wordpress image"

    def test_db_image_is_mariadb(self):
        dc = load_compose()
        img = dc["services"]["db"].get("image", "")
        assert "mariadb" in img.lower(), "db service must use mariadb image"

    def test_minio_image(self):
        dc = load_compose()
        img = dc["services"]["minio"].get("image", "")
        assert "minio" in img.lower(), "minio service must use a minio image"

    def test_certbot_image(self):
        dc = load_compose()
        img = dc["services"]["certbot"].get("image", "")
        assert "certbot" in img.lower(), "certbot service must use a certbot image"

    # --- Named volumes ---
    @pytest.mark.parametrize("vol", ["db_data", "wp_uploads", "minio_data", "certbot_etc"])
    def test_named_volume_defined(self, vol):
        dc = load_compose()
        volumes = dc.get("volumes", {})
        assert volumes is not None, "Top-level 'volumes' section missing"
        assert vol in volumes, f"Named volume '{vol}' not defined at top level"

    # --- Network ---
    def test_wp_network_defined(self):
        dc = load_compose()
        networks = dc.get("networks", {})
        assert networks is not None, "Top-level 'networks' section missing"
        assert "wp_network" in networks, "Network 'wp_network' not defined"

    def test_all_services_on_wp_network(self):
        dc = load_compose()
        for svc_name, svc_def in dc.get("services", {}).items():
            nets = svc_def.get("networks", [])
            if isinstance(nets, list):
                assert "wp_network" in nets, \
                    f"Service '{svc_name}' must be on wp_network"
            elif isinstance(nets, dict):
                assert "wp_network" in nets, \
                    f"Service '{svc_name}' must be on wp_network"

    # --- Port mappings ---
    def test_nginx_ports(self):
        dc = load_compose()
        nginx = dc["services"]["nginx"]
        ports_raw = nginx.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "80" in ports_str, "Nginx must map port 80"
        assert "443" in ports_str, "Nginx must map port 443"

    def test_minio_ports(self):
        dc = load_compose()
        minio = dc["services"]["minio"]
        ports_raw = minio.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "9000" in ports_str, "MinIO must expose port 9000"
        assert "9001" in ports_str, "MinIO must expose port 9001"

    # --- Security: db must NOT publish ports ---
    def test_db_no_published_ports(self):
        dc = load_compose()
        db = dc["services"]["db"]
        ports = db.get("ports", [])
        assert len(ports) == 0 or ports is None, \
            "db service must NOT publish any ports to the host"

    # --- WordPress shared volume ---
    def test_wordpress_shared_volume(self):
        dc = load_compose()
        for svc in ("wordpress1", "wordpress2"):
            vols = dc["services"][svc].get("volumes", [])
            vol_str = " ".join(str(v) for v in vols)
            assert "wp_uploads" in vol_str, \
                f"{svc} must mount the wp_uploads volume"

    # --- db volume ---
    def test_db_data_volume(self):
        dc = load_compose()
        vols = dc["services"]["db"].get("volumes", [])
        vol_str = " ".join(str(v) for v in vols)
        assert "db_data" in vol_str, "db must mount db_data volume"

    # --- nginx depends_on ---
    def test_nginx_depends_on_wordpress(self):
        dc = load_compose()
        deps = dc["services"]["nginx"].get("depends_on", [])
        if isinstance(deps, dict):
            deps = list(deps.keys())
        assert "wordpress1" in deps, "nginx must depend on wordpress1"
        assert "wordpress2" in deps, "nginx must depend on wordpress2"

    # --- certbot shares certbot_etc volume ---
    def test_certbot_volume(self):
        dc = load_compose()
        vols = dc["services"]["certbot"].get("volumes", [])
        vol_str = " ".join(str(v) for v in vols)
        assert "certbot_etc" in vol_str, "certbot must mount certbot_etc volume"

    # --- backup sidecar volumes ---
    def test_backup_mounts_required_volumes(self):
        dc = load_compose()
        vols = dc["services"]["backup"].get("volumes", [])
        vol_str = " ".join(str(v) for v in vols)
        assert "db_data" in vol_str, "backup must mount db_data"
        assert "wp_uploads" in vol_str, "backup must mount wp_uploads"


# ============================================================================
# 3. Nginx configuration tests
# ============================================================================

class TestNginxConfig:
    """Validate nginx/default.conf content."""

    def _conf(self):
        content = read_file("nginx/default.conf")
        assert content is not None, "nginx/default.conf missing"
        return content

    def test_upstream_block_exists(self):
        conf = self._conf()
        assert re.search(r'upstream\s+wordpress\s*\{', conf), \
            "Must define an upstream block named 'wordpress'"

    def test_upstream_contains_wordpress1(self):
        conf = self._conf()
        assert re.search(r'server\s+wordpress1[:\s]', conf), \
            "Upstream must include wordpress1"

    def test_upstream_contains_wordpress2(self):
        conf = self._conf()
        assert re.search(r'server\s+wordpress2[:\s]', conf), \
            "Upstream must include wordpress2"

    def test_upstream_port_8080(self):
        conf = self._conf()
        assert "8080" in conf, "Upstream servers must use port 8080"

    def test_http_to_https_redirect(self):
        conf = self._conf()
        assert re.search(r'listen\s+80', conf), "Must have a server listening on port 80"
        assert re.search(r'return\s+301\s+https', conf), \
            "Port 80 server must redirect to HTTPS with 301"

    def test_ssl_server_block(self):
        conf = self._conf()
        assert re.search(r'listen\s+443\s+.*ssl', conf) or \
               re.search(r'listen\s+443\s+ssl', conf), \
            "Must have a server listening on 443 with ssl"

    def test_ssl_certificate_paths(self):
        conf = self._conf()
        assert re.search(r'ssl_certificate\s+/etc/letsencrypt/', conf), \
            "SSL certificate must reference /etc/letsencrypt/"
        assert re.search(r'ssl_certificate_key\s+/etc/letsencrypt/', conf), \
            "SSL certificate key must reference /etc/letsencrypt/"

    def test_tls_protocols_secure(self):
        conf = self._conf()
        proto_match = re.search(r'ssl_protocols\s+([^;]+);', conf)
        assert proto_match, "Must set ssl_protocols directive"
        protocols = proto_match.group(1)
        assert "TLSv1.2" in protocols, "Must allow TLSv1.2"
        assert "TLSv1.3" in protocols, "Must allow TLSv1.3"
        # Must NOT allow weak protocols
        # Check that TLSv1 alone (not TLSv1.2/1.3) is not present
        # and TLSv1.1 is not present
        tokens = protocols.split()
        for t in tokens:
            assert t not in ("TLSv1", "TLSv1.1"), \
                f"Weak protocol {t} must not be allowed"

    def test_ssl_ciphers(self):
        conf = self._conf()
        assert re.search(r'ssl_ciphers\s+.*HIGH:!aNULL:!MD5', conf), \
            "ssl_ciphers must be set to HIGH:!aNULL:!MD5"

    def test_proxy_set_headers(self):
        conf = self._conf()
        assert re.search(r'proxy_set_header\s+Host\s', conf), \
            "Must set proxy_set_header Host"
        assert re.search(r'proxy_set_header\s+X-Real-IP\s', conf), \
            "Must set proxy_set_header X-Real-IP"
        assert re.search(r'proxy_set_header\s+X-Forwarded-Proto\s', conf), \
            "Must set proxy_set_header X-Forwarded-Proto"

    def test_proxy_pass_to_upstream(self):
        conf = self._conf()
        assert re.search(r'proxy_pass\s+https?://wordpress', conf), \
            "SSL server must proxy_pass to the wordpress upstream"


# ============================================================================
# 4. .env.example tests
# ============================================================================

class TestEnvExample:
    """Validate .env.example has all required keys with comments."""

    REQUIRED_KEYS = [
        "MYSQL_ROOT_PASSWORD",
        "MYSQL_DATABASE",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "WORDPRESS_DB_HOST",
        "WORDPRESS_DB_USER",
        "WORDPRESS_DB_PASSWORD",
        "WORDPRESS_DB_NAME",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "DOMAIN",
    ]

    def _env(self):
        content = read_file(".env.example")
        assert content is not None, ".env.example missing"
        return content

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_required_key_present(self, key):
        env = self._env()
        # Key should appear as KEY= or KEY = at start of a line
        assert re.search(rf'^{re.escape(key)}\s*=', env, re.MULTILINE), \
            f"Key '{key}' missing from .env.example"

    def test_has_comments(self):
        """Each key should have a comment (above or inline) explaining its purpose."""
        env = self._env()
        comment_lines = [l for l in env.splitlines() if l.strip().startswith("#")]
        # At minimum, there should be several comment lines (one per key is ideal)
        assert len(comment_lines) >= 5, \
            ".env.example must have comments explaining the keys"


# ============================================================================
# 5. Backup script tests
# ============================================================================

class TestBackupScript:
    """Validate backup/backup.sh content."""

    def _script(self):
        content = read_file("backup/backup.sh")
        assert content is not None, "backup/backup.sh missing"
        return content

    def test_uses_mysqldump(self):
        script = self._script()
        assert "mysqldump" in script, "backup.sh must use mysqldump"

    def test_date_stamp_format(self):
        """Backup filenames must include YYYY-MM-DD date stamp."""
        script = self._script()
        # Should use date command with +%F or +%Y-%m-%d
        assert re.search(r'date\s+\+%F', script) or \
               re.search(r'date\s+\+%Y-%m-%d', script) or \
               re.search(r'date\s+"\+%Y-%m-%d"', script) or \
               re.search(r"date\s+'\+%Y-%m-%d'", script) or \
               re.search(r"date\s+'\+%F'", script) or \
               re.search(r'date\s+"\+%F"', script), \
            "Must use date format YYYY-MM-DD (date +%F or +%Y-%m-%d)"

    def test_uploads_to_minio(self):
        """Must upload to MinIO using mc or aws s3 cp with endpoint-url."""
        script = self._script()
        uses_mc = "mc cp" in script or "mc mirror" in script
        uses_aws = "aws s3" in script and "endpoint" in script.lower()
        assert uses_mc or uses_aws, \
            "Must upload to MinIO via mc CLI or aws s3 cp --endpoint-url"

    def test_backups_bucket(self):
        script = self._script()
        assert "backups" in script, "Must reference a MinIO bucket named 'backups'"

    def test_no_hardcoded_passwords(self):
        """Credentials must come from env vars, not hardcoded."""
        script = self._script()
        # Remove comment lines before checking
        code_lines = [l for l in script.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        # Should reference env vars for DB password
        assert re.search(r'\$\{?\w*(PASSWORD|PASS|SECRET)\w*\}?', code, re.IGNORECASE), \
            "Must use environment variables for credentials"

    def test_sql_dump_filename(self):
        script = self._script()
        assert re.search(r'db-.*\.sql', script), \
            "SQL dump filename must follow db-<date>.sql pattern"

    def test_uploads_archive_filename(self):
        script = self._script()
        assert re.search(r'uploads-.*\.tar\.gz', script), \
            "Uploads archive must follow uploads-<date>.tar.gz pattern"


# ============================================================================
# 6. Restore script tests
# ============================================================================

class TestRestoreScript:
    """Validate backup/restore.sh content."""

    def _script(self):
        content = read_file("backup/restore.sh")
        assert content is not None, "backup/restore.sh missing"
        return content

    def test_accepts_date_argument(self):
        """Must accept a date stamp as the first argument."""
        script = self._script()
        # Should reference $1 or ${1} for the date argument
        assert re.search(r'\$\{?1\}?', script), \
            "restore.sh must accept a date stamp as argument ($1)"

    def test_downloads_from_minio(self):
        """Must download from MinIO backups bucket."""
        script = self._script()
        uses_mc = "mc cp" in script or "mc mirror" in script
        uses_aws = "aws s3" in script and "endpoint" in script.lower()
        assert uses_mc or uses_aws, \
            "Must download from MinIO via mc CLI or aws s3 cp --endpoint-url"

    def test_restores_database(self):
        """Must use mysql CLI to import the SQL dump."""
        script = self._script()
        assert "mysql" in script, "Must use mysql CLI to restore database"

    def test_extracts_uploads_archive(self):
        """Must extract the tar.gz archive."""
        script = self._script()
        assert "tar" in script, "Must use tar to extract uploads archive"

    def test_success_message(self):
        script = self._script()
        assert "Restore completed successfully" in script, \
            "Must print exactly 'Restore completed successfully' on success"

    def test_failure_message(self):
        script = self._script()
        assert "Restore failed" in script, \
            "Must print exactly 'Restore failed' on failure"

    def test_failure_exit_code(self):
        script = self._script()
        assert "exit 1" in script, \
            "Must exit with code 1 on failure"

    def test_no_hardcoded_passwords(self):
        """Credentials must come from env vars, not hardcoded."""
        script = self._script()
        code_lines = [l for l in script.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        assert re.search(r'\$\{?\w*(PASSWORD|PASS|SECRET)\w*\}?', code, re.IGNORECASE), \
            "Must use environment variables for credentials"


# ============================================================================
# 7. Healthcheck script tests
# ============================================================================

class TestHealthcheck:
    """Validate healthcheck.sh content."""

    def _script(self):
        content = read_file("healthcheck.sh")
        assert content is not None, "healthcheck.sh missing"
        return content

    def test_checks_containers_running(self):
        """Must check that docker compose containers are running."""
        script = self._script()
        assert "docker" in script, "Must use docker commands to check containers"

    def test_checks_https(self):
        """Must attempt an HTTPS request to localhost."""
        script = self._script()
        assert re.search(r'https://localhost', script), \
            "Must check https://localhost"

    def test_allows_self_signed_certs(self):
        """Must allow self-signed certs (curl -k or --insecure)."""
        script = self._script()
        assert "-k" in script or "--insecure" in script, \
            "Must allow self-signed certs with curl -k or --insecure"

    def test_ok_output(self):
        script = self._script()
        # Must print exactly OK (as a standalone word in an echo/printf)
        assert re.search(r'(echo|printf)\s+.*"?OK"?', script), \
            "Must print 'OK' when healthy"

    def test_fail_output(self):
        script = self._script()
        assert re.search(r'(echo|printf)\s+.*"?FAIL"?', script), \
            "Must print 'FAIL' when unhealthy"

    def test_fail_exit_code(self):
        script = self._script()
        assert "exit 1" in script, "Must exit with code 1 on failure"


# ============================================================================
# 8. README.md tests
# ============================================================================

class TestReadme:
    """Validate README.md contains required sections."""

    def _readme(self):
        content = read_file("README.md")
        assert content is not None, "README.md missing"
        return content.lower()

    def test_start_instructions(self):
        readme = self._readme()
        assert "docker compose up" in readme or "docker-compose up" in readme, \
            "README must explain how to start the stack with docker compose up"

    def test_stop_instructions(self):
        readme = self._readme()
        assert "docker compose down" in readme or "docker-compose down" in readme, \
            "README must explain how to stop/tear down with docker compose down"

    def test_restore_instructions(self):
        readme = self._readme()
        assert "restore" in readme, \
            "README must explain how to restore from backup (reference restore.sh)"


# ============================================================================
# 9. Security hardening cross-checks
# ============================================================================

class TestSecurityHardening:
    """Cross-cutting security validation across all files."""

    def test_db_no_ports_in_compose_raw(self):
        """Double-check db has no ports by scanning raw YAML text."""
        content = read_file("docker-compose.yml")
        assert content is not None
        # Find the db service block and check it has no 'ports:' key
        # Use YAML parsing for reliability
        dc = yaml.safe_load(content)
        db = dc.get("services", {}).get("db", {})
        ports = db.get("ports")
        assert ports is None or ports == [], \
            "db service must not expose any ports to the host"

    def test_nginx_no_weak_tls_in_raw(self):
        """Ensure no TLSv1 or TLSv1.1 appears as allowed protocol."""
        conf = read_file("nginx/default.conf")
        assert conf is not None
        proto_match = re.search(r'ssl_protocols\s+([^;]+);', conf)
        assert proto_match, "ssl_protocols directive missing"
        tokens = proto_match.group(1).split()
        weak = [t for t in tokens if t in ("TLSv1", "TLSv1.1")]
        assert len(weak) == 0, f"Weak TLS protocols found: {weak}"

    def test_backup_script_no_literal_passwords(self):
        """Backup script must not contain obvious hardcoded password strings."""
        script = read_file("backup/backup.sh")
        assert script is not None
        code_lines = [l for l in script.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        # Check that mysqldump line uses a variable, not a literal password
        dump_lines = [l for l in code_lines if "mysqldump" in l]
        for line in dump_lines:
            # The password arg should reference a variable ($VAR or ${VAR})
            if "-p" in line:
                # After -p there should be a $ reference, not a plain string
                pw_match = re.search(r'-p(["\']?)(\$)', line)
                assert pw_match or re.search(r'-p\$', line) or \
                       re.search(r'-p"\$', line), \
                    "mysqldump password must use env variable, not hardcoded value"

    def test_restore_script_no_literal_passwords(self):
        """Restore script must not contain obvious hardcoded password strings."""
        script = read_file("backup/restore.sh")
        assert script is not None
        code_lines = [l for l in script.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
        code = "\n".join(code_lines)
        # Check that mysql import line uses a variable
        mysql_lines = [l for l in code_lines
                       if "mysql" in l and "mysqldump" not in l and "<" in l]
        for line in mysql_lines:
            if "-p" in line:
                assert re.search(r'-p\$', line) or re.search(r'-p"\$', line), \
                    "mysql restore password must use env variable"

    def test_compose_env_vars_use_references(self):
        """docker-compose.yml should use ${VAR} or env_file, not hardcoded credentials."""
        content = read_file("docker-compose.yml")
        assert content is not None
        # The compose file should either use env_file or ${VAR} syntax for secrets.
        # Check that at least some ${...} references or env_file directives exist.
        uses_var_refs = "${" in content
        uses_env_file = "env_file" in content
        assert uses_var_refs or uses_env_file, \
            "docker-compose.yml must use ${VAR} references or env_file for configuration"

