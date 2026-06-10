## Multi-Service Docker Network with Nginx Proxy and SSL Termination

Build a multi-container application stack using Docker Compose where an Nginx reverse proxy handles SSL termination and domain-based routing to three backend services.

### Technical Requirements

- All project files must be created under `/app/`
- Docker Compose file: `/app/docker-compose.yml`
- Nginx configuration: `/app/nginx/nginx.conf`
- SSL certificates directory: `/app/certs/`

### Services

The `docker-compose.yml` must define the following services and a custom bridge network:

1. **Custom Docker Network**
   - Network name: `app-network`
   - Driver: `bridge`
   - All services must be attached to this network.

2. **node-app** — A Node.js HTTP service
   - Dockerfile: `/app/node-app/Dockerfile`
   - Application source: `/app/node-app/app.js`
   - Listens internally on port `3000`
   - Responds to `GET /` with JSON: `{"service": "node-app", "status": "ok"}`
   - Responds to `GET /health` with JSON: `{"healthy": true}`
   - Container name: `node-app`

3. **flask-app** — A Python Flask HTTP service
   - Dockerfile: `/app/flask-app/Dockerfile`
   - Application source: `/app/flask-app/app.py`
   - Listens internally on port `5000`
   - Responds to `GET /` with JSON: `{"service": "flask-app", "status": "ok"}`
   - Responds to `GET /health` with JSON: `{"healthy": true}`
   - Container name: `flask-app`

4. **static-server** — An Nginx-based static file server
   - Dockerfile: `/app/static-server/Dockerfile`
   - Nginx config: `/app/static-server/nginx.conf`
   - Must serve a file `/app/static-server/html/index.html` containing exactly: `<h1>Static Server</h1>`
   - Listens internally on port `8080`
   - Container name: `static-server`

5. **nginx-proxy** — Nginx reverse proxy with SSL termination
   - Dockerfile: `/app/nginx/Dockerfile`
   - Configuration: `/app/nginx/nginx.conf`
   - Listens on port `443` (HTTPS) mapped to host port `8443`
   - Listens on port `80` (HTTP) mapped to host port `8080`, redirecting all HTTP traffic to HTTPS
   - Container name: `nginx-proxy`
   - Depends on all three backend services

### SSL Certificates

- Generate self-signed SSL certificates stored in `/app/certs/`
- Private key: `/app/certs/server.key`
- Certificate: `/app/certs/server.crt`
- Provide a generation script at `/app/certs/generate-certs.sh` that creates these files using `openssl`

### Domain-Based Routing (nginx-proxy)

The Nginx proxy must route requests based on the `Host` header:

| Host Header         | Backend Target         |
|----------------------|------------------------|
| `node.local`        | `node-app:3000`        |
| `flask.local`       | `flask-app:5000`       |
| `static.local`      | `static-server:8080`   |

Any request with an unrecognized `Host` header should return HTTP `444` (connection closed) or `502`.

### Docker Compose Specification

- Compose file version: `"3.8"` or later
- All services must have `restart: unless-stopped`
- The `nginx-proxy` service must declare `depends_on` for all three backend services
- All containers must be on the `app-network` network

### Verification

After running `docker compose up -d` from `/app/`, the following should work:

```
curl -k --resolve node.local:8443:127.0.0.1 https://node.local:8443/
# Returns: {"service": "node-app", "status": "ok"}

curl -k --resolve flask.local:8443:127.0.0.1 https://flask.local:8443/
# Returns: {"service": "flask-app", "status": "ok"}

curl -k --resolve static.local:8443:127.0.0.1 https://static.local:8443/
# Returns: <h1>Static Server</h1>

curl -k --resolve node.local:8443:127.0.0.1 https://node.local:8443/health
# Returns: {"healthy": true}
```
