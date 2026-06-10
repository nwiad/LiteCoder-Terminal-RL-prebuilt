## Multi-Container Micro-Service Health Dashboard

Build a Docker Compose stack that runs three demo HTTP services, Prometheus, Grafana, and an Nginx reverse proxy — all on a single Docker network. Nginx serves as the sole entry point, routing requests by hostname to the correct upstream service.

### Technical Requirements

- **Language/Tools:** Docker, Docker Compose, Nginx, Prometheus, Grafana
- **Working directory:** `/app`

### Demo Services

Three demo services are provided in `/app/services/`. Each is a small HTTP server:

| Service    | Directory              | Internal Port | Hostname          |
|------------|------------------------|---------------|-------------------|
| demo-svc-1 | `/app/services/svc1/` | 8001          | svc1.local.dev    |
| demo-svc-2 | `/app/services/svc2/` | 8002          | svc2.local.dev    |
| demo-svc-3 | `/app/services/svc3/` | 8003          | svc3.local.dev    |

Each service must:
- Respond to `GET /` with an HTTP 200 and a JSON body `{"service": "<name>", "status": "ok"}`.
- Expose a `GET /metrics` endpoint returning Prometheus-format metrics including at least a counter named `http_requests_total`.

If the provided service code does not exist or is incomplete, create minimal Python (Flask or http.server) services that satisfy the above contract. Each service directory must contain a `Dockerfile`.

### Docker Compose (`/app/docker-compose.yml`)

The file must define at least these services: `demo-svc-1`, `demo-svc-2`, `demo-svc-3`, `prometheus`, `grafana`, `nginx`.

All services must join a custom Docker network named `micro-stack` (driver: bridge).

### Prometheus (`/app/prometheus/prometheus.yml`)

- Global scrape interval: `5s`
- Scrape jobs must include:
  - A job named `prometheus` that scrapes Prometheus itself.
  - A job named `demo-services` (or three individual jobs) that scrapes all three demo services on their `/metrics` endpoints.

### Grafana

- Grafana must be accessible through Nginx and auto-provision a datasource pointing to the Prometheus container.
- A dashboard JSON file must be placed at `/app/grafana/dashboards/services.json`.
- The dashboard must contain:
  - One panel per demo service showing service UP status (using the Prometheus `up` metric).
  - One panel per demo service showing requests-per-second (using `http_requests_total`).
- Grafana provisioning config files must be placed under `/app/grafana/provisioning/` so the datasource and dashboard are loaded automatically on startup.

### Nginx (`/app/nginx/`)

- Nginx listens on port `443` (HTTPS) and port `80` (HTTP).
- All HTTP requests on port 80 must return a `301` redirect to the HTTPS equivalent.
- Use self-signed TLS certificates. Generate them and place them at `/app/nginx/certs/server.crt` and `/app/nginx/certs/server.key`.
- Host-based routing in the Nginx config (`/app/nginx/nginx.conf` or `/app/nginx/conf.d/default.conf`):
  - `prom.local.dev` → `prometheus:9090`
  - `graf.local.dev` → `grafana:3000`
  - `svc1.local.dev` → `demo-svc-1:8001`
  - `svc2.local.dev` → `demo-svc-2:8002`
  - `svc3.local.dev` → `demo-svc-3:8003`
- The Nginx container must expose ports `80` and `443` to the host.

### Expected Output / Verification

After running `docker compose -f /app/docker-compose.yml up -d`, the following must hold:

1. All six containers are running (exit code 0 from `docker compose ps`).
2. All containers are on the `micro-stack` network.
3. `/app/docker-compose.yml`, `/app/prometheus/prometheus.yml`, `/app/grafana/dashboards/services.json`, and the Nginx config file all exist.
4. Prometheus config has a scrape interval of `5s` and targets covering all three demo services.
5. Nginx config contains `server_name` directives for all five hostnames.
6. Grafana provisioning directory contains datasource and dashboard provider YAML files.
7. `curl -k --resolve svc1.local.dev:443:<host-ip> https://svc1.local.dev/` (and similarly for svc2, svc3) returns HTTP 200.
8. `curl -k --resolve prom.local.dev:443:<host-ip> https://prom.local.dev/` returns the Prometheus UI (HTTP 200).
9. `curl -k --resolve graf.local.dev:443:<host-ip> https://graf.local.dev/` returns the Grafana UI (HTTP 200).
10. HTTP to HTTPS redirect: `curl -I --resolve svc1.local.dev:80:<host-ip> http://svc1.local.dev/` returns a `301` with a `Location` header pointing to `https://`.
