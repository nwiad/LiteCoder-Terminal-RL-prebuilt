"""
Tests for Network Scan Report Generator.
Validates /app/output.json and /app/report.html against the primary input /app/input.json.
"""
import json
import os
import re

# ── Paths ──────────────────────────────────────────────────────────────
OUTPUT_JSON = "/app/output.json"
REPORT_HTML = "/app/report.html"
INPUT_JSON = "/app/input.json"
ANALYZER_PY = "/app/analyzer.py"
REPORT_GEN_PY = "/app/report_generator.py"
MAIN_PY = "/app/main.py"


# ── Helpers ────────────────────────────────────────────────────────────
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def load_html(path):
    with open(path, "r") as f:
        return f.read()


def load_input():
    return load_json(INPUT_JSON)


def load_output():
    return load_json(OUTPUT_JSON)


# ══════════════════════════════════════════════════════════════════════
#  1. FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════

def test_output_json_exists():
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    assert os.path.getsize(OUTPUT_JSON) > 10, f"{OUTPUT_JSON} is empty or trivially small"


def test_report_html_exists():
    assert os.path.isfile(REPORT_HTML), f"{REPORT_HTML} does not exist"
    assert os.path.getsize(REPORT_HTML) > 50, f"{REPORT_HTML} is empty or trivially small"


def test_scripts_exist():
    for script in [ANALYZER_PY, REPORT_GEN_PY, MAIN_PY]:
        assert os.path.isfile(script), f"{script} does not exist"


# ══════════════════════════════════════════════════════════════════════
#  2. OUTPUT.JSON – TOP-LEVEL STRUCTURE
# ══════════════════════════════════════════════════════════════════════

def test_output_json_is_valid_json():
    data = load_output()
    assert isinstance(data, dict), "output.json root must be a JSON object"


def test_output_has_required_keys():
    data = load_output()
    assert "scan_summary" in data, "Missing 'scan_summary' key"
    assert "host_reports" in data, "Missing 'host_reports' key"


def test_scan_summary_keys():
    summary = load_output()["scan_summary"]
    required = ["subnet", "scan_timestamp", "total_hosts_scanned", "hosts_up", "hosts_down"]
    for key in required:
        assert key in summary, f"scan_summary missing key: {key}"


def test_host_report_entry_keys():
    reports = load_output()["host_reports"]
    assert isinstance(reports, list) and len(reports) > 0, "host_reports must be a non-empty list"
    required = ["ip", "mac", "hostname", "status", "open_ports_count", "open_ports", "risk_level"]
    for host in reports:
        for key in required:
            assert key in host, f"Host {host.get('ip','?')} missing key: {key}"


# ══════════════════════════════════════════════════════════════════════
#  3. SCAN SUMMARY – CORRECT VALUES
# ══════════════════════════════════════════════════════════════════════

def test_scan_summary_subnet():
    inp = load_input()
    summary = load_output()["scan_summary"]
    assert summary["subnet"] == inp["subnet"], (
        f"Expected subnet '{inp['subnet']}', got '{summary['subnet']}'"
    )


def test_scan_summary_timestamp():
    inp = load_input()
    summary = load_output()["scan_summary"]
    assert summary["scan_timestamp"] == inp["scan_timestamp"]


def test_scan_summary_total_hosts():
    inp = load_input()
    summary = load_output()["scan_summary"]
    expected = len(inp["hosts"])
    assert summary["total_hosts_scanned"] == expected, (
        f"Expected total_hosts_scanned={expected}, got {summary['total_hosts_scanned']}"
    )


def test_scan_summary_hosts_up():
    inp = load_input()
    summary = load_output()["scan_summary"]
    expected = sum(1 for h in inp["hosts"] if h["status"] == "up")
    assert summary["hosts_up"] == expected, (
        f"Expected hosts_up={expected}, got {summary['hosts_up']}"
    )


def test_scan_summary_hosts_down():
    inp = load_input()
    summary = load_output()["scan_summary"]
    expected = sum(1 for h in inp["hosts"] if h["status"] == "down")
    assert summary["hosts_down"] == expected, (
        f"Expected hosts_down={expected}, got {summary['hosts_down']}"
    )


# ══════════════════════════════════════════════════════════════════════
#  4. HOST REPORTS – FILTERING & SORTING
# ══════════════════════════════════════════════════════════════════════

def test_only_up_hosts_in_reports():
    """Down hosts must NOT appear in host_reports."""
    inp = load_input()
    down_ips = {h["ip"] for h in inp["hosts"] if h["status"] == "down"}
    reports = load_output()["host_reports"]
    report_ips = {h["ip"] for h in reports}
    overlap = down_ips & report_ips
    assert len(overlap) == 0, f"Down hosts found in host_reports: {overlap}"


