"""
Tests for Docker Image Size Optimization and Security Hardening task.

Validates the output /app/Dockerfile against all requirements in instruction.md.
Since we cannot build Docker images inside the test container, all tests perform
static analysis of the Dockerfile content, with careful distinction between
builder stage(s) and the final production stage.
"""

import os
import re
import pytest

DOCKERFILE_PATH = "/app/Dockerfile"


def read_dockerfile():
    """Read the Dockerfile and return its content."""
    if not os.path.exists(DOCKERFILE_PATH):
        pytest.fail(f"Dockerfile not found at {DOCKERFILE_PATH}")
    with open(DOCKERFILE_PATH, "r") as f:
        content = f.read()
    if not content.strip():
        pytest.fail("Dockerfile is empty")
    return content


def get_lines(content):
    """Return non-empty, non-comment lines from Dockerfile content."""
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def get_stages(content):
    """
    Split Dockerfile into stages based on FROM instructions.
    Returns a list of (from_line, stage_lines) tuples.
    Each stage_lines is a list of non-comment, non-empty lines AFTER the FROM.
    """
    stages = []
    current_from = None
    current_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.upper().startswith("FROM "):
            if current_from is not None:
                stages.append((current_from, current_lines))
            current_from = stripped
            current_lines = []
        else:
            current_lines.append(stripped)
    if current_from is not None:
        stages.append((current_from, current_lines))
    return stages


def get_final_stage(content):
    """Return (from_line, stage_lines) for the final stage."""
    stages = get_stages(content)
    assert len(stages) >= 1, "Dockerfile has no FROM instructions"
    return stages[-1]


def join_continued_lines(lines):
    """
    Join lines that end with backslash (line continuation in Dockerfile RUN).
    Returns a list of logically complete lines.
    """
    joined = []
    buf = ""
    for line in lines:
        if line.endswith("\\"):
            buf += line[:-1] + " "
        else:
            buf += line
            joined.append(buf)
            buf = ""
    if buf:
        joined.append(buf)
    return joined


# ============================================================
# Test 1: Dockerfile exists and is non-trivial
# ============================================================
class TestDockerfileExists:
    def test_file_exists(self):
        assert os.path.exists(DOCKERFILE_PATH), f"{DOCKERFILE_PATH} does not exist"

    def test_file_not_empty(self):
        content = read_dockerfile()
        lines = get_lines(content)
        # A valid Dockerfile needs at least a FROM + a few instructions
        assert len(lines) >= 5, (
            f"Dockerfile has only {len(lines)} non-empty/non-comment lines; "
            "expected a meaningful Dockerfile"
        )


# ============================================================
# Test 2: Multi-stage build
# ============================================================
class TestMultiStageBuild:
    def test_multiple_from_instructions(self):
        content = read_dockerfile()
        stages = get_stages(content)
        assert len(stages) >= 2, (
            f"Expected multi-stage build (>=2 FROM instructions), found {len(stages)}"
        )


# ============================================================
# Test 3: Final stage uses Alpine or slim base image
# ============================================================
class TestBaseImage:
    def test_final_stage_alpine_or_slim(self):
        content = read_dockerfile()
        from_line, _ = get_final_stage(content)
        from_lower = from_line.lower()
        assert "alpine" in from_lower or "slim" in from_lower, (
            f"Final stage base image must be Alpine or slim. Got: {from_line}"
        )

    def test_final_stage_not_ubuntu(self):
        content = read_dockerfile()
        from_line, _ = get_final_stage(content)
        assert "ubuntu" not in from_line.lower(), (
            f"Final stage should not use Ubuntu. Got: {from_line}"
        )


# ============================================================
# Test 4: Security — Non-root user
# ============================================================
class TestNonRootUser:
    def test_user_directive_exists(self):
        """The final stage must have a USER directive."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        user_lines = [
            l for l in final_lines if l.upper().startswith("USER ")
        ]
        assert len(user_lines) >= 1, (
            "Final stage must contain a USER directive"
        )

    def test_user_is_not_root(self):
        """The USER directive must not be 'root'."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        user_lines = [
            l for l in final_lines if l.upper().startswith("USER ")
        ]
        assert len(user_lines) >= 1, "No USER directive found in final stage"
        # Check the last USER directive (the effective one)
        last_user = user_lines[-1]
        user_value = last_user.split(None, 1)[1].strip().lower()
        assert user_value != "root", (
            f"USER must not be root. Got: {last_user}"
        )
        assert user_value != "0", (
            f"USER must not be UID 0 (root). Got: {last_user}"
        )


