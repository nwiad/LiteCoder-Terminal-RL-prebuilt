## Dockerized HAProxy for Load Balancing with Health Checks

Build a load-balanced web application environment using Docker containers with HAProxy as the load balancer and health checks to ensure only healthy backends receive traffic.

### Technical Requirements

- Docker and Docker Compose
- HAProxy as the load balancer
- A simple backend web application (Node.js or Python — your choice)
- All project files must be placed under `/app/`

### Project Structure

The following files are required:

- `/app/docker-compose.yml` — orchestrates all services
- `/app/haproxy/haproxy.cfg` — HAProxy configuration
- `/app/app/` — directory containing the backend web application source and its Dockerfile

### Backend Web Application

- The backend app must expose an HTTP endpoint on port `3000` inside the container.
- `GET /` must return a JSON response with the following structure:

```json
{
  "server": "<container hostname>",
  "timestamp": "<ISO 8601 timestamp>"
}
```

- `GET /health` must return HTTP 200 with body `OK` when the server is healthy.

### Docker Compose Configuration (`/app/docker-compose.yml`)

- Define exactly 3 backend service replicas named `app1`, `app2`, `app3`.
- Define 1 HAProxy service named `haproxy`.
- The HAProxy service must publish port `80` on the host (mapped to HAProxy's listening port).
- All services must be on the same Docker network named `webnet`.

### HAProxy Configuration (`/app/haproxy/haproxy.cfg`)

- **Frontend:** Listen on port `80`, mode `http`, and forward traffic to the backend pool.
- **Backend:** Use `roundrobin` balancing algorithm across `app1`, `app2`, `app3` on port `3000`.
- **Health Checks:** Enable HTTP health checks against the `/health` endpoint on each backend. Backends that fail health checks must be removed from the rotation.
- **Stats:** Enable the HAProxy stats page on port `8404` at path `/stats`.

### Verification

After running `docker compose up -d` from `/app/`, the following must hold:

1. `curl http://localhost:80/` returns a valid JSON response containing `server` and `timestamp` fields.
2. Repeated requests to `http://localhost:80/` distribute across different backends (the `server` field changes across requests, demonstrating round-robin).
3. `curl http://localhost:80/health` returns HTTP 200.
4. The HAProxy stats page is accessible at `http://localhost:8404/stats`.
5. All 4 containers (haproxy + 3 backends) are running — verifiable via `docker compose ps`.