def test_all_up_hosts_in_reports():
    """Every up host must appear in host_reports."""
    inp = load_input()
    up_ips = {h["ip"] for h in inp["hosts"] if h["status"] == "up"}
    reports = load_output()["host_reports"]
    report_ips = {h["ip"] for h in reports}
    missing = up_ips - report_ips
    assert len(missing) == 0, f"Up hosts missing from host_reports: {missing}"


def test_host_reports_count():
    inp = load_input()
    expected = sum(1 for h in inp["hosts"] if h["status"] == "up")
    reports = load_output()["host_reports"]
    assert len(reports) == expected, (
        f"Expected {expected} host reports, got {len(reports)}"
    )


def test_host_reports_sorted_by_ip():
    """host_reports must be sorted by IP (lexicographic string sort)."""
    reports = load_output()["host_reports"]
    ips = [h["ip"] for h in reports]
    assert ips == sorted(ips), f"host_reports not sorted by IP. Order: {ips}"


def test_host_status_field_is_up():
    """Every entry in host_reports must have status 'up'."""
    reports = load_output()["host_reports"]
    for host in reports:
        assert host["status"] == "up", f"Host {host['ip']} has status '{host['status']}'"


# ══════════════════════════════════════════════════════════════════════
#  5. OPEN PORTS – FILTERING & SORTING
# ══════════════════════════════════════════════════════════════════════

def _get_input_host(ip):
    inp = load_input()
    for h in inp["hosts"]:
        if h["ip"] == ip:
            return h
    return None


def test_only_open_ports_included():
    """Ports with state 'closed' or 'filtered' must be excluded."""
    reports = load_output()["host_reports"]
    inp = load_input()
    for host in reports:
        inp_host = _get_input_host(host["ip"])
        if inp_host is None:
            continue
        non_open = {p["port"] for p in inp_host["ports"] if p["state"] != "open"}
        reported = {p["port"] for p in host["open_ports"]}
        leaked = non_open & reported
        assert len(leaked) == 0, (
            f"Host {host['ip']}: non-open ports in output: {leaked}"
        )


def test_all_open_ports_included():
    """All ports with state 'open' must appear."""
    reports = load_output()["host_reports"]
    for host in reports:
        inp_host = _get_input_host(host["ip"])
        if inp_host is None:
            continue
        expected = {p["port"] for p in inp_host["ports"] if p["state"] == "open"}
        reported = {p["port"] for p in host["open_ports"]}
        missing = expected - reported
        assert len(missing) == 0, (
            f"Host {host['ip']}: open ports missing: {missing}"
        )


def test_open_ports_sorted_ascending():
    """Open ports within each host must be sorted by port number ascending."""
    reports = load_output()["host_reports"]
    for host in reports:
        ports = [p["port"] for p in host["open_ports"]]
        assert ports == sorted(ports), (
            f"Host {host['ip']}: ports not sorted ascending: {ports}"
        )


def test_open_ports_count_field():
    """open_ports_count must match the actual length of open_ports array."""
    reports = load_output()["host_reports"]
    for host in reports:
        assert host["open_ports_count"] == len(host["open_ports"]), (
            f"Host {host['ip']}: open_ports_count={host['open_ports_count']} "
            f"but open_ports has {len(host['open_ports'])} entries"
        )


def test_open_port_entry_keys():
    """Each open port entry must have the required fields."""
    reports = load_output()["host_reports"]
    required = ["port", "protocol", "service", "version", "vulnerability"]
    for host in reports:
        for p in host["open_ports"]:
            for key in required:
                assert key in p, (
                    f"Host {host['ip']} port {p.get('port','?')}: missing key '{key}'"
                )


# ══════════════════════════════════════════════════════════════════════
#  6. VULNERABILITY DETECTION
# ══════════════════════════════════════════════════════════════════════

def _find_host_report(ip):
    reports = load_output()["host_reports"]
    for h in reports:
        if h["ip"] == ip:
            return h
    return None


def _find_port_in_report(host_report, port_num):
    for p in host_report["open_ports"]:
        if p["port"] == port_num:
            return p
    return None


def test_vuln_ftp_port21():
    """Port 21 open → 'FTP service exposed'."""
    # 192.168.1.5 has port 21 open
    host = _find_host_report("192.168.1.5")
    assert host is not None, "Host 192.168.1.5 not found"
    port = _find_port_in_report(host, 21)
    assert port is not None, "Port 21 not found on 192.168.1.5"
    assert port["vulnerability"] == "FTP service exposed", (
        f"Port 21 vulnerability: '{port['vulnerability']}'"
    )


def test_vuln_telnet_port23():
    """Port 23 open → 'Telnet service exposed - unencrypted protocol'."""
    host = _find_host_report("192.168.1.5")
    assert host is not None
    port = _find_port_in_report(host, 23)
    assert port is not None, "Port 23 not found on 192.168.1.5"
    assert port["vulnerability"] == "Telnet service exposed - unencrypted protocol", (
        f"Port 23 vulnerability: '{port['vulnerability']}'"
    )


