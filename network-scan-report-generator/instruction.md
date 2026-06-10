# Network Scan Analysis & Report Generation Suite

Build a Python-based network scan analysis suite that processes raw network scan data (host discovery results and port scan results), identifies potential vulnerabilities based on open ports/services, and generates a structured HTML report.

## Technical Requirements

- Language: Python 3.x
- No external packages beyond the Python standard library are required
- All scripts must be executable standalone via `python3 <script>.py`

## Input

A JSON file at `/app/input.json` containing raw network scan data with the following structure:

```json
{
  "subnet": "192.168.1.0/24",
  "scan_timestamp": "2025-06-15T10:30:00Z",
  "hosts": [
    {
      "ip": "192.168.1.1",
      "mac": "AA:BB:CC:DD:EE:01",
      "hostname": "gateway.local",
      "status": "up",
      "ports": [
        {
          "port": 80,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "nginx 1.14.0"
        },
        {
          "port": 443,
          "protocol": "tcp",
          "state": "open",
          "service": "https",
          "version": "nginx 1.14.0"
        },
        {
          "port": 23,
          "protocol": "tcp",
          "state": "closed",
          "service": "telnet",
          "version": ""
        }
      ]
    }
  ]
}
```

Each host has `ip` (string), `mac` (string), `hostname` (string), `status` ("up" or "down"), and `ports` (array). Each port entry has `port` (integer 1-65535), `protocol` (string), `state` ("open", "closed", or "filtered"), `service` (string), and `version` (string, may be empty).

## Output

### 1. `/app/output.json`

A JSON file containing the analysis results:

```json
{
  "scan_summary": {
    "subnet": "192.168.1.0/24",
    "scan_timestamp": "2025-06-15T10:30:00Z",
    "total_hosts_scanned": 5,
    "hosts_up": 3,
    "hosts_down": 2
  },
  "host_reports": [
    {
      "ip": "192.168.1.1",
      "mac": "AA:BB:CC:DD:EE:01",
      "hostname": "gateway.local",
      "status": "up",
      "open_ports_count": 2,
      "open_ports": [
        {
          "port": 80,
          "protocol": "tcp",
          "service": "http",
          "version": "nginx 1.14.0",
          "vulnerability": "Outdated software: nginx 1.14.0"
        }
      ],
      "risk_level": "high"
    }
  ]
}
```

Field specifications:

- `scan_summary`: aggregated counts from the input data. `total_hosts_scanned` is the total number of hosts in the input. `hosts_up` and `hosts_down` count hosts by their `status` field.
- `host_reports`: one entry per host whose `status` is `"up"`, sorted by IP address (lexicographic string sort). Hosts with `status` `"down"` must be excluded from `host_reports`.
- `open_ports`: include only ports where `state` is `"open"`. Sorted by port number ascending.
- `vulnerability`: a string describing the vulnerability. Apply these rules in order to each open port:
  - If `port` is 21 (FTP): `"FTP service exposed"`
  - If `port` is 23 (Telnet): `"Telnet service exposed - unencrypted protocol"`
  - If `port` is 3389 (RDP): `"RDP service exposed"`
  - If `version` is non-empty and contains a version number pattern (digits separated by dots, e.g. `1.14.0`), flag as `"Outdated software: <version_field_value>"` where `<version_field_value>` is the exact content of the `version` field.
  - Otherwise: `"None"`
- `risk_level`: determined by the vulnerabilities found on the host's open ports:
  - `"critical"`: host has any port with Telnet or RDP vulnerability
  - `"high"`: host has any port with FTP vulnerability OR any port flagged as outdated software
  - `"medium"`: host has 3 or more open ports but none of the above vulnerabilities
  - `"low"`: all other up hosts
  - Evaluate in the priority order listed above (critical > high > medium > low).

### 2. `/app/report.html`

An HTML report file that meets these requirements:

- Valid HTML5 document (starts with `<!DOCTYPE html>` or `<!doctype html>`)
- Contains a `<title>` element with text including "Network Scan Report"
- Contains the subnet value from the input somewhere in the document body
- Contains an HTML `<table>` element listing each up host with at least columns for: IP address, hostname, open port count, and risk level
- Each up host from the input must appear as a row in the table (the host's IP must appear in a table row)
- Risk level values in the table must use the exact strings: `critical`, `high`, `medium`, or `low`

## Scripts

Create the following files under `/app/`:

1. `analyzer.py` — Reads `/app/input.json`, performs the analysis (vulnerability detection, risk classification), and writes `/app/output.json`.
2. `report_generator.py` — Reads `/app/output.json` and generates `/app/report.html`.
3. `main.py` — Orchestrator that runs the full pipeline: calls the analyzer then the report generator. Running `python3 /app/main.py` must produce both `/app/output.json` and `/app/report.html`.
