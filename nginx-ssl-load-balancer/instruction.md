## Setup Nginx Load Balancer with SSL/TLS Termination

Configure an Nginx load balancer that terminates SSL/TLS connections and distributes traffic across multiple backend servers.

### Technical Requirements

- **Platform:** Linux with Nginx installed and available via `nginx` command
- **Working directory:** /app

### Tasks

1. **Install Nginx** on the system if not already installed. Ensure the `nginx` binary is available and the service can be started/tested.

2. **Generate a self-signed SSL certificate** for the domain `ecommerce.example.com`:
   - Private key: `/app/ssl/server.key` (RSA 2048-bit)
   - Certificate: `/app/ssl/server.crt` (valid for 365 days)
   - Subject must include `CN=ecommerce.example.com`

3. **Create the main Nginx load balancer configuration** at `/app/nginx/load_balancer.conf` with the following specifications:

   **Upstream block** (named `backend_servers`):
   - `server1.backend.local:8080`
   - `server2.backend.local:8080`
   - `server3.backend.local:8080`
   - Load balancing algorithm: `least_conn`

   **HTTPS server block** (listening on port `443 ssl`):
   - `server_name ecommerce.example.com;`
   - SSL certificate and key pointing to the paths generated in step 2
   - SSL protocols limited to: `TLSv1.2 TLSv1.3`
   - `proxy_pass` forwarding to the `backend_servers` upstream
   - The following security headers must be set (via `add_header` or `proxy_set_header` as appropriate):
     - `Strict-Transport-Security "max-age=31536000; includeSubDomains"`
     - `X-Frame-Options DENY`
     - `X-Content-Type-Options nosniff`
   - Proxy headers to pass to backends:
     - `proxy_set_header Host $host;`
     - `proxy_set_header X-Real-IP $remote_addr;`
     - `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
     - `proxy_set_header X-Forwarded-Proto $scheme;`

   **HTTP server block** (listening on port `80`):
   - Redirect all HTTP traffic to HTTPS using a `301` redirect (`return 301 https://$host$request_uri;`)

   **Health checks:**
   - Configure `max_fails=3` and `fail_timeout=30s` on each upstream server entry

4. **Validate the configuration** by running `nginx -t -c /app/nginx/load_balancer.conf` (or equivalent) and save the output to `/app/nginx/validation_result.txt`. The validation output should contain the string `syntax is ok`.

5. **Create a configuration summary** at `/app/nginx/config_summary.json` in the following JSON format:
   ```json
   {
     "domain": "ecommerce.example.com",
     "ssl_certificate": "/app/ssl/server.crt",
     "ssl_key": "/app/ssl/server.key",
     "ssl_protocols": ["TLSv1.2", "TLSv1.3"],
     "load_balancing_algorithm": "least_conn",
     "backend_servers": [
       "server1.backend.local:8080",
       "server2.backend.local:8080",
       "server3.backend.local:8080"
     ],
     "health_check": {
       "max_fails": 3,
       "fail_timeout": "30s"
     },
     "security_headers": [
       "Strict-Transport-Security",
       "X-Frame-Options",
       "X-Content-Type-Options"
     ],
     "http_redirect_to_https": true
   }
   ```

### Expected Output Files

| File | Description |
|---|---|
| `/app/ssl/server.key` | RSA 2048-bit private key |
| `/app/ssl/server.crt` | Self-signed X.509 certificate |
| `/app/nginx/load_balancer.conf` | Complete Nginx configuration |
| `/app/nginx/validation_result.txt` | Output of nginx config syntax check |
| `/app/nginx/config_summary.json` | JSON summary of the configuration |
