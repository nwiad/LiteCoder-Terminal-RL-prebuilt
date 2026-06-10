## Build an Nginx Reverse Proxy with Load Balancing, SSL Termination, and Rate Limiting

Set up Nginx as a reverse proxy that distributes traffic across multiple backend servers, terminates SSL, and enforces rate limiting.

### Technical Requirements

- **OS:** Linux (Debian/Ubuntu-based)
- **Nginx** must be installed and running
- **Backend servers:** Create 3 simple HTTP backend servers (using Python, Node.js, or any lightweight approach) listening on ports **8081**, **8082**, and **8083**. Each backend must return a plain-text or JSON response that includes its own port number so that load balancing can be verified (e.g., backend on port 8081 returns a response containing `8081`).
- Backend servers must be running as background processes when verification occurs.

### Nginx Configuration

All Nginx configuration must be placed in `/etc/nginx/sites-available/loadbalancer.conf` and symlinked/enabled in `/etc/nginx/sites-enabled/`.

The configuration must include:

1. **Upstream block** named `backend_servers` that lists the three backend servers (`127.0.0.1:8081`, `127.0.0.1:8082`, `127.0.0.1:8083`) with **weighted round-robin** load balancing. Assign weights 3, 2, and 1 respectively.

2. **SSL termination:**
   - Generate a self-signed SSL certificate and key stored at:
     - Certificate: `/etc/nginx/ssl/server.crt`
     - Key: `/etc/nginx/ssl/server.key`
   - Configure an HTTPS server block listening on port **443**.
   - The server_name must be set to `localhost`.

3. **HTTP-to-HTTPS redirect:**
   - A server block listening on port **80** that returns a **301 redirect** to HTTPS.

4. **Reverse proxy:**
   - Location `/` must proxy requests to the `backend_servers` upstream.
   - Must include `proxy_set_header Host $host;` and `proxy_set_header X-Real-IP $remote_addr;`.

5. **Rate limiting:**
   - Define a rate-limiting zone named `rate_limit_zone` using `$binary_remote_addr` as the key, with a zone size of `10m` and a rate of `10r/s`.
   - Apply `limit_req` on the `/` location with `burst=20` and `nodelay`.

6. **Logging:**
   - Access log at `/var/log/nginx/proxy_access.log`.
   - Error log at `/var/log/nginx/proxy_error.log`.

7. **Performance tuning** (in the main `nginx.conf` or the site config):
   - `worker_connections` must be set to at least **1024** in the `events` block.

### Verification Script

Create a Bash script at `/app/verify.sh` that performs the following checks and writes results to `/app/output.json`:

1. Check that Nginx is running (process exists).
2. Check that all 3 backend servers are responding on ports 8081, 8082, 8083.
3. Send an HTTP request to `http://localhost:80` and verify it returns a 301 redirect.
4. Send an HTTPS request to `https://localhost:443` (using `curl -k` to accept self-signed cert) and verify it returns a 200 response with content from a backend.
5. Send 5 HTTPS requests and collect the backend port from each response to verify that more than one backend is used (load balancing is working).
6. Verify the SSL certificate file exists at `/etc/nginx/ssl/server.crt`.
7. Verify the rate limit zone `rate_limit_zone` is configured in the Nginx config.

### Output Format

`/app/output.json` must be a JSON object with the following structure:

```json
{
  "nginx_running": true,
  "backends_responding": {
    "8081": true,
    "8082": true,
    "8083": true
  },
  "http_redirect": true,
  "https_working": true,
  "load_balancing": true,
  "ssl_cert_exists": true,
  "rate_limit_configured": true
}
```

Each value is a boolean (`true`/`false`) reflecting the actual check result. The script must be executable (`chmod +x /app/verify.sh`) and when run, produce the `/app/output.json` file with all checks passing.