def test_vuln_rdp_port3389():
    """Port 3389 open → 'RDP service exposed'."""
    host = _find_host_report("192.168.1.25")
    assert host is not None
    port = _find_port_in_report(host, 3389)
    assert port is not None, "Port 3389 not found on 192.168.1.25"
    assert port["vulnerability"] == "RDP service exposed", (
        f"Port 3389 vulnerability: '{port['vulnerability']}'"
    )


def test_vuln_outdated_software():
    """Version with digit.dot pattern → 'Outdated software: <version>'."""
    # 192.168.1.1 (gateway) has port 80 with version "nginx 1.14.0"
    host = _find_host_report("192.168.1.1")
    assert host is not None
    port = _find_port_in_report(host, 80)
    assert port is not None, "Port 80 not found on 192.168.1.1"
    assert port["vulnerability"] == "Outdated software: nginx 1.14.0", (
        f"Port 80 vulnerability: '{port['vulnerability']}'"
    )


def test_vuln_none_for_clean_port():
    """Port with no version and not a flagged port number → 'None'."""
    # 192.168.1.100 (laptop1) has port 22 with empty version
    host = _find_host_report("192.168.1.100")
    assert host is not None
    port = _find_port_in_report(host, 22)
    assert port is not None, "Port 22 not found on 192.168.1.100"
    assert port["vulnerability"] == "None", (
        f"Port 22 vulnerability: '{port['vulnerability']}'"
    )


def test_vuln_none_for_no_version_non_flagged():
    """Ports 8080, 3000, 9090 on workstation1 have no version → 'None'."""
    host = _find_host_report("192.168.1.10")
    assert host is not None
    for pnum in [22, 3000, 8080, 9090]:
        port = _find_port_in_report(host, pnum)
        assert port is not None, f"Port {pnum} not found on 192.168.1.10"
        assert port["vulnerability"] == "None", (
            f"Port {pnum} on 192.168.1.10 vulnerability: '{port['vulnerability']}'"
        )


def test_vuln_ftp_takes_priority_over_outdated():
    """Port 21 rule fires before outdated-software rule even if version present."""
    # 192.168.1.5 has port 21 with version "vsftpd 2.3.4"
    host = _find_host_report("192.168.1.5")
    assert host is not None
    port = _find_port_in_report(host, 21)
    assert port is not None
    # Must be "FTP service exposed", NOT "Outdated software: vsftpd 2.3.4"
    assert port["vulnerability"] == "FTP service exposed", (
        f"FTP rule should take priority. Got: '{port['vulnerability']}'"
    )


def test_closed_telnet_not_flagged():
    """Port 23 with state 'closed' must NOT appear in open_ports at all."""
    # 192.168.1.1 (gateway) has port 23 closed
    host = _find_host_report("192.168.1.1")
    assert host is not None
    port = _find_port_in_report(host, 23)
    assert port is None, (
        "Port 23 (closed) should not appear in open_ports for 192.168.1.1"
    )


# ══════════════════════════════════════════════════════════════════════
#  7. RISK CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════

# Expected risk levels for the primary input.json:
#   192.168.1.1   → high    (outdated software)
#   192.168.1.5   → critical (telnet open)
#   192.168.1.10  → medium  (4 open ports, no vulns)
#   192.168.1.25  → critical (RDP open)
#   192.168.1.50  → high    (outdated software)
#   192.168.1.100 → low     (1 clean port)

EXPECTED_RISK = {
    "192.168.1.1": "high",
    "192.168.1.5": "critical",
    "192.168.1.10": "medium",
    "192.168.1.25": "critical",
    "192.168.1.50": "high",
    "192.168.1.100": "low",
}


def test_risk_levels_all_hosts():
    """Verify risk_level for every up host."""
    reports = load_output()["host_reports"]
    for host in reports:
        ip = host["ip"]
        if ip in EXPECTED_RISK:
            assert host["risk_level"] == EXPECTED_RISK[ip], (
                f"Host {ip}: expected risk '{EXPECTED_RISK[ip]}', "
                f"got '{host['risk_level']}'"
            )


def test_risk_critical_telnet():
    host = _find_host_report("192.168.1.5")
    assert host is not None
    assert host["risk_level"] == "critical"


def test_risk_critical_rdp():
    host = _find_host_report("192.168.1.25")
    assert host is not None
    assert host["risk_level"] == "critical"


def test_risk_high_outdated():
    host = _find_host_report("192.168.1.1")
    assert host is not None
    assert host["risk_level"] == "high"


def test_risk_medium_many_ports():
    host = _find_host_report("192.168.1.10")
    assert host is not None
    assert host["risk_level"] == "medium"


