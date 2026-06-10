## DNS & HTTPS Configuration Validator for Multi-Site WordPress

Create a configuration validation system that verifies the setup of three WordPress sites with DNS, SSL, and reverse proxy configurations.

**Technical Requirements:**
- Language: Python 3.x
- Input: `/app/config.json` - Configuration file containing server setup details
- Output: `/app/validation_report.json` - Validation results with pass/fail status

**Input Format (`/app/config.json`):**
```json
{
  "dns": {
    "resolver": "string",
    "zone": "string",
    "records": [
      {"hostname": "string", "ip": "string"}
    ]
  },
  "nginx": {
    "sites": [
      {
        "domain": "string",
        "proxy_port": "integer",
        "ssl_cert_path": "string",
        "ssl_key_path": "string",
        "force_https": "boolean"
      }
    ]
  },
  "wordpress": {
    "containers": [
      {
        "name": "string",
        "port": "integer",
        "bind_ip": "string"
      }
    ]
  },
  "ssl": {
    "provider": "string",
    "auto_renew": "boolean",
    "renewal_frequency": "string"
  }
}
```

**Output Format (`/app/validation_report.json`):**
```json
{
  "overall_status": "pass|fail",
  "validations": {
    "dns_configuration": {"status": "pass|fail", "message": "string"},
    "nginx_configuration": {"status": "pass|fail", "message": "string"},
    "wordpress_containers": {"status": "pass|fail", "message": "string"},
    "ssl_certificates": {"status": "pass|fail", "message": "string"},
    "https_enforcement": {"status": "pass|fail", "message": "string"}
  },
  "errors": ["string"]
}
```

**Validation Rules:**
1. DNS must have resolver set to "localhost" or "127.0.0.1" and zone set to ".tst"
2. DNS records must include exactly 3 A records for site1.tst, site2.tst, site3.tst
3. Nginx must have exactly 3 site configurations with unique domains matching DNS records
4. Each Nginx site must proxy to a unique port (8081, 8082, 8083)
5. All Nginx sites must have force_https set to true
6. WordPress containers must match the proxy ports defined in Nginx configuration
7. All containers must bind to 127.0.0.1
8. SSL provider must be "letsencrypt" and auto_renew must be true
9. Renewal frequency must be "twice_daily" or more frequent

**Edge Cases:**
- Missing required fields should result in validation failure with descriptive error messages
- Duplicate ports or domains should be flagged as configuration conflicts
- Mismatched Nginx proxy ports and WordPress container ports should fail validation
- Invalid IP addresses or malformed domain names should be rejected
