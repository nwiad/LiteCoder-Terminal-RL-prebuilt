Build a production-grade reverse proxy with SSL termination and WAF-like request filtering to protect a legacy vulnerable web application.

**Technical Requirements:**
- Platform: Linux (Ubuntu/Debian-based)
- Web server: nginx-full
- SSL: Let's Encrypt via certbot
- Backend: DVWA (Damn Vulnerable Web Application) on port 8080
- Security: fail2ban, ufw firewall
- Domain: reverse-test.example.com

**Implementation Requirements:**

1. **System Setup:**
   - Install nginx-full, certbot, python3-certbot-nginx, fail2ban, ufw
   - Configure ufw to allow SSH (22), HTTP (80), HTTPS (443) only
   - Enable ufw firewall

2. **Backend Application:**
   - Deploy DVWA on localhost:8080
   - Verify accessibility via `curl http://localhost:8080`

3. **Reverse Proxy Configuration:**
   - Configure nginx to proxy requests to localhost:8080
   - Redirect all HTTP traffic to HTTPS
   - Obtain Let's Encrypt certificate for reverse-test.example.com
   - Accept Let's Encrypt TOS non-interactively

4. **SSL Hardening:**
   - Modern TLS protocols only (TLS 1.2+)
   - Strong cipher suites
   - OCSP stapling enabled
   - HSTS header configured
   - Security headers (X-Frame-Options, X-Content-Type-Options, etc.)

5. **WAF Rules:**
   - Block requests matching attack patterns in URI or query parameters:
     - SQL injection patterns (e.g., `UNION SELECT`, `OR 1=1`, `' OR '`)
     - XSS patterns (e.g., `<script>`, `javascript:`, `onerror=`)
     - Directory traversal (e.g., `../`, `..%2F`)
   - Return nginx 444 status (connection drop) on match

6. **Intrusion Prevention:**
   - Configure fail2ban to monitor nginx access/error logs
   - Ban IPs triggering WAF blocks >3 times in 10 minutes
   - Ban duration: 20 minutes

7. **Verification Script:**
   - Create automated test script at /app/verify.sh that validates:
     - HTTP to HTTPS redirect works
     - DVWA accessible through reverse proxy via HTTPS
     - WAF blocks malicious payloads (test at least 3 attack patterns)
     - fail2ban jail is active and configured
   - Script must exit with code 0 on success, non-zero on failure

8. **Documentation:**
   - Create /app/implementation-notes.md containing:
     - Architecture overview (reverse proxy → backend flow)
     - Certificate renewal process
     - Location of WAF rule configuration files
     - fail2ban configuration details

**Output Files:**
- /app/verify.sh - Automated verification script
- /app/implementation-notes.md - Implementation documentation
- Nginx configuration files in standard locations (/etc/nginx/)
- fail2ban configuration in standard locations (/etc/fail2ban/)

**Success Criteria:**
- HTTPS endpoint serves DVWA content correctly
- HTTP requests redirect to HTTPS
- WAF blocks at least 3 different attack pattern types
- fail2ban jail is active and monitoring nginx logs
- Verification script passes all checks
