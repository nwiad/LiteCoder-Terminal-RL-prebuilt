## DNS-over-TLS Resolver Setup and Validation

Create a Python script that sets up and validates a DNS-over-TLS (DoT) resolver using dnsmasq and Stubby on Ubuntu.

**Technical Requirements:**
- Python 3.x
- Input: `/app/config.json` - Configuration parameters for DoT setup
- Output: `/app/validation_report.json` - Validation results and status

**Input Format (`/app/config.json`):**
```json
{
  "upstream_servers": [
    {"name": "cloudflare", "address": "1.1.1.1", "tls_port": 853, "hostname": "cloudflare-dns.com"},
    {"name": "quad9", "address": "9.9.9.9", "tls_port": 853, "hostname": "dns.quad9.net"}
  ],
  "stubby_port": 53000,
  "test_domains": ["example.com", "google.com", "github.com"]
}
```

**Implementation Requirements:**

1. **Configuration Generation**: Generate valid configuration files for:
   - Stubby configuration (YAML format) with upstream DoT servers
   - dnsmasq configuration forwarding to localhost:53000

2. **Service Validation**: Check that:
   - Stubby is listening on the configured port
   - dnsmasq is running and forwarding queries
   - No port conflicts exist (check systemd-resolved status)

3. **DNS Query Testing**: Perform DNS lookups for test domains and verify:
   - Queries resolve successfully
   - Responses are received through the local resolver
   - Query response times are recorded

4. **Cache Verification**: Test DNS caching by:
   - Performing the same query twice
   - Comparing response times (cached should be faster)

**Output Format (`/app/validation_report.json`):**
```json
{
  "setup_status": "success|partial|failed",
  "stubby_running": true,
  "dnsmasq_running": true,
  "port_conflicts": [],
  "dns_tests": [
    {"domain": "example.com", "resolved": true, "ip": "93.184.216.34", "response_time_ms": 45},
    {"domain": "google.com", "resolved": true, "ip": "142.250.80.46", "response_time_ms": 38}
  ],
  "cache_test": {
    "domain": "example.com",
    "first_query_ms": 45,
    "second_query_ms": 2,
    "cache_working": true
  },
  "errors": []
}
```

**Error Handling:**
- Handle missing dependencies gracefully
- Report configuration errors in the errors array
- Continue validation even if some checks fail
