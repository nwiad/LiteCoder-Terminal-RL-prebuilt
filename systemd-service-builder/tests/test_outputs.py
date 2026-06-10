"""
Tests for the Automated Systemd Service Builder task.

Validates that build.sh correctly:
1. Compiles C source into a binary
2. Generates a systemd service unit file with correct format
3. Generates an installation script with all required commands
4. Handles error cases (missing source, compilation failure)
5. Applies default values for optional config fields
"""

import os
import stat
import json
import subprocess
import shutil
import tempfile

APP_DIR = "/app"
BUILD_DIR = "/app/build"
CONFIG_FILE = "/app/service_config.json"
BUILD_SCRIPT = "/app/build.sh"
TEST_DATA_DIR = "/app/test_data"


def _read_config(path=CONFIG_FILE):
    with open(path, "r") as f:
        return json.load(f)


def _read_file(path):
    with open(path, "r") as f:
        return f.read()


# ============================================================================
# 1. build.sh existence and executability
# ============================================================================

class TestBuildScriptExists:
    def test_build_sh_exists(self):
        assert os.path.isfile(BUILD_SCRIPT), f"{BUILD_SCRIPT} does not exist"

    def test_build_sh_is_shell_script(self):
        content = _read_file(BUILD_SCRIPT)
        first_line = content.strip().splitlines()[0]
        assert first_line.startswith("#!"), "build.sh must start with a shebang line"
        assert "bash" in first_line or "sh" in first_line, "build.sh shebang must reference bash or sh"


# ============================================================================
# 2. Build directory and compiled binary
# ============================================================================

class TestBuildOutputs:
    def test_build_directory_exists(self):
        assert os.path.isdir(BUILD_DIR), f"{BUILD_DIR} directory does not exist"

    def test_compiled_binary_exists(self):
        config = _read_config()
        binary_path = os.path.join(BUILD_DIR, config["service_name"])
        assert os.path.isfile(binary_path), f"Compiled binary {binary_path} does not exist"

    def test_compiled_binary_is_executable(self):
        config = _read_config()
        binary_path = os.path.join(BUILD_DIR, config["service_name"])
        assert os.path.isfile(binary_path), f"Binary {binary_path} not found"
        file_stat = os.stat(binary_path)
        assert file_stat.st_mode & stat.S_IXUSR, "Binary must be executable (user execute bit)"

    def test_compiled_binary_is_elf(self):
        """Verify the binary is actually a compiled ELF executable, not a dummy file."""
        config = _read_config()
        binary_path = os.path.join(BUILD_DIR, config["service_name"])
        assert os.path.isfile(binary_path), f"Binary {binary_path} not found"
        with open(binary_path, "rb") as f:
            magic = f.read(4)
        # ELF magic number: 0x7f 'E' 'L' 'F'
        assert magic == b"\x7fELF", "Compiled binary must be a valid ELF executable"

    def test_service_file_exists(self):
        config = _read_config()
        service_path = os.path.join(BUILD_DIR, f"{config['service_name']}.service")
        assert os.path.isfile(service_path), f"Service file {service_path} does not exist"

    def test_install_script_exists(self):
        install_path = os.path.join(BUILD_DIR, "install.sh")
        assert os.path.isfile(install_path), f"{install_path} does not exist"


# ============================================================================
# 3. Systemd service file content validation
# ============================================================================

