## Network Topology Discovery and Visualization

Build a network discovery tool that scans a local network, identifies devices, and generates a visualization of the network topology.

**Technical Requirements:**
- Python 3.x
- Input: Network configuration file at `/app/network_config.json`
- Output: Network topology data at `/app/topology.json` and visualization at `/app/network_graph.png`

**Input Specification:**

The `/app/network_config.json` file contains:
```json
{
  "subnet": "192.168.1.0/24",
  "scan_timeout": 300,
  "ports_to_scan": [22, 80, 443, 8080]
}
```

- `subnet`: CIDR notation for the network range to scan
- `scan_timeout`: Maximum time in seconds for the scan
- `ports_to_scan`: List of TCP ports to check on each host

**Output Specification:**

Generate `/app/topology.json` with discovered devices:
```json
{
  "scan_time": "2024-01-15T10:30:00Z",
  "subnet": "192.168.1.0/24",
  "devices": [
    {
      "ip": "192.168.1.1",
      "mac": "00:11:22:33:44:55",
      "hostname": "router.local",
      "manufacturer": "Cisco Systems",
      "open_ports": [80, 443],
      "os_guess": "Linux 3.x",
      "response_time_ms": 2.5
    }
  ],
  "total_devices": 5
}
```

Generate `/app/network_graph.png` as a visual representation showing:
- Nodes for each discovered device (labeled with IP and hostname)
- Connections between devices based on network topology
- PNG format, minimum 800x600 pixels

**Implementation Requirements:**

1. Read network configuration from `/app/network_config.json`
2. Perform network scanning to discover active hosts in the specified subnet
3. For each discovered device, collect: IP address, MAC address, hostname, open ports from the specified list, OS detection (if available), manufacturer lookup from MAC address
4. Store results in `/app/topology.json` with ISO 8601 timestamp
5. Generate network topology graph saved as `/app/network_graph.png`
6. Handle cases where devices don't respond to certain probes (use null for unavailable data)

**Error Handling:**

- If `/app/network_config.json` is missing or invalid, exit with error code 1
- If no devices are discovered, create valid output files with empty device lists
- Network scanning requires appropriate permissions; handle permission errors gracefully
