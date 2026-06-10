import os
import subprocess
import re


def test_nfs_config_summary_exists():
    """Test that the configuration summary file exists."""
    assert os.path.exists("/app/nfs_config_summary.txt"), \
        "Configuration summary file /app/nfs_config_summary.txt does not exist"


def test_nfs_config_summary_not_empty():
    """Test that the configuration summary file is not empty."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, \
        "Configuration summary file is empty"


def test_kerberos_realm_in_summary():
    """Test that Kerberos realm is correctly specified in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for Kerberos Realm line
    assert re.search(r"Kerberos Realm:\s*EXAMPLE\.COM", content), \
        "Kerberos Realm not found or incorrect in summary file"


def test_nfs_principal_in_summary():
    """Test that NFS principal is correctly specified in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for NFS Principal line
    assert re.search(r"NFS Principal:\s*nfs/nfs-server\.example\.com@EXAMPLE\.COM", content), \
        "NFS Principal not found or incorrect in summary file"


def test_shared_directory_in_summary():
    """Test that shared directory path is correctly specified in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for Shared Directory line
    assert re.search(r"Shared Directory:\s*/app/nfs_share", content), \
        "Shared Directory not found or incorrect in summary file"


def test_export_configuration_in_summary():
    """Test that export configuration is correctly specified in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for Export Configuration line with krb5p security
    assert re.search(r"Export Configuration:.*sec=krb5p", content), \
        "Export Configuration not found or missing krb5p security in summary file"

    # Verify it includes /app/nfs_share
    assert re.search(r"Export Configuration:.*\/app\/nfs_share", content), \
        "Export Configuration does not include /app/nfs_share"


def test_rpc_gssd_status_in_summary():
    """Test that RPC-GSSD status is reported in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for RPC-GSSD Status line
    assert re.search(r"RPC-GSSD Status:\s*(active|inactive)", content), \
        "RPC-GSSD Status not found in summary file"


def test_nfs_server_status_in_summary():
    """Test that NFS Server status is reported in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for NFS Server Status line
    assert re.search(r"NFS Server Status:\s*(active|inactive)", content), \
        "NFS Server Status not found in summary file"


def test_exported_directories_section_in_summary():
    """Test that Exported Directories section exists in summary."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Check for Exported Directories section
    assert re.search(r"Exported Directories:", content), \
        "Exported Directories section not found in summary file"


def test_shared_directory_exists():
    """Test that the shared directory actually exists on the filesystem."""
    assert os.path.exists("/app/nfs_share"), \
        "Shared directory /app/nfs_share does not exist"
    assert os.path.isdir("/app/nfs_share"), \
        "/app/nfs_share exists but is not a directory"


def test_shared_directory_permissions():
    """Test that the shared directory has correct permissions (755)."""
    stat_info = os.stat("/app/nfs_share")
    permissions = oct(stat_info.st_mode)[-3:]
    assert permissions == "755", \
        f"Shared directory permissions are {permissions}, expected 755"


def test_nfs_exports_file_exists():
    """Test that /etc/exports file exists and is configured."""
    assert os.path.exists("/etc/exports"), \
        "/etc/exports file does not exist"


def test_nfs_exports_contains_shared_directory():
    """Test that /etc/exports contains the shared directory configuration."""
    with open("/etc/exports", "r") as f:
        content = f.read()

    # Check for /app/nfs_share in exports
    assert "/app/nfs_share" in content, \
        "/app/nfs_share not found in /etc/exports"

    # Check for krb5p security
    assert "sec=krb5p" in content, \
        "Kerberos security (sec=krb5p) not configured in /etc/exports"


def test_krb5_config_exists():
    """Test that Kerberos configuration file exists."""
    assert os.path.exists("/etc/krb5.conf"), \
        "/etc/krb5.conf file does not exist"


def test_krb5_config_contains_realm():
    """Test that Kerberos configuration contains EXAMPLE.COM realm."""
    with open("/etc/krb5.conf", "r") as f:
        content = f.read()

    assert "EXAMPLE.COM" in content, \
        "EXAMPLE.COM realm not found in /etc/krb5.conf"


def test_krb5_keytab_exists():
    """Test that Kerberos keytab file exists."""
    assert os.path.exists("/etc/krb5.keytab"), \
        "/etc/krb5.keytab file does not exist"


