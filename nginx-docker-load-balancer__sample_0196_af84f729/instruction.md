## Multi-Server HTTP Load Balancer with NGINX and Docker

Set up a load-balanced web application using NGINX as a reverse proxy/load balancer in front of multiple Flask backend servers, all orchestrated with Docker Compose.

### Technical Requirements

- **Language/Framework:** Python 3 (Flask) for backend servers
- **Infrastructure:** Docker, Docker Compose, NGINX
- **Working directory:** `/app`

### File Structure

All files must be created under `/app`:

- `/app/docker-compose.yml` — orchestrates all containers
- `/app/app/app.py` — Flask application source
- `/app/app/Dockerfile` — Dockerfile for the Flask app
- `/app/nginx/nginx.conf` — NGINX configuration
- `/app/nginx/Dockerfile` — Dockerfile for the NGINX container (or use the official `nginx` image directly in docker-compose)

### Flask Application (`/app/app/app.py`)

- The Flask app must expose two HTTP endpoints:
  - `GET /` — returns a JSON response: `{"server_id": "<HOSTNAME>", "message": "Hello from server <HOSTNAME>"}` where `<HOSTNAME>` is the container's hostname (use the system hostname or the `HOSTNAME` environment variable). Content-Type must be `application/json`.
  - `GET /health` — returns a JSON response: `{"status": "healthy"}` with HTTP 200.
- The app listens on port `5000` inside the container.

### Docker Compose (`/app/docker-compose.yml`)

- Define exactly **3 Flask backend service replicas** as separate services named `backend1`, `backend2`, `backend3`. Each builds from `/app/app/Dockerfile` and exposes port `5000` internally.
- Define **1 NGINX service** named `nginx` that:
  - Maps host port `8080` to container port `80`.
  - Depends on all three backend services.

### NGINX Configuration (`/app/nginx/nginx.conf`)

- Configure an `upstream` block that lists all three backend containers (`backend1:5000`, `backend2:5000`, `backend3:5000`).
- Use **round-robin** load balancing (the default).
- Proxy all requests on `/` to the upstream group.
- Set appropriate proxy headers (`Host`, `X-Real-IP`, `X-Forwarded-For`).

### Verification

After running `docker compose up -d --build` from `/app`, the infrastructure must satisfy:

1. `curl http://localhost:8080/` returns a valid JSON response containing `server_id` and `message` fields.
2. `curl http://localhost:8080/health` returns `{"status": "healthy"}` with HTTP 200.
3. Sending **10 sequential requests** to `http://localhost:8080/` must return responses from **at least 2 distinct `server_id` values**, demonstrating that load balancing is active.
4. All 4 containers (3 backends + 1 nginx) must be running — verifiable via `docker compose ps`.
