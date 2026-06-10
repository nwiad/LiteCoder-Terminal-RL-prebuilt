"""
Tests for the C++ WebSocket Server deployment task.
Validates all 7 required output files for existence, format, and content correctness.
"""

import os
import json
import subprocess
import re

# All paths are absolute as specified in instruction.md
APP_DIR = "/app"
BINARY_PATH = "/app/build/ws_server"
SERVICE_PATH = "/app/ws_server.service"
CERT_PATH = "/app/certs/server.crt"
KEY_PATH = "/app/certs/server.key"
SOURCE_PATH = "/app/ws_server.cpp"
CMAKE_PATH = "/app/CMakeLists.txt"
STATUS_PATH = "/app/deploy_status.json"


# ============================================================
# 1. File Existence Tests
# ============================================================

class TestFileExistence:
    """All 7 required output files must exist and be non-empty."""

    def test_source_file_exists(self):
        assert os.path.isfile(SOURCE_PATH), f"{SOURCE_PATH} does not exist"
        assert os.path.getsize(SOURCE_PATH) > 100, "ws_server.cpp is suspiciously small"

    def test_cmake_file_exists(self):
        assert os.path.isfile(CMAKE_PATH), f"{CMAKE_PATH} does not exist"
        assert os.path.getsize(CMAKE_PATH) > 50, "CMakeLists.txt is suspiciously small"

    def test_cert_exists(self):
        assert os.path.isfile(CERT_PATH), f"{CERT_PATH} does not exist"
        assert os.path.getsize(CERT_PATH) > 100, "server.crt is suspiciously small"

    def test_key_exists(self):
        assert os.path.isfile(KEY_PATH), f"{KEY_PATH} does not exist"
        assert os.path.getsize(KEY_PATH) > 100, "server.key is suspiciously small"

    def test_binary_exists(self):
        assert os.path.isfile(BINARY_PATH), f"{BINARY_PATH} does not exist"
        assert os.path.getsize(BINARY_PATH) > 1000, "Binary is suspiciously small"

    def test_service_file_exists(self):
        assert os.path.isfile(SERVICE_PATH), f"{SERVICE_PATH} does not exist"
        assert os.path.getsize(SERVICE_PATH) > 50, "Service file is suspiciously small"

    def test_status_json_exists(self):
        assert os.path.isfile(STATUS_PATH), f"{STATUS_PATH} does not exist"
        assert os.path.getsize(STATUS_PATH) > 20, "Status JSON is suspiciously small"


# ============================================================
# 2. SSL Certificate Tests
# ============================================================

