import os
import subprocess
import re

# Base paths
OPENSSL_PREFIX = "/opt/openssl-3.x"
OPENSSL_BIN = f"{OPENSSL_PREFIX}/bin/openssl"
VALIDATE_GOST_BIN = f"{OPENSSL_PREFIX}/bin/validate_gost"
OPENSSL_GOST_WRAPPER = f"{OPENSSL_PREFIX}/bin/openssl-gost"
README_PATH = f"{OPENSSL_PREFIX}/README.md"
VALIDATION_OUTPUT = "/app/validation_output.txt"

def test_openssl_binary_exists():
    """Test that custom OpenSSL binary exists and is executable."""
    assert os.path.isfile(OPENSSL_BIN), f"OpenSSL binary not found at {OPENSSL_BIN}"
    assert os.access(OPENSSL_BIN, os.X_OK), f"OpenSSL binary at {OPENSSL_BIN} is not executable"

def test_openssl_version():
    """Test that OpenSSL binary returns version 3.x and is functional."""
    result = subprocess.run(
        [OPENSSL_BIN, "version"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, f"OpenSSL version command failed with code {result.returncode}"

    version_output = result.stdout.strip()
    assert len(version_output) > 0, "OpenSSL version output is empty"

    # Check for OpenSSL 3.x version string
    assert re.search(r'OpenSSL\s+3\.\d+\.\d+', version_output), \
        f"Expected OpenSSL 3.x version, got: {version_output}"

def test_gost_engine_library_exists():
    """Test that GOST engine shared library exists in correct location."""
    # Check both possible locations (lib64 or lib)
    lib64_path = f"{OPENSSL_PREFIX}/lib64/engines-3/gost.so"
    lib_path = f"{OPENSSL_PREFIX}/lib/engines-3/gost.so"

    exists_lib64 = os.path.isfile(lib64_path)
    exists_lib = os.path.isfile(lib_path)

    assert exists_lib64 or exists_lib, \
        f"GOST engine not found at {lib64_path} or {lib_path}"

    # Verify it's a valid shared library (non-empty)
    engine_path = lib64_path if exists_lib64 else lib_path
    file_size = os.path.getsize(engine_path)
    assert file_size > 1024, f"GOST engine file is suspiciously small: {file_size} bytes"

def test_validate_gost_binary_exists():
    """Test that validate_gost binary exists and is executable."""
    assert os.path.isfile(VALIDATE_GOST_BIN), \
        f"validate_gost binary not found at {VALIDATE_GOST_BIN}"
    assert os.access(VALIDATE_GOST_BIN, os.X_OK), \
        f"validate_gost binary at {VALIDATE_GOST_BIN} is not executable"

def test_validate_gost_execution():
    """Test that validate_gost executes successfully with proper environment."""
    # Determine library directory
    if os.path.isfile(f"{OPENSSL_PREFIX}/lib64/engines-3/gost.so"):
        lib_dir = f"{OPENSSL_PREFIX}/lib64"
        engine_dir = f"{OPENSSL_PREFIX}/lib64/engines-3"
    else:
        lib_dir = f"{OPENSSL_PREFIX}/lib"
        engine_dir = f"{OPENSSL_PREFIX}/lib/engines-3"

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{lib_dir}:{env.get('LD_LIBRARY_PATH', '')}"
    env["OPENSSL_CONF"] = f"{OPENSSL_PREFIX}/ssl/openssl.cnf"
    env["OPENSSL_ENGINES"] = engine_dir

    result = subprocess.run(
        [VALIDATE_GOST_BIN],
        capture_output=True,
        text=True,
        env=env,
        timeout=30
    )

    assert result.returncode == 0, \
        f"validate_gost failed with exit code {result.returncode}\nStderr: {result.stderr}"

    output = result.stdout + result.stderr
    assert len(output) > 0, "validate_gost produced no output"

    # Check for key success indicators
    assert "GOST engine loaded successfully" in output or "gost" in output.lower(), \
        f"Output doesn't confirm GOST engine loaded: {output}"

def test_openssl_gost_wrapper_exists():
    """Test that openssl-gost wrapper script exists and is executable."""
    assert os.path.isfile(OPENSSL_GOST_WRAPPER), \
        f"openssl-gost wrapper not found at {OPENSSL_GOST_WRAPPER}"
    assert os.access(OPENSSL_GOST_WRAPPER, os.X_OK), \
        f"openssl-gost wrapper at {OPENSSL_GOST_WRAPPER} is not executable"

def test_openssl_gost_wrapper_content():
    """Test that openssl-gost wrapper has proper environment setup."""
    with open(OPENSSL_GOST_WRAPPER, 'r') as f:
        content = f.read()

    # Check for essential environment variables
    assert "LD_LIBRARY_PATH" in content, "Wrapper missing LD_LIBRARY_PATH setup"
    assert "OPENSSL_CONF" in content, "Wrapper missing OPENSSL_CONF setup"
    assert "/opt/openssl-3.x/bin/openssl" in content, "Wrapper doesn't execute custom OpenSSL"

    # Ensure it's not just a dummy script
    assert len(content) > 50, "Wrapper script is suspiciously short"

def test_validation_output_file_exists():
    """Test that validation_output.txt exists and contains meaningful output."""
    assert os.path.isfile(VALIDATION_OUTPUT), \
        f"Validation output file not found at {VALIDATION_OUTPUT}"

    with open(VALIDATION_OUTPUT, 'r') as f:
        content = f.read()

    assert len(content) > 0, "Validation output file is empty"

    # Check for evidence of successful GOST engine operation
    content_lower = content.lower()
    assert "gost" in content_lower, \
        f"Validation output doesn't mention GOST engine: {content}"

    # Look for success indicators
    success_indicators = [
        "loaded successfully",
        "successful",
        "completed successfully",
        "engine id",
        "digest"
    ]

    has_success = any(indicator in content_lower for indicator in success_indicators)
    assert has_success, \
        f"Validation output doesn't show successful operation: {content}"

def test_readme_exists_and_documents_structure():
    """Test that README.md exists and documents the installation."""
    assert os.path.isfile(README_PATH), f"README.md not found at {README_PATH}"

    with open(README_PATH, 'r') as f:
        content = f.read()

    assert len(content) > 100, "README.md is too short to be meaningful"

    # Check for documentation of key components
    required_paths = [
        "/opt/openssl-3.x/bin/openssl",
        "/opt/openssl-3.x/bin/validate_gost",
        "/opt/openssl-3.x/bin/openssl-gost",
        "gost.so"
    ]

    for path in required_paths:
        assert path in content, f"README.md doesn't document {path}"

def test_openssl_config_exists():
    """Test that OpenSSL configuration file exists and references GOST."""
    config_path = f"{OPENSSL_PREFIX}/ssl/openssl.cnf"
    assert os.path.isfile(config_path), f"OpenSSL config not found at {config_path}"

    with open(config_path, 'r') as f:
        content = f.read()

    assert "gost" in content.lower(), "OpenSSL config doesn't reference GOST engine"
    assert "engine" in content.lower(), "OpenSSL config doesn't configure engines"

def test_system_openssl_unaffected():
    """Test that system OpenSSL is not overwritten."""
    # Check that system OpenSSL still exists and works
    result = subprocess.run(
        ["which", "openssl"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        system_openssl = result.stdout.strip()
        # System OpenSSL should not be our custom one
        assert system_openssl != OPENSSL_BIN, \
            "System OpenSSL was overwritten by custom installation"

def test_openssl_libraries_exist():
    """Test that OpenSSL libraries are installed."""
    # Check both lib64 and lib directories
    lib64_crypto = f"{OPENSSL_PREFIX}/lib64/libcrypto.so"
    lib_crypto = f"{OPENSSL_PREFIX}/lib/libcrypto.so"

    lib64_ssl = f"{OPENSSL_PREFIX}/lib64/libssl.so"
    lib_ssl = f"{OPENSSL_PREFIX}/lib/libssl.so"

    has_crypto = os.path.exists(lib64_crypto) or os.path.exists(lib_crypto)
    has_ssl = os.path.exists(lib64_ssl) or os.path.exists(lib_ssl)

    assert has_crypto, "libcrypto.so not found in lib or lib64"
    assert has_ssl, "libssl.so not found in lib or lib64"

def test_validate_gost_not_dummy():
    """Test that validate_gost is not just a dummy script returning 0."""
    # Read the binary to check it's actually compiled C code
    with open(VALIDATE_GOST_BIN, 'rb') as f:
        header = f.read(4)

    # Check for ELF magic number (compiled binary)
    assert header[:4] == b'\x7fELF', \
        "validate_gost is not a valid ELF binary (might be a dummy script)"

def test_openssl_binary_not_symlink_to_system():
    """Test that custom OpenSSL is not just a symlink to system OpenSSL."""
    if os.path.islink(OPENSSL_BIN):
        target = os.readlink(OPENSSL_BIN)
        assert "/opt/openssl-3.x" in os.path.abspath(target), \
            "OpenSSL binary is a symlink to system OpenSSL"

    # Verify it's a real binary
    assert os.path.isfile(OPENSSL_BIN), "OpenSSL binary is not a regular file"
    file_size = os.path.getsize(OPENSSL_BIN)
    assert file_size > 10000, f"OpenSSL binary is suspiciously small: {file_size} bytes"
