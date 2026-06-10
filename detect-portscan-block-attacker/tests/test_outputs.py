"""
Tests for the port scan detection and iptables configuration task.

Validates:
1. /app/analysis_report.json - correct structure, types, and values
2. /app/firewall_rules.sh - executable script with correct iptables rules
3. Consistency between the two output files
"""

import json
import os
import re
import stat

REPORT_PATH = "/app/analysis_report.json"
FIREWALL_PATH = "/app/firewall_rules.sh"

# Ground truth from the pcap generation (generate_pcap.py with seed=42)
EXPECTED_ATTACKER_IP = "10.45.33.187"
EXPECTED_TOTAL_PACKETS = 206
EXPECTED_ATTACKER_PACKETS = 80
EXPECTED_UNIQUE_PORTS = 80

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def load_report():
    """Load and return the JSON report, or None on failure."""
    assert os.path.isfile(REPORT_PATH), f"Report file not found: {REPORT_PATH}"
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "Report file is empty"
    return json.loads(content)


def load_firewall_script():
    """Load and return the firewall script content."""
    assert os.path.isfile(FIREWALL_PATH), f"Firewall script not found: {FIREWALL_PATH}"
    with open(FIREWALL_PATH, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, "Firewall script is empty"
    return content


# ===========================================================================
# Tests for /app/analysis_report.json
# ===========================================================================

class TestReportFileExists:
    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), f"Expected report at {REPORT_PATH}"

    def test_report_is_valid_json(self):
        load_report()  # will raise on invalid JSON

    def test_report_not_empty(self):
        size = os.path.getsize(REPORT_PATH)
        assert size > 10, f"Report file suspiciously small ({size} bytes)"


class TestReportStructure:
    """All required keys present with correct types."""

    def test_has_attacker_ip(self):
        report = load_report()
        assert "attacker_ip" in report, "Missing key: attacker_ip"

    def test_has_total_packets(self):
        report = load_report()
        assert "total_packets" in report, "Missing key: total_packets"

    def test_has_attacker_packets(self):
        report = load_report()
        assert "attacker_packets" in report, "Missing key: attacker_packets"

    def test_has_unique_ports_scanned(self):
        report = load_report()
        assert "unique_ports_scanned" in report, "Missing key: unique_ports_scanned"

    def test_attacker_ip_is_string(self):
        report = load_report()
        assert isinstance(report["attacker_ip"], str), "attacker_ip must be a string"

    def test_total_packets_is_int(self):
        report = load_report()
        assert isinstance(report["total_packets"], int), "total_packets must be an integer"

    def test_attacker_packets_is_int(self):
        report = load_report()
        assert isinstance(report["attacker_packets"], int), "attacker_packets must be an integer"

    def test_unique_ports_is_int(self):
        report = load_report()
        assert isinstance(report["unique_ports_scanned"], int), "unique_ports_scanned must be an integer"


class TestReportValues:
    """Verify the actual detected values match ground truth."""

    def test_attacker_ip_is_valid_ipv4(self):
        report = load_report()
        ip = report["attacker_ip"]
        # Must match dotted-quad IPv4 pattern
        pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        assert re.match(pattern, ip), f"attacker_ip is not valid IPv4: {ip}"
        # Each octet 0-255
        octets = ip.split(".")
        for o in octets:
            assert 0 <= int(o) <= 255, f"Invalid octet {o} in IP {ip}"

    def test_attacker_ip_correct(self):
        report = load_report()
        assert report["attacker_ip"] == EXPECTED_ATTACKER_IP, (
            f"Expected attacker IP {EXPECTED_ATTACKER_IP}, got {report['attacker_ip']}"
        )

    def test_total_packets_correct(self):
        report = load_report()
        assert report["total_packets"] == EXPECTED_TOTAL_PACKETS, (
            f"Expected total_packets={EXPECTED_TOTAL_PACKETS}, got {report['total_packets']}"
        )

    def test_attacker_packets_correct(self):
        report = load_report()
        assert report["attacker_packets"] == EXPECTED_ATTACKER_PACKETS, (
            f"Expected attacker_packets={EXPECTED_ATTACKER_PACKETS}, got {report['attacker_packets']}"
        )

    def test_unique_ports_scanned_correct(self):
        report = load_report()
        assert report["unique_ports_scanned"] == EXPECTED_UNIQUE_PORTS, (
            f"Expected unique_ports_scanned={EXPECTED_UNIQUE_PORTS}, got {report['unique_ports_scanned']}"
        )

    def test_total_packets_positive(self):
        report = load_report()
        assert report["total_packets"] > 0, "total_packets must be positive"

    def test_attacker_packets_positive(self):
        report = load_report()
        assert report["attacker_packets"] > 0, "attacker_packets must be positive"

    def test_unique_ports_above_threshold(self):
        """The attacker must have scanned >= 50 ports (the detection threshold)."""
        report = load_report()
        assert report["unique_ports_scanned"] >= 50, (
            f"unique_ports_scanned={report['unique_ports_scanned']} is below the 50-port threshold"
        )

    def test_attacker_packets_leq_total(self):
        """Attacker packets cannot exceed total packets."""
        report = load_report()
        assert report["attacker_packets"] <= report["total_packets"], (
            "attacker_packets exceeds total_packets — impossible"
        )