# ============================================================
# Test 5: Security — No secrets in ENV
# ============================================================
class TestNoSecrets:
    def test_no_secret_env_variables(self):
        """ENV variables must not contain secrets or passwords."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        joined = join_continued_lines(final_lines)
        secret_keywords = [
            "password", "secret", "api_key", "apikey",
            "token", "credential", "private_key",
        ]
        for line in joined:
            if line.upper().startswith("ENV "):
                line_lower = line.lower()
                for kw in secret_keywords:
                    assert kw not in line_lower, (
                        f"ENV line appears to contain a secret ({kw}): {line}"
                    )

    def test_no_bloated_secrets_carried_over(self):
        """Specifically check the secrets from Dockerfile.bloated are gone."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        joined_text = " ".join(final_lines).lower()
        assert "supersecret" not in joined_text, (
            "Secret 'supersecret123' from bloated Dockerfile found in final stage"
        )
        assert "sk-fake-key" not in joined_text, (
            "Secret 'sk-fake-key' from bloated Dockerfile found in final stage"
        )


# ============================================================
# Test 6: No openssh-server in final stage
# ============================================================
class TestNoSSH:
    def test_no_openssh_in_final_stage(self):
        """openssh-server must not be installed in the final stage."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        joined = join_continued_lines(final_lines)
        for line in joined:
            if line.upper().startswith("RUN "):
                assert "openssh" not in line.lower(), (
                    f"openssh-server must not be installed in final stage: {line}"
                )


# ============================================================
# Test 7: No build tools or debug utilities in final stage
# ============================================================
class TestNoBloatPackages:
    FORBIDDEN_TOOLS = [
        "gcc", "g++", "make", "cmake",
        "vim", "nano",
        "nmap", "tcpdump", "strace",
        "telnet", "net-tools",
        "htop", "sysstat",
    ]

    def test_no_build_tools_in_final_stage(self):
        """Build tools and debug utilities must not be in the final stage."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        joined = join_continued_lines(final_lines)
        for line in joined:
            if not line.upper().startswith("RUN "):
                continue
            # Only check apt-get/apk install lines for forbidden packages
            line_lower = line.lower()
            if "install" not in line_lower:
                continue
            for tool in self.FORBIDDEN_TOOLS:
                # Use word boundary matching to avoid false positives
                # e.g., "make" shouldn't match "Makefile" in a different context
                pattern = r'\b' + re.escape(tool) + r'\b'
                assert not re.search(pattern, line_lower), (
                    f"Forbidden tool '{tool}' found in final stage install: {line}"
                )

    def test_no_extra_pip_packages_in_final_stage(self):
        """
        Final stage should not install extra pip packages beyond requirements.txt.
        The bloated Dockerfile installed numpy, pandas, scipy, scikit-learn, etc.
        """
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        joined = join_continued_lines(final_lines)
        bloat_packages = ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "pillow"]
        for line in joined:
            if not line.upper().startswith("RUN "):
                continue
            line_lower = line.lower()
            if "pip" not in line_lower:
                continue
            for pkg in bloat_packages:
                assert pkg not in line_lower, (
                    f"Extra pip package '{pkg}' found in final stage: {line}"
                )


# ============================================================
# Test 8: Gunicorn as production server
# ============================================================
class TestGunicorn:
    def test_cmd_or_entrypoint_uses_gunicorn(self):
        """CMD or ENTRYPOINT must use gunicorn, not Flask dev server."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        cmd_lines = [
            l for l in final_lines
            if l.upper().startswith("CMD ") or l.upper().startswith("ENTRYPOINT ")
        ]
        assert len(cmd_lines) >= 1, (
            "Final stage must have a CMD or ENTRYPOINT instruction"
        )
        # Check the last CMD/ENTRYPOINT (the effective one)
        last_cmd = cmd_lines[-1].lower()
        assert "gunicorn" in last_cmd, (
            f"CMD/ENTRYPOINT must use gunicorn. Got: {cmd_lines[-1]}"
        )

    def test_not_flask_dev_server(self):
        """CMD must not use 'python3 app.py' (Flask dev server)."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        cmd_lines = [
            l for l in final_lines
            if l.upper().startswith("CMD ") or l.upper().startswith("ENTRYPOINT ")
        ]
        for cmd in cmd_lines:
            cmd_lower = cmd.lower()
            # Reject patterns like: python app.py, python3 app.py, flask run
            assert not re.search(r'python[3]?\s+app\.py', cmd_lower), (
                f"Must not use Flask dev server (python app.py). Got: {cmd}"
            )
            # Also check for "flask run" pattern
            assert "flask run" not in cmd_lower, (
                f"Must not use 'flask run' dev server. Got: {cmd}"
            )

    def test_gunicorn_binds_port_5000(self):
        """Gunicorn should bind to port 5000."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        cmd_lines = [
            l for l in final_lines
            if l.upper().startswith("CMD ") or l.upper().startswith("ENTRYPOINT ")
        ]
        assert len(cmd_lines) >= 1, "No CMD/ENTRYPOINT found"
        last_cmd = cmd_lines[-1].lower()
        if "gunicorn" in last_cmd:
            assert "5000" in last_cmd, (
                f"Gunicorn should bind to port 5000. Got: {cmd_lines[-1]}"
            )


# ============================================================
# Test 9: EXPOSE 5000
# ============================================================
class TestExpose:
    def test_expose_5000(self):
        """Dockerfile must expose port 5000."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        expose_lines = [
            l for l in final_lines if l.upper().startswith("EXPOSE ")
        ]
        assert len(expose_lines) >= 1, "Final stage must have an EXPOSE instruction"
        found_5000 = any("5000" in l for l in expose_lines)
        assert found_5000, (
            f"Must EXPOSE 5000. Found: {expose_lines}"
        )


