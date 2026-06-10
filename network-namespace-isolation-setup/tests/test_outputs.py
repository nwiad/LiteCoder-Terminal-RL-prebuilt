"""
Tests for Network Namespace Isolation Setup task.

These tests verify that the agent created correct scripts under /app/
and that executing them produces the expected network environment.

Test execution assumes:
- The agent has already created the scripts and run them.
- The container has iproute2, iptables, tcpdump, jq installed.
- Tests run as root with appropriate capabilities.
"""

import os
import json
import stat
import subprocess

SCRIPTS_DIR = "/app"
SETUP_SCRIPT = os.path.join(SCRIPTS_DIR, "setup.sh")
CAPTURE_SCRIPT = os.path.join(SCRIPTS_DIR, "capture.sh")
REPORT_SCRIPT = os.path.join(SCRIPTS_DIR, "report.sh")
CLEANUP_SCRIPT = os.path.join(SCRIPTS_DIR, "cleanup.sh")
CAPTURE_FILE = os.path.join(SCRIPTS_DIR, "capture.pcap")
REPORT_FILE = os.path.join(SCRIPTS_DIR, "network_report.json")

ALL_SCRIPTS = [SETUP_SCRIPT, CAPTURE_SCRIPT, REPORT_SCRIPT, CLEANUP_SCRIPT]


