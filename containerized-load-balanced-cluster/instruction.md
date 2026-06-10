## Build a Containerized Load-Balanced Web Cluster

Build a containerized three-tier web cluster (HAProxy → Nginx → Flask) on a single Docker host. All components must run via Docker Compose and the cluster must be reachable on the host.

### Technical Requirements

- Docker and Docker Compose must be installed and functional.
- All project files live under `/app/`.
- Python 3 for the Flask application.

### Project File Structure

```
/app/
├── docker-compose.yml
├── flask-app/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── nginx/
│   └── nginx.conf
├── haproxy/
│   └── haproxy.cfg
└── ARCHITECTURE.md
```

### Flask Application (`/app/flask-app/app.py`)

- A Flask web application listening on port `5000`.
- `GET /` — returns a plain-text response containing the container's hostname (e.g., the value of the `HOSTNAME` environment variable), so that round-robin behavior is observable.
- `GET /health` — returns JSON `{"status": "ok"}` with HTTP 200 and content type `application/json`.

### Flask Dockerfile (`/app/flask-app/Dockerfile`)

- Base image: `python:3-slim` (or any `python:3` slim variant).
- Runs as a non-root user.
- Installs dependencies from `requirements.txt`.
- The built image must be tagged `flask-app:1.0` (done via `docker-compose.yml` build config or manual build).

### Docker Compose (`/app/docker-compose.yml`)

- Compose file must define at least three services: `app`, `nginx`, and `haproxy`.
- The `app` service must run exactly 3 replicas of the Flask container (use `deploy.replicas: 3` or equivalent).
- All services must be on a custom bridge network named `webcluster`.
- Only `haproxy` exposes ports to the host:
  - Host port `80` → HAProxy HTTP frontend.
  - Host port `8404` → HAProxy stats page.
- No other service should publish ports to the host.

### Nginx Configuration (`/app/nginx/nginx.conf`)

- Acts as a reverse proxy sitting between HAProxy and the Flask app instances.
- Defines an `upstream` block pointing to the 3 Flask app containers on port 5000.
- Includes passive health-check parameters: `max_fails=2` and `fail_timeout=15s` on each upstream server entry.
- Listens on port `80` inside its container.

### HAProxy Configuration (`/app/haproxy/haproxy.cfg`)

- Frontend bound to `*:80` that forwards traffic to a backend.
- Backend uses `roundrobin` balance algorithm pointing to the Nginx service.
- HTTP health check configured on the backend, checking the `/health` endpoint with an interval of `2s`.
- A dedicated `frontend` or `listen` block for the stats page:
  - Binds to `*:8404`.
  - Stats URI is `/stats`.
  - Stats must be enabled (`stats enable`).

### Verification Criteria

After running `docker compose up -d` (or `docker-compose up -d`) from `/app/`:

1. `curl -s http://localhost/` returns a successful HTTP 200 response.
2. `curl -s http://localhost/health` returns `{"status": "ok"}` with HTTP 200.
3. `curl -s http://localhost:8404/stats` returns the HAProxy stats page (HTTP 200).
4. All expected containers (3 Flask replicas, 1 Nginx, 1 HAProxy) are running.
5. The custom Docker network `webcluster` exists.

### ARCHITECTURE.md (`/app/ARCHITECTURE.md`)

A brief document describing:
- The three-tier architecture (HAProxy → Nginx → Flask).
- Port mappings (host port 80 for traffic, host port 8404 for stats).
- The network topology (custom bridge network `webcluster`).
