## Multi-Container Reverse Proxy Setup with SSL/TLS Termination

Set up a multi-container environment using Docker Compose where an Nginx reverse proxy handles SSL/TLS termination and routes traffic to three backend services based on hostname.

### Technical Requirements

- Language/Tools: Docker Compose (version `3.8` or higher), Nginx, OpenSSL, Bash
- Working directory: `/app`
- All configuration files must be created under `/app`

### File Structure

Create the following files:

1. `/app/docker-compose.yml` — Docker Compose configuration
2. `/app/nginx/nginx.conf` — Nginx reverse proxy configuration
3. `/app/nginx/certs/server.crt` — Self-signed SSL certificate
4. `/app/nginx/certs/server.key` — SSL private key
5. `/app/renew-certs.sh` — Certificate renewal script (executable)

### Docker Compose Specification (`docker-compose.yml`)

Define the following services:

| Service Name | Image | Internal Port | Description |
|---|---|---|---|
| `nginx-proxy` | `nginx:latest` | 80, 443 | Reverse proxy with SSL termination |
| `static-site` | `nginx:alpine` | 80 | Static website |
| `api-service` | `nginx:alpine` | 80 | API service |
| `admin-panel` | `nginx:alpine` | 80 | Admin panel |

Requirements:
- The `nginx-proxy` service must publish port `443` mapped to host port `443` and port `80` mapped to host port `80`.
- The `nginx-proxy` service must mount `/app/nginx/nginx.conf` to `/etc/nginx/nginx.conf` (read-only) and `/app/nginx/certs` to `/etc/nginx/certs` (read-only).
- All four services must be on a shared Docker network named `proxy-network` (driver: `bridge`).
- The `nginx-proxy` service must declare `depends_on` for all three backend services.

### Nginx Configuration (`nginx/nginx.conf`)

The Nginx config must:
- Listen on port `443` with SSL enabled, using `/etc/nginx/certs/server.crt` and `/etc/nginx/certs/server.key`.
- Listen on port `80` and redirect all HTTP traffic to HTTPS (return 301).
- Define three `server` blocks (or use `if`/`map` logic) for hostname-based routing:
  - Requests with `Host: www.example.com` → proxy to `http://static-site:80`
  - Requests with `Host: api.example.com` → proxy to `http://api-service:80`
  - Requests with `Host: admin.example.com` → proxy to `http://admin-panel:80`
- Include `proxy_set_header Host $host;` and `proxy_set_header X-Real-IP $remote_addr;` in each proxy location block.
- Include `proxy_set_header X-Forwarded-Proto $scheme;` in each proxy location block.

### SSL Certificate Generation

Generate a self-signed certificate and key using OpenSSL:
- Certificate path: `/app/nginx/certs/server.crt`
- Key path: `/app/nginx/certs/server.key`
- Subject: `/CN=example.com`
- Validity: 365 days
- Key size: 2048 bits minimum
- The certificate's Subject Alternative Names (SAN) must include: `www.example.com`, `api.example.com`, `admin.example.com`

### Certificate Renewal Script (`renew-certs.sh`)

Create an executable Bash script at `/app/renew-certs.sh` that:
- Regenerates the self-signed certificate and key to the same paths.
- Reloads the Nginx container by running `docker compose -f /app/docker-compose.yml exec nginx-proxy nginx -s reload`.
- Exits with code `0` on success.

### Validation

After all files are created, run `docker compose -f /app/docker-compose.yml config` to validate the Compose file. The command must exit with code `0`.
