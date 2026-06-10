## Network Traffic Analysis and iptables Configuration

Analyze a captured network traffic file to detect a port scanning attack, identify the attacker's IP address, and generate iptables rules to block the attacker while preserving SSH access.

### Technical Requirements

- Language/Tools: Bash scripting, standard Linux networking utilities
- Input: `/app/traffic.pcap` — a pcap file containing captured network traffic with a simulated port scan attack mixed in with normal traffic
- Output:
  - `/app/analysis_report.json` — JSON report of the traffic analysis
  - `/app/firewall_rules.sh` — executable Bash script that applies iptables rules

### Input Specification

The file `/app/traffic.pcap` is a standard pcap-format file. It contains:
- Normal traffic from multiple source IPs (small number of destination ports per IP)
- One attacker IP that performs a port scan (connecting to many distinct destination ports in a short time window)

A port scan is defined as: a single source IP that attempts connections to **50 or more distinct destination ports** on the target host.

### Output Specification

#### 1. `/app/analysis_report.json`

A JSON file with the following structure:

```json
{
  "attacker_ip": "<detected attacker IP address>",
  "total_packets": <integer, total number of packets in the pcap>,
  "attacker_packets": <integer, number of packets from the attacker IP>,
  "unique_ports_scanned": <integer, number of distinct destination ports the attacker targeted>
}
```

- All fields are required.
- `attacker_ip` must be a valid IPv4 address string.
- All numeric fields must be integers (not strings).

#### 2. `/app/firewall_rules.sh`

An executable Bash script (`chmod +x`) that, when run, applies iptables rules with the following requirements:

- **Block all incoming traffic** from the detected attacker IP (DROP or REJECT).
- **Allow SSH access** (TCP port 22) from all other IPs — there must be an explicit ACCEPT rule for destination port 22.
- The script must use `iptables` commands.
- The script must contain a shebang line (`#!/bin/bash` or `#!/usr/bin/env bash`).
- The attacker IP used in the blocking rule must match the `attacker_ip` value in `analysis_report.json`.
