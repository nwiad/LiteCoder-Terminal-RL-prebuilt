## Reverse Proxy with Load Balancing and SSL Termination

Set up a production-ready Nginx reverse proxy with load balancing, SSL termination, and health checks for a multi-node web application using Docker Compose.

### Technical Requirements

- Docker and Docker Compose
- Nginx (as reverse proxy)
- OpenSSL (for certificate generation)
- Simple backend HTTP servers (Python, Node, or any lightweight HTTP server)

### Directory Structure

All files must be created under `/app/`:

```
/app/
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   └── ssl/
│       ├── server.crt
│       └── server.key
├── backend/
│   └── Dockerfile
└── docs/
    └── configuration.md
```

### Requirements

#### 1. SSL Certificates

Generate self-signed SSL certificates using OpenSSL and place them at `/app/nginx/ssl/server.crt` and `/app/nginx/ssl/server.key`.

- Certificate must use RSA with at least 2048-bit key length
- Common Name (CN) must be set to `localhost`
- Certificate validity must be at least 365 days

#### 2. Backend Servers

Create three backend HTTP server containers that each respond to `GET /` with an HTTP 200 response and a plain-text body containing the server's identifier (e.g., `Server 1`, `Server 2`, `Server 3`). Each backend must also respond to `GET /health` with HTTP 200 and body `OK`.

The three backends must be accessible within the Docker network on these ports:

- `backend1`: port `8080`
- `backend2`: port `8081`
- `backend3`: port `8082`

#### 3. Nginx Configuration (`/app/nginx/nginx.conf`)

The Nginx config must include:

**Upstream block:**
- Named `backend_servers`
- List all three backend servers (`backend1:8080`, `backend2:8081`, `backend3:8082`)
- Use `least_conn` load balancing algorithm
- Include `max_fails=3` and `fail_timeout=30s` for each server entry

**HTTPS server block (port 443):**
- Listen on port `443` with SSL enabled
- `server_name` set to `localhost`
- Reference the SSL certificate and key files at `/etc/nginx/ssl/server.crt` and `/etc/nginx/ssl/server.key`
- SSL protocols limited to `TLSv1.2` and `TLSv1.3` only
- `proxy_pass` to the `backend_servers` upstream
- Include these proxy headers: `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `Host`

**HTTP server block (port 80):**
- Listen on port `80`
- Return a `301` redirect to the HTTPS equivalent URL

**Logging:**
- Access log at `/var/log/nginx/access.log`
- Error log at `/var/log/nginx/error.log`

#### 4. Docker Compose (`/app/docker-compose.yml`)

- Define services: `nginx`, `backend1`, `backend2`, `backend3`
- The `nginx` service must:
  - Map host port `80` to container port `80`
  - Map host port `443` to container port `443`
  - Mount `/app/nginx/nginx.conf` to `/etc/nginx/nginx.conf`
  - Mount `/app/nginx/ssl/` to `/etc/nginx/ssl/`
  - Depend on all three backend services
- All services must be on a shared Docker network named `app_network`

#### 5. Documentation (`/app/docs/configuration.md`)

Create a Markdown document that includes:

- A table listing each service name, its internal port, and its role
- The load balancing algorithm used and why
- SSL/TLS configuration summary (protocols enabled, certificate type)
- How health checks work in the setup