# ============================================================
# Test 10: WORKDIR /app
# ============================================================
class TestWorkdir:
    def test_workdir_app(self):
        """Final stage must set WORKDIR /app."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        workdir_lines = [
            l for l in final_lines if l.upper().startswith("WORKDIR ")
        ]
        assert len(workdir_lines) >= 1, (
            "Final stage must have a WORKDIR instruction"
        )
        # Check the last WORKDIR (the effective one)
        last_workdir = workdir_lines[-1]
        workdir_value = last_workdir.split(None, 1)[1].strip()
        assert workdir_value == "/app", (
            f"WORKDIR must be /app. Got: {workdir_value}"
        )


# ============================================================
# Test 11: Only application files copied
# ============================================================
class TestCopyFiles:
    def test_app_py_copied(self):
        """app.py must be copied into the final image."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        copy_lines = [
            l for l in final_lines
            if l.upper().startswith("COPY ") or l.upper().startswith("ADD ")
        ]
        # Filter out COPY --from= lines (those copy from builder, which is fine)
        # We want to check that app.py is present somewhere in COPY instructions
        all_copy_text = " ".join(copy_lines).lower()
        assert "app.py" in all_copy_text, (
            "app.py must be COPYed into the final image"
        )

    def test_requirements_txt_copied(self):
        """requirements.txt must be copied into the final image."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        copy_lines = [
            l for l in final_lines
            if l.upper().startswith("COPY ") or l.upper().startswith("ADD ")
        ]
        all_copy_text = " ".join(copy_lines).lower()
        assert "requirements.txt" in all_copy_text, (
            "requirements.txt must be COPYed into the final image"
        )


# ============================================================
# Test 12: Gunicorn references the Flask app correctly
# ============================================================
class TestGunicornAppReference:
    def test_gunicorn_references_app_module(self):
        """
        Gunicorn CMD should reference the Flask app module.
        Common patterns: 'app:app', 'app:create_app()', 'wsgi:app'
        """
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        cmd_lines = [
            l for l in final_lines
            if l.upper().startswith("CMD ") or l.upper().startswith("ENTRYPOINT ")
        ]
        assert len(cmd_lines) >= 1, "No CMD/ENTRYPOINT found"
        last_cmd = cmd_lines[-1].lower()
        if "gunicorn" in last_cmd:
            # Must reference the app module — typically "app:app"
            assert "app" in last_cmd.split("gunicorn", 1)[1], (
                f"Gunicorn must reference the Flask app module (e.g., app:app). "
                f"Got: {cmd_lines[-1]}"
            )


# ============================================================
# Test 13: Dockerfile is valid syntax (basic checks)
# ============================================================
class TestDockerfileSyntax:
    def test_starts_with_from(self):
        """First non-comment instruction must be FROM."""
        content = read_dockerfile()
        lines = get_lines(content)
        assert lines[0].upper().startswith("FROM "), (
            f"Dockerfile must start with FROM. Got: {lines[0]}"
        )

    def test_no_duplicate_cmd(self):
        """Final stage should have at most one CMD instruction."""
        content = read_dockerfile()
        _, final_lines = get_final_stage(content)
        cmd_count = sum(
            1 for l in final_lines if l.upper().startswith("CMD ")
        )
        assert cmd_count <= 1, (
            f"Final stage has {cmd_count} CMD instructions; only the last one takes effect"
        )

    def test_is_not_bloated_dockerfile(self):
        """
        The output must not be a copy of the bloated Dockerfile.
        Check that it doesn't contain the telltale signs of the original.
        """
        content = read_dockerfile()
        content_lower = content.lower()
        # The bloated Dockerfile uses ubuntu:22.04 as the only FROM
        stages = get_stages(content)
        if len(stages) == 1:
            from_line = stages[0][0].lower()
            assert "ubuntu" not in from_line, (
                "Output appears to be the original bloated Dockerfile (single Ubuntu stage)"
            )
        # Check for the bloated secret ENV
        assert "secret_db_password" not in content_lower, (
            "Output contains SECRET_DB_PASSWORD from the bloated Dockerfile"
        )

