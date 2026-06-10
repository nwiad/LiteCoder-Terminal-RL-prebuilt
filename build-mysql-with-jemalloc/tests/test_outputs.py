import os
import subprocess
import tarfile
import re


def test_mysqld_binary_exists():
    """Verify the MySQL server binary exists at the expected location."""
    mysqld_path = "/app/mysql/bin/mysqld"
    assert os.path.exists(mysqld_path), f"MySQL binary not found at {mysqld_path}"
    assert os.path.isfile(mysqld_path), f"{mysqld_path} is not a file"


def test_mysqld_binary_is_executable():
    """Verify the mysqld binary has executable permissions."""
    mysqld_path = "/app/mysql/bin/mysqld"
    assert os.path.exists(mysqld_path), f"MySQL binary not found at {mysqld_path}"
    assert os.access(mysqld_path, os.X_OK), f"{mysqld_path} is not executable"


def test_mysqld_binary_is_not_empty():
    """Verify the mysqld binary is not an empty file (lazy agent check)."""
    mysqld_path = "/app/mysql/bin/mysqld"
    assert os.path.exists(mysqld_path), f"MySQL binary not found at {mysqld_path}"
    file_size = os.path.getsize(mysqld_path)
    # MySQL binary should be at least several MB (typically 500+ MB)
    assert file_size > 10_000_000, f"mysqld binary suspiciously small: {file_size} bytes"


def test_build_verification_file_exists():
    """Verify the build verification file exists."""
    verification_path = "/app/build_verification.txt"
    assert os.path.exists(verification_path), f"Verification file not found at {verification_path}"
    assert os.path.isfile(verification_path), f"{verification_path} is not a file"


def test_build_verification_contains_jemalloc():
    """Verify the verification file contains evidence of jemalloc linkage."""
    verification_path = "/app/build_verification.txt"
    assert os.path.exists(verification_path), f"Verification file not found at {verification_path}"

    with open(verification_path, 'r') as f:
        content = f.read()

    # Check file is not empty (lazy agent check)
    assert len(content.strip()) > 0, "Verification file is empty"

    # Check for jemalloc in the content
    assert "jemalloc" in content.lower(), "No jemalloc reference found in verification file"