class TestServiceFileContent:
    def _get_service_content(self):
        config = _read_config()
        service_path = os.path.join(BUILD_DIR, f"{config['service_name']}.service")
        return _read_file(service_path), config

    def test_has_unit_section(self):
        content, _ = self._get_service_content()
        assert "[Unit]" in content, "Service file must contain [Unit] section"

    def test_has_service_section(self):
        content, _ = self._get_service_content()
        assert "[Service]" in content, "Service file must contain [Service] section"

    def test_has_install_section(self):
        content, _ = self._get_service_content()
        assert "[Install]" in content, "Service file must contain [Install] section"

    def test_description_directive(self):
        content, config = self._get_service_content()
        expected = f"Description={config['description']}"
        assert expected in content, f"Service file must contain '{expected}'"

    def test_after_directive(self):
        content, config = self._get_service_content()
        after_val = config.get("after", "network.target")
        expected = f"After={after_val}"
        assert expected in content, f"Service file must contain '{expected}'"

    def test_type_simple(self):
        content, _ = self._get_service_content()
        assert "Type=simple" in content, "Service file must contain 'Type=simple'"

    def test_execstart_directive(self):
        content, config = self._get_service_content()
        expected = f"ExecStart=/usr/local/bin/{config['service_name']}"
        assert expected in content, f"Service file must contain '{expected}'"

    def test_restart_directive(self):
        content, config = self._get_service_content()
        restart_val = config.get("restart_policy", "always")
        expected = f"Restart={restart_val}"
        assert expected in content, f"Service file must contain '{expected}'"

    def test_user_directive(self):
        content, config = self._get_service_content()
        user_val = config.get("user", "root")
        expected = f"User={user_val}"
        assert expected in content, f"Service file must contain '{expected}'"

    def test_wantedby_directive(self):
        content, _ = self._get_service_content()
        assert "WantedBy=multi-user.target" in content, \
            "Service file must contain 'WantedBy=multi-user.target'"

    def test_trailing_newline(self):
        content, _ = self._get_service_content()
        assert content.endswith("\n"), "Service file must end with a trailing newline"

    def test_section_order(self):
        """[Unit] must come before [Service], which must come before [Install]."""
        content, _ = self._get_service_content()
        unit_pos = content.index("[Unit]")
        service_pos = content.index("[Service]")
        install_pos = content.index("[Install]")
        assert unit_pos < service_pos < install_pos, \
            "Sections must be ordered: [Unit], [Service], [Install]"

    def test_exact_structure(self):
        """Verify the full service file matches the expected template."""
        content, config = self._get_service_content()
        sn = config["service_name"]
        desc = config["description"]
        after = config.get("after", "network.target")
        restart = config.get("restart_policy", "always")
        user = config.get("user", "root")

        expected = (
            f"[Unit]\n"
            f"Description={desc}\n"
            f"After={after}\n"
            f"\n"
            f"[Service]\n"
            f"Type=simple\n"
            f"ExecStart=/usr/local/bin/{sn}\n"
            f"Restart={restart}\n"
            f"User={user}\n"
            f"\n"
            f"[Install]\n"
            f"WantedBy=multi-user.target\n"
        )
        assert content == expected, (
            f"Service file content does not match expected template.\n"
            f"--- Expected ---\n{expected}\n"
            f"--- Got ---\n{content}"
        )


# ============================================================================
# 4. Installation script content validation
# ============================================================================

class TestInstallScript:
    def _get_install_content(self):
        config = _read_config()
        install_path = os.path.join(BUILD_DIR, "install.sh")
        return _read_file(install_path), config

    def test_shebang_line(self):
        content, _ = self._get_install_content()
        first_line = content.strip().splitlines()[0]
        assert first_line.strip() == "#!/bin/bash", \
            f"install.sh must start with '#!/bin/bash', got '{first_line}'"

    def test_is_executable(self):
        install_path = os.path.join(BUILD_DIR, "install.sh")
        assert os.path.isfile(install_path), f"{install_path} not found"
        file_stat = os.stat(install_path)
        assert file_stat.st_mode & stat.S_IXUSR, "install.sh must be executable"

    def test_copies_binary(self):
        content, config = self._get_install_content()
        sn = config["service_name"]
        # Must copy binary to /usr/local/bin/<service_name>
        assert f"/usr/local/bin/{sn}" in content, \
            f"install.sh must copy binary to /usr/local/bin/{sn}"
        # Check there's a cp command for the binary
        lines = content.splitlines()
        found = any("cp" in line and f"/usr/local/bin/{sn}" in line for line in lines)
        assert found, "install.sh must have a cp command for the binary"

    def test_copies_service_file(self):
        content, config = self._get_install_content()
        sn = config["service_name"]
        expected_dest = f"/etc/systemd/system/{sn}.service"
        assert expected_dest in content, \
            f"install.sh must copy service file to {expected_dest}"

    def test_daemon_reload(self):
        content, _ = self._get_install_content()
        assert "systemctl daemon-reload" in content, \
            "install.sh must run 'systemctl daemon-reload'"

    def test_enable_service(self):
        content, config = self._get_install_content()
        sn = config["service_name"]
        assert f"systemctl enable {sn}" in content, \
            f"install.sh must run 'systemctl enable {sn}'"

    def test_start_service(self):
        content, config = self._get_install_content()
        sn = config["service_name"]
        assert f"systemctl start {sn}" in content, \
            f"install.sh must run 'systemctl start {sn}'"

    def test_command_order(self):
        """daemon-reload must come before enable, which must come before start."""
        content, config = self._get_install_content()
        sn = config["service_name"]
        reload_pos = content.index("systemctl daemon-reload")
        enable_pos = content.index(f"systemctl enable {sn}")
        start_pos = content.index(f"systemctl start {sn}")
        assert reload_pos < enable_pos < start_pos, \
            "Commands must be ordered: daemon-reload, enable, start"