def run_cmd(cmd, timeout=30):
    """Run a shell command and return the CompletedProcess."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


def ensure_setup():
    """Make sure the network environment is set up before state-checking tests."""
    # If namespaces already exist, skip
    r = run_cmd("ip netns list")
    if "app-ns" in r.stdout and "monitor-ns" in r.stdout:
        return
    # Otherwise run setup
    if os.path.isfile(SETUP_SCRIPT):
        run_cmd(f"bash {SETUP_SCRIPT}", timeout=15)


# ============================================================
# Section 1: Script existence, permissions, and shebang
# ============================================================

class TestScriptBasics:
    """Verify all four scripts exist, are executable, and have correct shebang."""

    def test_setup_script_exists(self):
        assert os.path.isfile(SETUP_SCRIPT), "setup.sh not found at /app/setup.sh"

    def test_capture_script_exists(self):
        assert os.path.isfile(CAPTURE_SCRIPT), "capture.sh not found at /app/capture.sh"

    def test_report_script_exists(self):
        assert os.path.isfile(REPORT_SCRIPT), "report.sh not found at /app/report.sh"

    def test_cleanup_script_exists(self):
        assert os.path.isfile(CLEANUP_SCRIPT), "cleanup.sh not found at /app/cleanup.sh"

    def test_setup_script_executable(self):
        mode = os.stat(SETUP_SCRIPT).st_mode
        assert mode & stat.S_IXUSR, "setup.sh is not executable"

    def test_capture_script_executable(self):
        mode = os.stat(CAPTURE_SCRIPT).st_mode
        assert mode & stat.S_IXUSR, "capture.sh is not executable"

    def test_report_script_executable(self):
        mode = os.stat(REPORT_SCRIPT).st_mode
        assert mode & stat.S_IXUSR, "report.sh is not executable"

    def test_cleanup_script_executable(self):
        mode = os.stat(CLEANUP_SCRIPT).st_mode
        assert mode & stat.S_IXUSR, "cleanup.sh is not executable"

    def test_setup_script_shebang(self):
        with open(SETUP_SCRIPT, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash"), (
            f"setup.sh shebang is '{first_line}', expected '#!/bin/bash'"
        )

    def test_capture_script_shebang(self):
        with open(CAPTURE_SCRIPT, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash"), (
            f"capture.sh shebang is '{first_line}', expected '#!/bin/bash'"
        )

    def test_report_script_shebang(self):
        with open(REPORT_SCRIPT, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash"), (
            f"report.sh shebang is '{first_line}', expected '#!/bin/bash'"
        )

    def test_cleanup_script_shebang(self):
        with open(CLEANUP_SCRIPT, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/bin/bash"), (
            f"cleanup.sh shebang is '{first_line}', expected '#!/bin/bash'"
        )


# ============================================================
# Section 2: setup.sh — exit code and network state
# ============================================================

class TestSetupScript:
    """Verify setup.sh creates the correct network environment."""

    def test_setup_exits_zero(self):
        """setup.sh must exit with code 0."""
        # Clean first to test from scratch
        if os.path.isfile(CLEANUP_SCRIPT):
            run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        r = run_cmd(f"bash {SETUP_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"setup.sh exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )

    def test_namespace_app_ns_exists(self):
        """app-ns namespace must exist after setup."""
        ensure_setup()
        r = run_cmd("ip netns list")
        assert "app-ns" in r.stdout, (
            f"app-ns not found in namespace list: {r.stdout}"
        )

    def test_namespace_monitor_ns_exists(self):
        """monitor-ns namespace must exist after setup."""
        ensure_setup()
        r = run_cmd("ip netns list")
        assert "monitor-ns" in r.stdout, (
            f"monitor-ns not found in namespace list: {r.stdout}"
        )

    def test_veth_app_exists_in_app_ns(self):
        """veth-app interface must exist inside app-ns."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns ip link show veth-app")
        assert r.returncode == 0, "veth-app not found in app-ns"
        assert "veth-app" in r.stdout

    def test_veth_monitor_exists_in_monitor_ns(self):
        """veth-monitor interface must exist inside monitor-ns."""
        ensure_setup()
        r = run_cmd("ip netns exec monitor-ns ip link show veth-monitor")
        assert r.returncode == 0, "veth-monitor not found in monitor-ns"
        assert "veth-monitor" in r.stdout

    def test_veth_app_ip_address(self):
        """veth-app must have IP 10.0.1.1/24."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns ip -4 addr show veth-app")
        assert "10.0.1.1/24" in r.stdout, (
            f"Expected 10.0.1.1/24 on veth-app, got: {r.stdout}"
        )

    def test_veth_monitor_ip_address(self):
        """veth-monitor must have IP 10.0.1.2/24."""
        ensure_setup()
        r = run_cmd("ip netns exec monitor-ns ip -4 addr show veth-monitor")
        assert "10.0.1.2/24" in r.stdout, (
            f"Expected 10.0.1.2/24 on veth-monitor, got: {r.stdout}"
        )

    def test_veth_app_is_up(self):
        """veth-app must be in UP state."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns ip link show veth-app")
        assert "UP" in r.stdout.upper(), "veth-app is not UP"

    def test_veth_monitor_is_up(self):
        """veth-monitor must be in UP state."""
        ensure_setup()
        r = run_cmd("ip netns exec monitor-ns ip link show veth-monitor")
        assert "UP" in r.stdout.upper(), "veth-monitor is not UP"

    def test_loopback_up_in_app_ns(self):
        """Loopback must be UP in app-ns."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns ip link show lo")
        assert "UP" in r.stdout.upper(), "lo is not UP in app-ns"

    def test_loopback_up_in_monitor_ns(self):
        """Loopback must be UP in monitor-ns."""
        ensure_setup()
        r = run_cmd("ip netns exec monitor-ns ip link show lo")
        assert "UP" in r.stdout.upper(), "lo is not UP in monitor-ns"


# ============================================================
# Section 3: iptables rules verification
# ============================================================

class TestIptablesRules:
    """Verify iptables rules in app-ns and monitor-ns."""

    def test_forward_policy_drop(self):
        """FORWARD chain in app-ns must have policy DROP."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns iptables -L FORWARD")
        assert r.returncode == 0, f"iptables failed: {r.stderr}"
        first_line = r.stdout.strip().split("\n")[0]
        assert "DROP" in first_line.upper(), (
            f"FORWARD policy is not DROP: {first_line}"
        )

    def test_icmp_allowed_input(self):
        """INPUT chain in app-ns must have an ACCEPT rule for ICMP."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns iptables -L INPUT -n")
        assert r.returncode == 0
        lines = r.stdout.lower()
        assert "icmp" in lines and "accept" in lines, (
            f"No ICMP ACCEPT rule found on INPUT chain: {r.stdout}"
        )

    def test_icmp_allowed_output(self):
        """OUTPUT chain in app-ns must have an ACCEPT rule for ICMP."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns iptables -L OUTPUT -n")
        assert r.returncode == 0
        lines = r.stdout.lower()
        assert "icmp" in lines and "accept" in lines, (
            f"No ICMP ACCEPT rule found on OUTPUT chain: {r.stdout}"
        )

    def test_log_rule_with_prefix(self):
        """INPUT chain in app-ns must have a LOG rule with prefix 'APP-NS-IN: '."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns iptables -L INPUT -n -v")
        assert r.returncode == 0
        assert "LOG" in r.stdout, f"No LOG rule found on INPUT: {r.stdout}"
        assert "APP-NS-IN: " in r.stdout, (
            f"LOG prefix 'APP-NS-IN: ' not found: {r.stdout}"
        )

    def test_nat_masquerade_in_monitor_ns(self):
        """monitor-ns must have a MASQUERADE rule on POSTROUTING for 10.0.1.0/24."""
        ensure_setup()
        r = run_cmd("ip netns exec monitor-ns iptables -t nat -L POSTROUTING -n")
        assert r.returncode == 0
        out = r.stdout.lower()
        assert "masquerade" in out, (
            f"No MASQUERADE rule found in monitor-ns nat POSTROUTING: {r.stdout}"
        )
        assert "10.0.1.0" in r.stdout, (
            f"MASQUERADE rule does not reference 10.0.1.0/24: {r.stdout}"
        )

    def test_ping_connectivity(self):
        """app-ns should be able to ping monitor-ns (10.0.1.2)."""
        ensure_setup()
        r = run_cmd("ip netns exec app-ns ping -c 2 -W 3 10.0.1.2", timeout=15)
        assert r.returncode == 0, (
            f"Ping from app-ns to 10.0.1.2 failed: {r.stderr}"
        )


# ============================================================
# Section 4: capture.sh — pcap file validation
# ============================================================

class TestCaptureScript:
    """Verify capture.sh produces a valid pcap with ICMP packets."""

    def test_capture_script_exits_zero(self):
        """capture.sh must exit with code 0."""
        ensure_setup()
        r = run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        assert r.returncode == 0, (
            f"capture.sh exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )

    def test_capture_pcap_exists(self):
        """capture.pcap must exist after running capture.sh."""
        ensure_setup()
        if not os.path.isfile(CAPTURE_FILE):
            run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        assert os.path.isfile(CAPTURE_FILE), "capture.pcap not found at /app/capture.pcap"

    def test_capture_pcap_not_empty(self):
        """capture.pcap must not be empty."""
        ensure_setup()
        if not os.path.isfile(CAPTURE_FILE):
            run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        size = os.path.getsize(CAPTURE_FILE)
        assert size > 0, "capture.pcap is empty (0 bytes)"

    def test_capture_pcap_has_icmp(self):
        """capture.pcap must contain ICMP packets when read by tcpdump."""
        ensure_setup()
        if not os.path.isfile(CAPTURE_FILE):
            run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        r = run_cmd(f"tcpdump -r {CAPTURE_FILE} -n icmp 2>/dev/null")
        # tcpdump -r outputs packet summaries; we need at least one line
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        assert len(lines) >= 1, (
            f"No ICMP packets found in capture.pcap. tcpdump output: {r.stdout[:500]}"
        )

    def test_capture_pcap_valid_magic(self):
        """capture.pcap must start with a valid pcap magic number."""
        ensure_setup()
        if not os.path.isfile(CAPTURE_FILE):
            run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        with open(CAPTURE_FILE, "rb") as f:
            magic = f.read(4)
        # Standard pcap: d4c3b2a1 or a1b2c3d4; pcapng: 0a0d0d0a
        valid_magics = [
            b'\xd4\xc3\xb2\xa1',  # pcap LE
            b'\xa1\xb2\xc3\xd4',  # pcap BE
            b'\x0a\x0d\x0d\x0a',  # pcapng
        ]
        assert magic in valid_magics, (
            f"capture.pcap has invalid magic bytes: {magic.hex()}"
        )


# ============================================================
# Section 5: report.sh — JSON report validation
# ============================================================

class TestReportScript:
    """Verify report.sh produces correct network_report.json."""

    def _get_report(self):
        """Helper: ensure report exists and return parsed JSON."""
        ensure_setup()
        # Always regenerate report to test the script itself
        r = run_cmd(f"bash {REPORT_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"report.sh exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )
        assert os.path.isfile(REPORT_FILE), "network_report.json not created"
        with open(REPORT_FILE, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "network_report.json is empty"
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"network_report.json is not valid JSON: {e}")

    def test_report_exits_zero(self):
        """report.sh must exit with code 0."""
        ensure_setup()
        r = run_cmd(f"bash {REPORT_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"report.sh exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )

    def test_report_file_exists(self):
        """network_report.json must exist."""
        self._get_report()

    def test_report_has_namespaces(self):
        """Report must contain 'namespaces' key with both namespaces."""
        data = self._get_report()
        assert "namespaces" in data, "Missing 'namespaces' key"
        ns = data["namespaces"]
        assert isinstance(ns, list), "'namespaces' must be a list"
        assert "app-ns" in ns, "'app-ns' not in namespaces list"
        assert "monitor-ns" in ns, "'monitor-ns' not in namespaces list"

    def test_report_has_veth_pair(self):
        """Report must contain 'veth_pair' with app_side and monitor_side."""
        data = self._get_report()
        assert "veth_pair" in data, "Missing 'veth_pair' key"
        vp = data["veth_pair"]
        assert "app_side" in vp, "Missing 'app_side' in veth_pair"
        assert "monitor_side" in vp, "Missing 'monitor_side' in veth_pair"

    def test_report_app_side_details(self):
        """app_side must have correct name, namespace, and IP."""
        data = self._get_report()
        app = data["veth_pair"]["app_side"]
        assert app.get("name") == "veth-app", (
            f"app_side name: expected 'veth-app', got '{app.get('name')}'"
        )
        assert app.get("namespace") == "app-ns", (
            f"app_side namespace: expected 'app-ns', got '{app.get('namespace')}'"
        )
        assert app.get("ip") == "10.0.1.1/24", (
            f"app_side ip: expected '10.0.1.1/24', got '{app.get('ip')}'"
        )

    def test_report_monitor_side_details(self):
        """monitor_side must have correct name, namespace, and IP."""
        data = self._get_report()
        mon = data["veth_pair"]["monitor_side"]
        assert mon.get("name") == "veth-monitor", (
            f"monitor_side name: expected 'veth-monitor', got '{mon.get('name')}'"
        )
        assert mon.get("namespace") == "monitor-ns", (
            f"monitor_side namespace: expected 'monitor-ns', got '{mon.get('namespace')}'"
        )
        assert mon.get("ip") == "10.0.1.2/24", (
            f"monitor_side ip: expected '10.0.1.2/24', got '{mon.get('ip')}'"
        )

    def test_report_iptables_rules_structure(self):
        """Report must have iptables_rules with app_ns and monitor_ns."""
        data = self._get_report()
        assert "iptables_rules" in data, "Missing 'iptables_rules' key"
        ipt = data["iptables_rules"]
        assert "app_ns" in ipt, "Missing 'app_ns' in iptables_rules"
        assert "monitor_ns" in ipt, "Missing 'monitor_ns' in iptables_rules"

    def test_report_forward_policy(self):
        """iptables_rules.app_ns.forward_policy must be 'DROP'."""
        data = self._get_report()
        policy = data["iptables_rules"]["app_ns"].get("forward_policy", "")
        assert policy.upper() == "DROP", (
            f"forward_policy: expected 'DROP', got '{policy}'"
        )

    def test_report_icmp_allowed(self):
        """iptables_rules.app_ns.icmp_allowed must be true."""
        data = self._get_report()
        icmp = data["iptables_rules"]["app_ns"].get("icmp_allowed")
        assert icmp is True, (
            f"icmp_allowed: expected true, got {icmp}"
        )

    def test_report_log_prefix(self):
        """iptables_rules.app_ns.log_prefix must be 'APP-NS-IN: '."""
        data = self._get_report()
        prefix = data["iptables_rules"]["app_ns"].get("log_prefix", "")
        # Accept both "APP-NS-IN: " (with trailing space) and "APP-NS-IN:" (stripped)
        assert prefix.strip().rstrip(":") == "APP-NS-IN" and prefix.startswith("APP-NS-IN:"), (
            f"log_prefix: expected 'APP-NS-IN: ', got '{prefix}'"
        )

    def test_report_nat_masquerade(self):
        """iptables_rules.monitor_ns.nat_masquerade must be true."""
        data = self._get_report()
        nat = data["iptables_rules"]["monitor_ns"].get("nat_masquerade")
        assert nat is True, (
            f"nat_masquerade: expected true, got {nat}"
        )


# ============================================================
# Section 6: Idempotency tests
# ============================================================

class TestIdempotency:
    """Verify scripts are idempotent as required."""

    def test_setup_idempotent(self):
        """Running setup.sh twice must not error."""
        ensure_setup()
        # Run setup a second time — must still exit 0
        r = run_cmd(f"bash {SETUP_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"setup.sh second run exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )
        # Verify state is still correct after second run
        r2 = run_cmd("ip netns list")
        assert "app-ns" in r2.stdout, "app-ns missing after idempotent setup"
        assert "monitor-ns" in r2.stdout, "monitor-ns missing after idempotent setup"

    def test_setup_no_duplicate_ips(self):
        """Running setup.sh twice must not create duplicate IP addresses."""
        ensure_setup()
        run_cmd(f"bash {SETUP_SCRIPT}", timeout=15)
        r = run_cmd("ip netns exec app-ns ip -4 addr show veth-app")
        # Count occurrences of the IP — should be exactly 1
        count = r.stdout.count("10.0.1.1/24")
        assert count == 1, (
            f"Expected exactly 1 occurrence of 10.0.1.1/24, found {count}"
        )


# ============================================================
# Section 7: cleanup.sh — teardown verification
# ============================================================

class TestCleanupScript:
    """Verify cleanup.sh properly removes the environment."""

    def test_cleanup_exits_zero(self):
        """cleanup.sh must exit with code 0."""
        ensure_setup()
        r = run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"cleanup.sh exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )

    def test_cleanup_removes_namespaces(self):
        """After cleanup, both namespaces must be gone."""
        ensure_setup()
        run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        r = run_cmd("ip netns list")
        assert "app-ns" not in r.stdout, "app-ns still exists after cleanup"
        assert "monitor-ns" not in r.stdout, "monitor-ns still exists after cleanup"

    def test_cleanup_removes_capture(self):
        """After cleanup, capture.pcap must be removed."""
        ensure_setup()
        # Create capture file if not present
        if not os.path.isfile(CAPTURE_FILE):
            run_cmd(f"bash {CAPTURE_SCRIPT}", timeout=30)
        run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        assert not os.path.isfile(CAPTURE_FILE), (
            "capture.pcap still exists after cleanup"
        )

    def test_cleanup_idempotent(self):
        """Running cleanup.sh twice must not error."""
        # First ensure clean state
        run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        # Run again on already-clean state
        r = run_cmd(f"bash {CLEANUP_SCRIPT}", timeout=15)
        assert r.returncode == 0, (
            f"cleanup.sh second run exited with {r.returncode}. stderr: {r.stderr[:500]}"
        )