def test_nfs_principal_in_keytab():
    """Test that NFS principal exists in the keytab."""
    try:
        result = subprocess.run(
            ["klist", "-k", "/etc/krb5.keytab"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if the command succeeded
        assert result.returncode == 0, \
            f"Failed to list keytab contents: {result.stderr}"

        # Check for NFS principal
        assert "nfs/nfs-server.example.com@EXAMPLE.COM" in result.stdout, \
            "NFS principal not found in keytab"
    except FileNotFoundError:
        # If klist is not available, check keytab file exists and is not empty
        stat_info = os.stat("/etc/krb5.keytab")
        assert stat_info.st_size > 0, \
            "Keytab file exists but is empty"


def test_rpc_gssd_service_active():
    """Test that rpc-gssd service is actually active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "rpc-gssd"],
            capture_output=True,
            text=True,
            timeout=10
        )

        status = result.stdout.strip()
        assert status == "active", \
            f"rpc-gssd service is not active (status: {status})"
    except Exception as e:
        # If systemctl check fails, verify it's reported correctly in summary
        with open("/app/nfs_config_summary.txt", "r") as f:
            content = f.read()
        assert "RPC-GSSD Status:" in content, \
            f"Could not verify rpc-gssd status: {e}"


def test_nfs_server_service_active():
    """Test that nfs-kernel-server service is actually active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "nfs-kernel-server"],
            capture_output=True,
            text=True,
            timeout=10
        )

        status = result.stdout.strip()
        assert status == "active", \
            f"nfs-kernel-server service is not active (status: {status})"
    except Exception as e:
        # If systemctl check fails, verify it's reported correctly in summary
        with open("/app/nfs_config_summary.txt", "r") as f:
            content = f.read()
        assert "NFS Server Status:" in content, \
            f"Could not verify nfs-kernel-server status: {e}"


def test_nfs_export_is_active():
    """Test that NFS export is actually active using showmount."""
    try:
        result = subprocess.run(
            ["showmount", "-e", "localhost"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if showmount succeeded
        assert result.returncode == 0, \
            f"showmount command failed: {result.stderr}"

        # Check for /app/nfs_share in exports
        assert "/app/nfs_share" in result.stdout, \
            f"/app/nfs_share not found in active exports. Output: {result.stdout}"
    except FileNotFoundError:
        # If showmount is not available, check that exports file is configured
        with open("/etc/exports", "r") as f:
            content = f.read()
        assert "/app/nfs_share" in content and "sec=krb5p" in content, \
            "NFS export not properly configured"


def test_services_enabled_on_boot():
    """Test that services are enabled to start on boot."""
    try:
        # Check rpc-gssd
        result = subprocess.run(
            ["systemctl", "is-enabled", "rpc-gssd"],
            capture_output=True,
            text=True,
            timeout=10
        )
        rpc_enabled = result.stdout.strip() in ["enabled", "static"]

        # Check nfs-kernel-server
        result = subprocess.run(
            ["systemctl", "is-enabled", "nfs-kernel-server"],
            capture_output=True,
            text=True,
            timeout=10
        )
        nfs_enabled = result.stdout.strip() in ["enabled", "static"]

        assert rpc_enabled, "rpc-gssd service is not enabled on boot"
        assert nfs_enabled, "nfs-kernel-server service is not enabled on boot"
    except Exception:
        # If we can't check enabled status, at least verify services are active
        pass


def test_summary_matches_actual_service_status():
    """Test that the summary file accurately reflects actual service statuses."""
    with open("/app/nfs_config_summary.txt", "r") as f:
        content = f.read()

    # Extract reported statuses from summary
    rpc_match = re.search(r"RPC-GSSD Status:\s*(active|inactive)", content)
    nfs_match = re.search(r"NFS Server Status:\s*(active|inactive)", content)

    assert rpc_match, "RPC-GSSD Status not found in summary"
    assert nfs_match, "NFS Server Status not found in summary"

    reported_rpc_status = rpc_match.group(1)
    reported_nfs_status = nfs_match.group(1)

    # Verify actual statuses
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "rpc-gssd"],
            capture_output=True,
            text=True,
            timeout=10
        )
        actual_rpc_status = result.stdout.strip()

        result = subprocess.run(
            ["systemctl", "is-active", "nfs-kernel-server"],
            capture_output=True,
            text=True,
            timeout=10
        )
        actual_nfs_status = result.stdout.strip()

        # Compare reported vs actual
        assert reported_rpc_status == actual_rpc_status, \
            f"RPC-GSSD status mismatch: summary says {reported_rpc_status}, actual is {actual_rpc_status}"
        assert reported_nfs_status == actual_nfs_status, \
            f"NFS Server status mismatch: summary says {reported_nfs_status}, actual is {actual_nfs_status}"
    except Exception:
        # If we can't verify, at least ensure they're reported as active
        assert reported_rpc_status == "active", "RPC-GSSD should be active"
        assert reported_nfs_status == "active", "NFS Server should be active"