# ===========================================================================
# Tests for /app/firewall_rules.sh
# ===========================================================================

class TestFirewallFileExists:
    def test_firewall_file_exists(self):
        assert os.path.isfile(FIREWALL_PATH), f"Expected firewall script at {FIREWALL_PATH}"

    def test_firewall_not_empty(self):
        size = os.path.getsize(FIREWALL_PATH)
        assert size > 10, f"Firewall script suspiciously small ({size} bytes)"

    def test_firewall_is_executable(self):
        st = os.stat(FIREWALL_PATH)
        is_exec = bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        assert is_exec, "Firewall script is not executable (missing +x permission)"


class TestFirewallContent:
    """Validate the firewall script contains the required iptables rules."""

    def test_has_shebang(self):
        content = load_firewall_script()
        first_line = content.strip().split("\n")[0].strip()
        assert first_line.startswith("#!"), (
            f"Firewall script missing shebang. First line: {first_line}"
        )
        assert "bash" in first_line or "sh" in first_line, (
            f"Shebang does not reference bash/sh: {first_line}"
        )

    def test_uses_iptables(self):
        content = load_firewall_script()
        assert "iptables" in content, "Firewall script does not contain any iptables commands"

    def test_blocks_attacker_ip(self):
        """Must contain a rule that blocks (DROP or REJECT) the attacker IP."""
        content = load_firewall_script()
        # The attacker IP must appear in the script
        assert EXPECTED_ATTACKER_IP in content, (
            f"Attacker IP {EXPECTED_ATTACKER_IP} not found in firewall script"
        )
        # Must have DROP or REJECT action associated with the attacker
        content_lower = content.lower()
        has_drop = "drop" in content_lower
        has_reject = "reject" in content_lower
        assert has_drop or has_reject, (
            "Firewall script has no DROP or REJECT action for the attacker"
        )

    def test_attacker_block_rule_structure(self):
        """Verify there's an iptables line that references the attacker IP with DROP/REJECT."""
        content = load_firewall_script()
        lines = content.split("\n")
        found_block_rule = False
        for line in lines:
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            if "iptables" in stripped and EXPECTED_ATTACKER_IP in stripped:
                if "DROP" in stripped.upper() or "REJECT" in stripped.upper():
                    found_block_rule = True
                    break
        assert found_block_rule, (
            f"No iptables rule found that blocks {EXPECTED_ATTACKER_IP} with DROP/REJECT"
        )

    def test_allows_ssh_port_22(self):
        """Must have an explicit ACCEPT rule for TCP destination port 22."""
        content = load_firewall_script()
        lines = content.split("\n")
        found_ssh_rule = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "iptables" in stripped and "ACCEPT" in stripped.upper():
                # Check for port 22 reference: --dport 22 or -p tcp ... 22
                if re.search(r"--dport\s+22\b", stripped) or re.search(r"-p\s+tcp.*22", stripped):
                    found_ssh_rule = True
                    break
        assert found_ssh_rule, (
            "No iptables ACCEPT rule found for SSH (TCP port 22)"
        )

    def test_ssh_rule_uses_tcp(self):
        """The SSH allow rule should specify TCP protocol."""
        content = load_firewall_script()
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "iptables" in stripped and "ACCEPT" in stripped.upper() and "22" in stripped:
                assert "-p tcp" in stripped.lower() or "-p TCP" in stripped, (
                    f"SSH rule does not specify TCP protocol: {stripped}"
                )
                return
        # If we get here, no SSH rule was found at all (caught by other test)


# ===========================================================================
# Cross-file consistency
# ===========================================================================

class TestConsistency:
    """Verify the attacker IP is consistent between the report and firewall script."""

    def test_attacker_ip_matches_across_files(self):
        report = load_report()
        content = load_firewall_script()
        report_ip = report["attacker_ip"]
        assert report_ip in content, (
            f"Attacker IP from report ({report_ip}) not found in firewall script"
        )

    def test_firewall_blocks_reported_attacker(self):
        """The IP blocked in the firewall must be the same one reported in JSON."""
        report = load_report()
        content = load_firewall_script()
        report_ip = report["attacker_ip"]
        lines = content.split("\n")
        found = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "iptables" in stripped and report_ip in stripped:
                if "DROP" in stripped.upper() or "REJECT" in stripped.upper():
                    found = True
                    break
        assert found, (
            f"Firewall script does not block the reported attacker IP ({report_ip})"
        )