def test_mysqld_actually_linked_to_jemalloc():
    """Verify mysqld is actually linked to jemalloc using ldd command."""
    mysqld_path = "/app/mysql/bin/mysqld"
    assert os.path.exists(mysqld_path), f"MySQL binary not found at {mysqld_path}"

    try:
        result = subprocess.run(
            ["ldd", mysqld_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        # ldd should succeed
        assert result.returncode == 0, f"ldd command failed with return code {result.returncode}"

        ldd_output = result.stdout.lower()

        # Check for jemalloc in the actual ldd output
        assert "jemalloc" in ldd_output, "mysqld is not linked against jemalloc (ldd shows no jemalloc dependency)"

        # Verify it's a proper ldd output format (contains "=>" which indicates library mapping)
        assert "=>" in result.stdout, "ldd output format is invalid (missing '=>' library mappings)"

    except subprocess.TimeoutExpired:
        assert False, "ldd command timed out"
    except FileNotFoundError:
        assert False, "ldd command not found (should be available in standard Linux)"


def test_deployment_tarball_exists():
    """Verify the deployment tarball exists."""
    tarball_path = "/app/mysql-8.4.2-jemalloc.tar.gz"
    assert os.path.exists(tarball_path), f"Deployment tarball not found at {tarball_path}"
    assert os.path.isfile(tarball_path), f"{tarball_path} is not a file"


def test_deployment_tarball_is_not_empty():
    """Verify the tarball is not empty (lazy agent check)."""
    tarball_path = "/app/mysql-8.4.2-jemalloc.tar.gz"
    assert os.path.exists(tarball_path), f"Deployment tarball not found at {tarball_path}"

    file_size = os.path.getsize(tarball_path)
    # MySQL installation tarball should be at least 100 MB
    assert file_size > 100_000_000, f"Tarball suspiciously small: {file_size} bytes (expected > 100 MB)"


def test_deployment_tarball_is_valid():
    """Verify the tarball is a valid gzipped tar archive."""
    tarball_path = "/app/mysql-8.4.2-jemalloc.tar.gz"
    assert os.path.exists(tarball_path), f"Deployment tarball not found at {tarball_path}"

    try:
        with tarfile.open(tarball_path, 'r:gz') as tar:
            # Just opening it validates the format
            members = tar.getmembers()
            assert len(members) > 0, "Tarball is empty (no files inside)"
    except tarfile.TarError as e:
        assert False, f"Tarball is not a valid tar.gz file: {e}"
    except Exception as e:
        assert False, f"Failed to open tarball: {e}"


def test_deployment_tarball_contains_mysqld():
    """Verify the tarball contains the mysqld binary."""
    tarball_path = "/app/mysql-8.4.2-jemalloc.tar.gz"
    assert os.path.exists(tarball_path), f"Deployment tarball not found at {tarball_path}"

    try:
        with tarfile.open(tarball_path, 'r:gz') as tar:
            member_names = [m.name for m in tar.getmembers()]

            # Look for mysqld binary in the tarball
            mysqld_found = any('bin/mysqld' in name for name in member_names)
            assert mysqld_found, "mysqld binary not found in deployment tarball"

    except Exception as e:
        assert False, f"Failed to inspect tarball contents: {e}"


def test_deployment_tarball_contains_mysql_directory():
    """Verify the tarball contains the mysql directory structure."""
    tarball_path = "/app/mysql-8.4.2-jemalloc.tar.gz"
    assert os.path.exists(tarball_path), f"Deployment tarball not found at {tarball_path}"

    try:
        with tarfile.open(tarball_path, 'r:gz') as tar:
            member_names = [m.name for m in tar.getmembers()]

            # Check for key MySQL directories
            has_bin = any('mysql/bin' in name or name.startswith('mysql/bin/') for name in member_names)
            has_lib = any('mysql/lib' in name or name.startswith('mysql/lib/') for name in member_names)

            assert has_bin, "mysql/bin directory not found in tarball"
            assert has_lib, "mysql/lib directory not found in tarball"

    except Exception as e:
        assert False, f"Failed to inspect tarball structure: {e}"


def test_mysql_installation_directory_exists():
    """Verify the MySQL installation directory exists."""
    mysql_dir = "/app/mysql"
    assert os.path.exists(mysql_dir), f"MySQL installation directory not found at {mysql_dir}"
    assert os.path.isdir(mysql_dir), f"{mysql_dir} is not a directory"


def test_mysql_bin_directory_has_multiple_binaries():
    """Verify the MySQL bin directory contains multiple binaries (not just mysqld)."""
    bin_dir = "/app/mysql/bin"
    assert os.path.exists(bin_dir), f"MySQL bin directory not found at {bin_dir}"
    assert os.path.isdir(bin_dir), f"{bin_dir} is not a directory"

    binaries = [f for f in os.listdir(bin_dir) if os.path.isfile(os.path.join(bin_dir, f))]

    # MySQL installation should have multiple binaries (mysqld, mysql, mysqladmin, etc.)
    assert len(binaries) > 5, f"Too few binaries in {bin_dir}: {len(binaries)} (expected > 5)"


def test_verification_file_matches_actual_ldd_output():
    """Verify the verification file content matches actual ldd output (anti-hardcoding check)."""
    verification_path = "/app/build_verification.txt"
    mysqld_path = "/app/mysql/bin/mysqld"

    assert os.path.exists(verification_path), f"Verification file not found at {verification_path}"
    assert os.path.exists(mysqld_path), f"MySQL binary not found at {mysqld_path}"

    # Read the verification file
    with open(verification_path, 'r') as f:
        verification_content = f.read()

    # Run ldd ourselves
    result = subprocess.run(
        ["ldd", mysqld_path],
        capture_output=True,
        text=True,
        timeout=30
    )

    actual_ldd_output = result.stdout

    # The verification file should contain actual ldd output, not hardcoded fake data
    # Check that key libraries present in actual ldd are also in verification file
    actual_libs = re.findall(r'(\S+\.so[.\d]*)', actual_ldd_output)

    # At least some of the libraries from actual ldd should be in verification file
    matching_libs = [lib for lib in actual_libs if lib in verification_content]

    assert len(matching_libs) > 5, \
        f"Verification file doesn't match actual ldd output (only {len(matching_libs)} libraries match)"
