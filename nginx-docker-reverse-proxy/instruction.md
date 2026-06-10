## Setting Up a Reverse Proxy with NGINX and Docker Compose

Configure a reverse proxy using NGINX inside a Docker container to route requests to three backend services running in separate containers, all orchestrated with Docker Compose.

### Technical Requirements

- Language/Tools: Python 3 (Flask), Node.js, NGINX, Docker, Docker Compose
- Working directory: `/app`
- All project files must be created under `/app`

### Project Structure

Create the following directory structure:

```
/app/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── webapp/
│   ├── Dockerfile
│   └── app.py
├── api/
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
└── static/
    ├── Dockerfile
    └── public/
        └── index.html
```

### Service Specifications

**1. Flask Web Application (`webapp`)**
- Container name: `webapp`
- Internal port: `5000`
- Endpoint `GET /` must return JSON: `{"service": "webapp", "status": "running"}`
- Endpoint `GET /health` must return JSON: `{"status": "healthy"}` with HTTP 200

**2. Node.js API Service (`api`)**
- Container name: `api`
- Internal port: `3000`
- Endpoint `GET /` must return JSON: `{"service": "api", "status": "running"}`
- Endpoint `GET /health` must return JSON: `{"status": "healthy"}` with HTTP 200

**3. Static File Server (`static`)**
- Container name: `static`
- Internal port: `8080`
- Serve static files from a `public/` directory
- The file `public/index.html` must contain an `<h1>` element with the text `Static File Server`

### NGINX Reverse Proxy Configuration

- Container name: `nginx`
- Exposed port: `80` on the host
- Routing rules based on URL path prefix:
  - `/webapp/` → forwards to the `webapp` service on port 5000 (strip the `/webapp` prefix)
  - `/api/` → forwards to the `api` service on port 3000 (strip the `/api` prefix)
  - `/static/` → forwards to the `static` service on port 8080 (strip the `/static` prefix)
- The NGINX config file must be located at `/app/nginx/nginx.conf`

### Docker Compose Configuration

- File: `/app/docker-compose.yml`
- Must define exactly four services: `nginx`, `webapp`, `api`, `static`
- All services must be on the same Docker network named `proxy-network`
- The NGINX service must expose port `80` to the host (mapping host port `80` to container port `80`)
- The NGINX service must depend on all three backend services

### Expected Behavior

After running `docker compose up -d` from `/app`:

1. `curl http://localhost/webapp/` returns `{"service": "webapp", "status": "running"}`
2. `curl http://localhost/webapp/health` returns `{"status": "healthy"}`
3. `curl http://localhost/api/` returns `{"service": "api", "status": "running"}`
4. `curl http://localhost/api/health` returns `{"status": "healthy"}`
5. `curl http://localhost/static/` returns HTML content containing `<h1>Static File Server</h1>`