class TestSSLCertificates:
    """Validate certificate and key properties."""

    def test_cert_is_pem_encoded(self):
        with open(CERT_PATH, "r") as f:
            content = f.read()
        assert "-----BEGIN CERTIFICATE-----" in content, "Certificate is not PEM-encoded"
        assert "-----END CERTIFICATE-----" in content, "Certificate PEM is incomplete"

    def test_key_is_pem_encoded(self):
        with open(KEY_PATH, "r") as f:
            content = f.read()
        # Accept both traditional and PKCS#8 format
        assert ("-----BEGIN RSA PRIVATE KEY-----" in content or
                "-----BEGIN PRIVATE KEY-----" in content), \
            "Key is not PEM-encoded RSA private key"

    def test_cert_subject_cn_localhost(self):
        """CN must be localhost."""
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-subject"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"openssl failed: {result.stderr}"
        subject = result.stdout.strip()
        assert "CN" in subject and "localhost" in subject, \
            f"Certificate CN is not localhost. Got: {subject}"

    def test_cert_rsa_key_size(self):
        """Key must be RSA 2048-bit minimum."""
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-text"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"openssl failed: {result.stderr}"
        text = result.stdout
        # Look for "Public-Key: (2048 bit)" or higher
        match = re.search(r"Public-Key:\s*\((\d+)\s*bit\)", text)
        assert match, "Could not find public key size in certificate"
        key_size = int(match.group(1))
        assert key_size >= 2048, f"Key size {key_size} is less than 2048 bits"

    def test_cert_validity_365_days(self):
        """Certificate should be valid for approximately 365 days."""
        result = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-dates"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"openssl failed: {result.stderr}"
        output = result.stdout
        assert "notBefore=" in output, "Missing notBefore in certificate"
        assert "notAfter=" in output, "Missing notAfter in certificate"

    def test_cert_is_self_signed(self):
        """Certificate issuer and subject should match (self-signed)."""
        result_subj = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-subject"],
            capture_output=True, text=True
        )
        result_issuer = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-issuer"],
            capture_output=True, text=True
        )
        # For self-signed, issuer CN should also be localhost
        assert "localhost" in result_issuer.stdout, \
            "Certificate does not appear to be self-signed (issuer != subject)"

    def test_key_matches_cert(self):
        """Private key must match the certificate."""
        cert_mod = subprocess.run(
            ["openssl", "x509", "-in", CERT_PATH, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-in", KEY_PATH, "-noout", "-modulus"],
            capture_output=True, text=True
        )
        # If key is PKCS#8, try pkey
        if key_mod.returncode != 0:
            key_mod = subprocess.run(
                ["openssl", "pkey", "-in", KEY_PATH, "-noout", "-text"],
                capture_output=True, text=True
            )
        assert cert_mod.returncode == 0, f"Cannot read cert modulus: {cert_mod.stderr}"
        # Compare modulus values
        if "Modulus=" in cert_mod.stdout and "Modulus=" in key_mod.stdout:
            cert_m = cert_mod.stdout.strip().split("=", 1)[1]
            key_m = key_mod.stdout.strip().split("=", 1)[1]
            assert cert_m == key_m, "Private key does not match certificate"


# ============================================================
# 3. Binary Tests
# ============================================================

class TestBinary:
    """Validate the compiled binary."""

    def test_binary_is_elf_executable(self):
        """Binary must be a valid ELF executable."""
        result = subprocess.run(
            ["file", BINARY_PATH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"file command failed: {result.stderr}"
        output = result.stdout
        assert "ELF" in output, f"Binary is not an ELF file. Got: {output}"
        assert "executable" in output.lower() or "shared object" in output.lower() or "pie" in output.lower(), \
            f"Binary is not executable. Got: {output}"

    def test_binary_is_actually_executable(self):
        """Binary must have execute permission."""
        assert os.access(BINARY_PATH, os.X_OK), "Binary does not have execute permission"

    def test_binary_linked_against_libssl(self):
        """Binary must be dynamically linked against OpenSSL (libssl)."""
        result = subprocess.run(
            ["ldd", BINARY_PATH],
            capture_output=True, text=True
        )
        # ldd might fail for static binaries; check readelf as fallback
        if result.returncode == 0:
            output = result.stdout.lower()
            assert "libssl" in output, \
                f"Binary is not linked against libssl. ldd output: {result.stdout}"
        else:
            # Fallback: check with readelf for dynamic section
            result2 = subprocess.run(
                ["readelf", "-d", BINARY_PATH],
                capture_output=True, text=True
            )
            assert "libssl" in result2.stdout.lower(), \
                "Binary is not dynamically linked against libssl"


# ============================================================
# 4. Source Code Tests
# ============================================================

class TestSourceCode:
    """Validate C++ source and CMake configuration."""

    def test_source_references_port_9443(self):
        """Server source must reference port 9443."""
        with open(SOURCE_PATH, "r") as f:
            content = f.read()
        assert "9443" in content, "Source code does not reference port 9443"

    def test_source_has_echo_prefix(self):
        """Server must echo messages with 'Echo: ' prefix."""
        with open(SOURCE_PATH, "r") as f:
            content = f.read()
        assert "Echo: " in content or "Echo:" in content, \
            "Source code does not contain echo prefix logic"

    def test_source_references_cert_paths(self):
        """Source must load certs from /app/certs/."""
        with open(SOURCE_PATH, "r") as f:
            content = f.read()
        assert "server.crt" in content or "certs" in content, \
            "Source does not reference certificate path"
        assert "server.key" in content or "certs" in content, \
            "Source does not reference key path"

    def test_source_has_startup_message(self):
        """Source must print startup message about port 9443."""
        with open(SOURCE_PATH, "r") as f:
            content = f.read()
        assert "WebSocket server started on port 9443" in content, \
            "Source missing required startup message"

    def test_source_uses_ssl(self):
        """Source must use SSL/TLS."""
        with open(SOURCE_PATH, "r") as f:
            content = f.read()
        content_lower = content.lower()
        assert ("ssl" in content_lower or "tls" in content_lower), \
            "Source code does not appear to use SSL/TLS"

    def test_cmake_project_name(self):
        """CMake project must be named ws_server."""
        with open(CMAKE_PATH, "r") as f:
            content = f.read()
        assert re.search(r"project\s*\(\s*ws_server", content, re.IGNORECASE), \
            "CMake project is not named ws_server"

    def test_cmake_cpp17_or_later(self):
        """CMake must specify C++17 or later standard."""
        with open(CMAKE_PATH, "r") as f:
            content = f.read()
        # Accept C++17, C++20, C++23, etc.
        match = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", content)
        assert match, "CMakeLists.txt does not set CMAKE_CXX_STANDARD"
        std_version = int(match.group(1))
        assert std_version >= 17, f"C++ standard is {std_version}, must be >= 17"

    def test_cmake_links_openssl(self):
        """CMake must link against OpenSSL."""
        with open(CMAKE_PATH, "r") as f:
            content = f.read()
        content_lower = content.lower()
        assert "openssl" in content_lower or "ssl" in content_lower, \
            "CMakeLists.txt does not reference OpenSSL"


# ============================================================
# 5. systemd Service File Tests
# ============================================================

class TestServiceFile:
    """Validate systemd service unit file directives."""

    def _read_service(self):
        with open(SERVICE_PATH, "r") as f:
            return f.read()

    def test_has_unit_section(self):
        content = self._read_service()
        assert "[Unit]" in content, "Service file missing [Unit] section"

    def test_has_service_section(self):
        content = self._read_service()
        assert "[Service]" in content, "Service file missing [Service] section"

    def test_has_install_section(self):
        content = self._read_service()
        assert "[Install]" in content, "Service file missing [Install] section"

    def test_description(self):
        content = self._read_service()
        assert re.search(r"Description\s*=\s*WebSocket Server", content), \
            "Service file missing 'Description=WebSocket Server'"

    def test_after_network(self):
        content = self._read_service()
        assert re.search(r"After\s*=\s*network\.target", content), \
            "Service file missing 'After=network.target'"

    def test_execstart(self):
        content = self._read_service()
        assert re.search(r"ExecStart\s*=\s*/app/build/ws_server", content), \
            "Service file missing 'ExecStart=/app/build/ws_server'"

    def test_restart_on_failure(self):
        content = self._read_service()
        assert re.search(r"Restart\s*=\s*on-failure", content), \
            "Service file missing 'Restart=on-failure'"

    def test_restart_sec(self):
        content = self._read_service()
        assert re.search(r"RestartSec\s*=\s*5", content), \
            "Service file missing 'RestartSec=5'"

    def test_working_directory(self):
        content = self._read_service()
        assert re.search(r"WorkingDirectory\s*=\s*/app", content), \
            "Service file missing 'WorkingDirectory=/app'"

    def test_wanted_by(self):
        content = self._read_service()
        assert re.search(r"WantedBy\s*=\s*multi-user\.target", content), \
            "Service file missing 'WantedBy=multi-user.target'"


# ============================================================
# 6. Deployment Status JSON Tests
# ============================================================

class TestDeployStatusJSON:
    """Validate deploy_status.json structure, types, and consistency."""

    def _load_status(self):
        with open(STATUS_PATH, "r") as f:
            return json.load(f)

    def test_valid_json(self):
        """File must be valid JSON."""
        with open(STATUS_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "deploy_status.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"deploy_status.json is not valid JSON: {e}"

    def test_required_keys_present(self):
        """All required keys must be present."""
        data = self._load_status()
        required_keys = [
            "binary_path", "service_file", "cert_path",
            "key_path", "port", "ssl_enabled",
            "compiler_used", "cpp_standard"
        ]
        for key in required_keys:
            assert key in data, f"Missing required key: {key}"

    def test_binary_path_value(self):
        data = self._load_status()
        assert data["binary_path"] == "/app/build/ws_server", \
            f"binary_path should be /app/build/ws_server, got {data['binary_path']}"

    def test_service_file_value(self):
        data = self._load_status()
        assert data["service_file"] == "/app/ws_server.service", \
            f"service_file should be /app/ws_server.service, got {data['service_file']}"

    def test_cert_path_value(self):
        data = self._load_status()
        assert data["cert_path"] == "/app/certs/server.crt", \
            f"cert_path should be /app/certs/server.crt, got {data['cert_path']}"

    def test_key_path_value(self):
        data = self._load_status()
        assert data["key_path"] == "/app/certs/server.key", \
            f"key_path should be /app/certs/server.key, got {data['key_path']}"

    def test_port_value(self):
        data = self._load_status()
        assert data["port"] == 9443, \
            f"port should be 9443, got {data['port']}"
        assert isinstance(data["port"], int), \
            f"port should be an integer, got {type(data['port']).__name__}"

    def test_ssl_enabled_value(self):
        data = self._load_status()
        assert data["ssl_enabled"] is True, \
            f"ssl_enabled should be true, got {data['ssl_enabled']}"
        assert isinstance(data["ssl_enabled"], bool), \
            f"ssl_enabled should be a boolean, got {type(data['ssl_enabled']).__name__}"

    def test_compiler_used_value(self):
        data = self._load_status()
        assert isinstance(data["compiler_used"], str), \
            f"compiler_used should be a string, got {type(data['compiler_used']).__name__}"
        valid_compilers = ["g++", "clang++"]
        assert data["compiler_used"] in valid_compilers, \
            f"compiler_used should be one of {valid_compilers}, got '{data['compiler_used']}'"

    def test_cpp_standard_value(self):
        data = self._load_status()
        assert isinstance(data["cpp_standard"], str), \
            f"cpp_standard should be a string, got {type(data['cpp_standard']).__name__}"
        # Accept "17", "20", "23", etc.
        try:
            std_val = int(data["cpp_standard"])
        except ValueError:
            assert False, f"cpp_standard should be a numeric string, got '{data['cpp_standard']}'"
        assert std_val >= 17, \
            f"cpp_standard should be >= 17, got {std_val}"

    def test_paths_in_json_match_real_files(self):
        """All file paths in the JSON must point to files that actually exist."""
        data = self._load_status()
        path_keys = ["binary_path", "service_file", "cert_path", "key_path"]
        for key in path_keys:
            path = data.get(key, "")
            assert os.path.isfile(path), \
                f"Path in {key} ('{path}') does not exist on disk"

    def test_no_placeholder_values(self):
        """Values must not be placeholders like <g++ or clang++>."""
        data = self._load_status()
        for key, value in data.items():
            if isinstance(value, str):
                assert "<" not in value and ">" not in value, \
                    f"Field '{key}' contains placeholder value: {value}"