# ============================================================================
# 5. build.sh exit code on success
# ============================================================================

class TestBuildExitCode:
    def test_build_exits_zero_on_success(self):
        """Running build.sh with valid config should exit 0."""
        result = subprocess.run(
            ["bash", BUILD_SCRIPT],
            cwd=APP_DIR,
            capture_output=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"build.sh should exit 0 on success, got {result.returncode}.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )


# ============================================================================
# 6. Error handling tests
# ============================================================================

class TestErrorHandling:
    def _run_build_with_config(self, config_path):
        """Helper: copy a test config to /app/service_config.json, run build.sh, restore original."""
        original_config = CONFIG_FILE
        backup_path = CONFIG_FILE + ".bak"
        # Backup original config
        shutil.copy2(original_config, backup_path)
        try:
            shutil.copy2(config_path, original_config)
            result = subprocess.run(
                ["bash", BUILD_SCRIPT],
                cwd=APP_DIR,
                capture_output=True,
                timeout=60,
            )
            return result
        finally:
            # Restore original config
            shutil.move(backup_path, original_config)

    def test_missing_source_file_nonzero_exit(self):
        """build.sh must exit non-zero when source_file points to a nonexistent file."""
        bad_source_config = os.path.join(TEST_DATA_DIR, "bad_source_config.json")
        if not os.path.isfile(bad_source_config):
            # If test data not available, create a temporary config
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump({
                "service_name": "ghost",
                "description": "Missing source test",
                "source_file": "src/nonexistent.c"
            }, tmp)
            tmp.close()
            bad_source_config = tmp.name

        result = self._run_build_with_config(bad_source_config)
        assert result.returncode != 0, (
            "build.sh must exit non-zero when source file does not exist"
        )

    def test_missing_source_file_stderr(self):
        """build.sh must print an error to stderr when source file is missing."""
        bad_source_config = os.path.join(TEST_DATA_DIR, "bad_source_config.json")
        if not os.path.isfile(bad_source_config):
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump({
                "service_name": "ghost",
                "description": "Missing source test",
                "source_file": "src/nonexistent.c"
            }, tmp)
            tmp.close()
            bad_source_config = tmp.name

        result = self._run_build_with_config(bad_source_config)
        stderr_output = result.stderr.decode(errors="replace").strip()
        assert len(stderr_output) > 0, \
            "build.sh must print an error message to stderr for missing source file"

    def test_missing_config_nonzero_exit(self):
        """build.sh must exit non-zero when service_config.json does not exist."""
        backup_path = CONFIG_FILE + ".bak2"
        shutil.copy2(CONFIG_FILE, backup_path)
        try:
            os.remove(CONFIG_FILE)
            result = subprocess.run(
                ["bash", BUILD_SCRIPT],
                cwd=APP_DIR,
                capture_output=True,
                timeout=60,
            )
            assert result.returncode != 0, \
                "build.sh must exit non-zero when config file is missing"
            stderr_output = result.stderr.decode(errors="replace").strip()
            assert len(stderr_output) > 0, \
                "build.sh must print an error to stderr when config is missing"
        finally:
            shutil.move(backup_path, CONFIG_FILE)

    def test_compilation_failure_nonzero_exit(self):
        """build.sh must exit non-zero when gcc compilation fails."""
        bad_compile_config = os.path.join(TEST_DATA_DIR, "bad_compile_config.json")
        # Ensure the bad source file exists where the config expects it
        bad_source_src = os.path.join(TEST_DATA_DIR, "bad_source.c")
        bad_source_dest = os.path.join(APP_DIR, "src", "bad_source.c")
        copied_bad_source = False
        if os.path.isfile(bad_source_src) and not os.path.isfile(bad_source_dest):
            shutil.copy2(bad_source_src, bad_source_dest)
            copied_bad_source = True

        try:
            if os.path.isfile(bad_compile_config):
                result = self._run_build_with_config(bad_compile_config)
                assert result.returncode != 0, \
                    "build.sh must exit non-zero when compilation fails"
        finally:
            if copied_bad_source and os.path.isfile(bad_source_dest):
                os.remove(bad_source_dest)


# ============================================================================
# 7. Default values test (minimal config)
# ============================================================================

class TestDefaultValues:
    """Test that optional fields get correct defaults when using minimal config."""

    def _build_with_minimal_config(self):
        """Run build.sh with minimal_config.json and return generated outputs."""
        minimal_config = os.path.join(TEST_DATA_DIR, "minimal_config.json")
        if not os.path.isfile(minimal_config):
            return None, None

        backup_path = CONFIG_FILE + ".bak_defaults"
        shutil.copy2(CONFIG_FILE, backup_path)
        # Clean build dir to avoid stale outputs
        if os.path.isdir(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
        try:
            shutil.copy2(minimal_config, CONFIG_FILE)
            result = subprocess.run(
                ["bash", BUILD_SCRIPT],
                cwd=APP_DIR,
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                return None, None

            config = _read_config(minimal_config)
            sn = config["service_name"]
            service_path = os.path.join(BUILD_DIR, f"{sn}.service")
            install_path = os.path.join(BUILD_DIR, "install.sh")

            service_content = _read_file(service_path) if os.path.isfile(service_path) else None
            install_content = _read_file(install_path) if os.path.isfile(install_path) else None
            return service_content, install_content
        finally:
            shutil.move(backup_path, CONFIG_FILE)
            # Rebuild with original config to restore state for other tests
            if os.path.isdir(BUILD_DIR):
                shutil.rmtree(BUILD_DIR)
            subprocess.run(["bash", BUILD_SCRIPT], cwd=APP_DIR,
                           capture_output=True, timeout=60)

    def test_default_user_is_root(self):
        """When 'user' is omitted, default should be 'root'."""
        service_content, _ = self._build_with_minimal_config()
        if service_content is None:
            return  # Skip if minimal config not available
        assert "User=root" in service_content, \
            "Default user must be 'root' when not specified in config"

    def test_default_restart_policy_is_always(self):
        """When 'restart_policy' is omitted, default should be 'always'."""
        service_content, _ = self._build_with_minimal_config()
        if service_content is None:
            return
        assert "Restart=always" in service_content, \
            "Default restart_policy must be 'always' when not specified"

    def test_default_after_is_network_target(self):
        """When 'after' is omitted, default should be 'network.target'."""
        service_content, _ = self._build_with_minimal_config()
        if service_content is None:
            return
        assert "After=network.target" in service_content, \
            "Default after must be 'network.target' when not specified"

    def test_minimal_config_produces_valid_service_name(self):
        """Minimal config service_name should appear in generated outputs."""
        service_content, install_content = self._build_with_minimal_config()
        if service_content is None:
            return
        minimal_config = os.path.join(TEST_DATA_DIR, "minimal_config.json")
        config = _read_config(minimal_config)
        sn = config["service_name"]
        assert f"ExecStart=/usr/local/bin/{sn}" in service_content, \
            f"Service file must reference /usr/local/bin/{sn}"
        if install_content:
            assert f"systemctl enable {sn}" in install_content, \
                f"install.sh must enable {sn}"


# ============================================================================
# 8. Anti-cheat: content must not be empty or trivially faked
# ============================================================================

class TestAntiCheat:
    def test_service_file_not_empty(self):
        config = _read_config()
        service_path = os.path.join(BUILD_DIR, f"{config['service_name']}.service")
        assert os.path.isfile(service_path), "Service file missing"
        content = _read_file(service_path).strip()
        assert len(content) > 50, "Service file appears to be empty or trivially small"

    def test_install_script_not_empty(self):
        install_path = os.path.join(BUILD_DIR, "install.sh")
        assert os.path.isfile(install_path), "install.sh missing"
        content = _read_file(install_path).strip()
        assert len(content) > 30, "install.sh appears to be empty or trivially small"

    def test_binary_not_empty(self):
        config = _read_config()
        binary_path = os.path.join(BUILD_DIR, config["service_name"])
        assert os.path.isfile(binary_path), "Binary missing"
        size = os.path.getsize(binary_path)
        assert size > 1000, f"Binary is suspiciously small ({size} bytes), likely not a real compiled binary"

    def test_install_has_minimum_commands(self):
        """install.sh must have at least 5 meaningful lines (shebang + 2 cp + 3 systemctl)."""
        install_path = os.path.join(BUILD_DIR, "install.sh")
        content = _read_file(install_path)
        meaningful_lines = [
            line.strip() for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert len(meaningful_lines) >= 5, \
            f"install.sh has only {len(meaningful_lines)} non-empty non-comment lines, expected at least 5"
