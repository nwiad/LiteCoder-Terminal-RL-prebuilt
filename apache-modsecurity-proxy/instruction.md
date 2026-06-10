## Reverse Proxy with ModSecurity WAF

Set up an Apache reverse proxy with ModSecurity Web Application Firewall to protect a backend Node.js application with custom security rules and logging.

## Technical Requirements

- Apache 2.4+ with mod_proxy, mod_proxy_http, and ModSecurity modules
- Node.js backend application listening on port 3000
- ModSecurity with OWASP Core Rule Set (CRS)
- Apache listening on port 8080

## Implementation Requirements

### 1. Node.js Backend Application

Create a Node.js application at `/app/backend/server.js` that:
- Listens on port 3000
- Provides endpoint GET `/api/status` returning JSON: `{"status": "ok", "service": "backend"}`
- Provides endpoint POST `/api/data` that accepts JSON body and returns: `{"received": true, "data": <received_data>}`
- Provides endpoint GET `/api/user?id=<id>` that returns: `{"user_id": "<id>", "name": "User <id>"}`

### 2. Apache Reverse Proxy Configuration

Create Apache configuration at `/app/apache/proxy.conf` that:
- Configures Apache to listen on port 8080
- Proxies all requests to `http://localhost:3000`
- Preserves original host headers
- Enables ModSecurity engine

### 3. ModSecurity Custom Rules

Create custom ModSecurity rules at `/app/modsecurity/custom-rules.conf` that:
- Block requests containing SQL injection patterns (e.g., `UNION SELECT`, `OR 1=1`)
- Block requests with XSS patterns (e.g., `<script>`, `javascript:`)
- Block requests with path traversal patterns (e.g., `../`, `..\\`)
- Log all blocked requests with rule ID and matched pattern

### 4. Security Event Logging

Configure logging at `/app/logs/modsec_audit.log` that captures:
- Timestamp of security event
- Request URI that triggered the rule
- Rule ID that was matched
- Client IP address (can be localhost for testing)

### 5. Test Results Documentation

Create `/app/test_results.json` with the following structure:

```json
{
  "legitimate_requests": {
    "status_endpoint": {"status_code": 200, "blocked": false},
    "data_endpoint": {"status_code": 200, "blocked": false},
    "user_endpoint": {"status_code": 200, "blocked": false}
  },
  "malicious_requests": {
    "sql_injection": {"blocked": true, "rule_matched": "<rule_id>"},
    "xss_attempt": {"blocked": true, "rule_matched": "<rule_id>"},
    "path_traversal": {"blocked": true, "rule_matched": "<rule_id>"}
  }
}
```

## Expected Behavior

- Legitimate API requests pass through the proxy to the backend
- Malicious requests are blocked by ModSecurity before reaching the backend
- All security events are logged with sufficient detail for audit purposes
- The reverse proxy correctly forwards responses from the backend to clients