def test_risk_low_clean():
    host = _find_host_report("192.168.1.100")
    assert host is not None
    assert host["risk_level"] == "low"


def test_risk_level_values_are_valid():
    """All risk_level values must be one of the four valid strings."""
    valid = {"critical", "high", "medium", "low"}
    reports = load_output()["host_reports"]
    for host in reports:
        assert host["risk_level"] in valid, (
            f"Host {host['ip']}: invalid risk_level '{host['risk_level']}'"
        )


# ══════════════════════════════════════════════════════════════════════
#  8. HTML REPORT VALIDATION
# ══════════════════════════════════════════════════════════════════════

def test_html_is_valid_html5():
    """Report must start with a DOCTYPE declaration."""
    html = load_html(REPORT_HTML)
    assert html.strip().lower().startswith("<!doctype html"), (
        "report.html must start with <!DOCTYPE html>"
    )


def test_html_has_title():
    """Report must have a <title> containing 'Network Scan Report'."""
    html = load_html(REPORT_HTML)
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    assert title_match is not None, "No <title> element found"
    assert "network scan report" in title_match.group(1).lower(), (
        f"Title does not contain 'Network Scan Report': '{title_match.group(1)}'"
    )


def test_html_contains_subnet():
    """Report body must contain the subnet from input."""
    inp = load_input()
    html = load_html(REPORT_HTML)
    assert inp["subnet"] in html, (
        f"Subnet '{inp['subnet']}' not found in report.html"
    )


def test_html_has_table():
    """Report must contain at least one <table> element."""
    html = load_html(REPORT_HTML)
    assert "<table" in html.lower(), "No <table> element found in report.html"


def test_html_table_has_all_up_hosts():
    """Every up host IP must appear within a <tr> in the table."""
    inp = load_input()
    html = load_html(REPORT_HTML).lower()
    up_ips = [h["ip"] for h in inp["hosts"] if h["status"] == "up"]
    # Extract all table rows
    rows = re.findall(r"<tr.*?</tr>", html, re.DOTALL)
    for ip in up_ips:
        found = any(ip in row for row in rows)
        assert found, f"Up host {ip} not found in any table row"


def test_html_table_contains_risk_levels():
    """Risk level strings must appear in the HTML for each host."""
    reports = load_output()["host_reports"]
    html = load_html(REPORT_HTML).lower()
    rows = re.findall(r"<tr.*?</tr>", html, re.DOTALL)
    for host in reports:
        ip = host["ip"]
        risk = host["risk_level"]
        # Find the row containing this IP
        host_rows = [r for r in rows if ip in r]
        assert len(host_rows) > 0, f"No table row for {ip}"
        assert risk in host_rows[0], (
            f"Risk level '{risk}' not found in table row for {ip}"
        )


def test_html_no_down_hosts_in_table():
    """Down hosts must NOT appear in the table."""
    inp = load_input()
    html = load_html(REPORT_HTML).lower()
    down_ips = [h["ip"] for h in inp["hosts"] if h["status"] == "down"]
    rows = re.findall(r"<tr.*?</tr>", html, re.DOTALL)
    for ip in down_ips:
        found = any(ip in row for row in rows)
        assert not found, f"Down host {ip} should not appear in table"


# ══════════════════════════════════════════════════════════════════════
#  9. SPECIFIC HOST DATA INTEGRITY
# ══════════════════════════════════════════════════════════════════════

def test_webserver_filtered_port_excluded():
    """192.168.1.50 has port 3306 filtered — must not appear in open_ports."""
    host = _find_host_report("192.168.1.50")
    assert host is not None
    port = _find_port_in_report(host, 3306)
    assert port is None, "Filtered port 3306 should not appear in open_ports"
    assert host["open_ports_count"] == 3, (
        f"Expected 3 open ports for webserver, got {host['open_ports_count']}"
    )


def test_legacy_server_has_three_open_ports():
    """192.168.1.5 has ports 21, 23, 80 all open."""
    host = _find_host_report("192.168.1.5")
    assert host is not None
    assert host["open_ports_count"] == 3
    port_nums = [p["port"] for p in host["open_ports"]]
    assert port_nums == [21, 23, 80], f"Expected [21, 23, 80], got {port_nums}"


def test_host_mac_and_hostname_preserved():
    """MAC and hostname from input must be preserved in output."""
    inp = load_input()
    reports = load_output()["host_reports"]
    inp_map = {h["ip"]: h for h in inp["hosts"]}
    for host in reports:
        ip = host["ip"]
        if ip in inp_map:
            assert host["mac"] == inp_map[ip]["mac"], (
                f"Host {ip}: MAC mismatch"
            )
            assert host["hostname"] == inp_map[ip]["hostname"], (
                f"Host {ip}: hostname mismatch"
            )
