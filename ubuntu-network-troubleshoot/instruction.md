## Task: Ubuntu Container Network Troubleshooting

You are a system administrator managing Ubuntu containers. A container has lost external internet connectivity and you must diagnose and fix the network issues to restore access.

**Technical Requirements:**
- Environment: Ubuntu container with standard networking tools (ip, ping, curl, systemd-resolved, iptables)
- Working directory: /app
- Output: JSON report at /app/report.json

**Your Tasks:**

1. Diagnose the network connectivity issues by checking:
   - Network interface status and configuration
   - DNS resolution capability
   - Routing table configuration
   - Firewall rules
   - Network service status

2. Implement fixes to restore external internet connectivity

3. Verify the container can successfully reach external resources

4. Generate a troubleshooting report at /app/report.json with the following structure:

```json
{
  "issues_found": [
    {
      "component": "string (e.g., 'dns', 'routing', 'interface', 'firewall', 'service')",
      "description": "string describing the issue",
      "severity": "string (critical/major/minor)"
    }
  ],
  "fixes_applied": [
    {
      "component": "string",
      "action": "string describing what was fixed",
      "command": "string (command used to fix, if applicable)"
    }
  ],
  "connectivity_status": {
    "can_reach_external": "boolean",
    "dns_working": "boolean",
    "test_results": [
      {
        "target": "string (e.g., '8.8.8.8', 'google.com')",
        "success": "boolean"
      }
    ]
  }
}
```

**Success Criteria:**
- External internet connectivity is restored
- The container can resolve domain names via DNS
- The container can reach external IP addresses
- A valid JSON report is generated at /app/report.json documenting all issues found and fixes applied
