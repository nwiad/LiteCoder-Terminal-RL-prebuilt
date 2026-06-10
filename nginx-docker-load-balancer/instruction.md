## Containerized Load Balancer with Nginx and Docker Compose

Set up a containerized load balancer using Nginx that distributes HTTP traffic across multiple backend web application containers, with health checks, SSL termination, and monitoring, all orchestrated via Docker Compose.

### Technical Requirements

- Docker and Docker Compose
- All project files must be created under `/app/`
- The final setup must be launchable via `docker compose -f /app/docker-compose.yml up -d`

### Project Structure

Create the following files:

- `/app/docker-compose.yml` — orchestrates all services
- `/app/nginx/nginx.conf` — Nginx load balancer configuration
- `/app/nginx/ssl/server.crt` — self-signed SSL certificate
- `/app/nginx/ssl/server.key` — SSL private key
- `/app/backend/Dockerfile` — Dockerfile for the backend web application
- `/app/backend/app.py` — a minimal Python (Flask or similar) web application used as the backend
- `/app/prometheus/prometheus.yml` — Prometheus configuration

### Backend Application

- Each backend instance must expose an HTTP endpoint on port `5000`.
- `GET /` must return a JSON response: `{"service": "<container_hostname>", "status": "ok"}` with Content-Type `application/json`.
- `GET /health` must return HTTP 200 with body `{"status": "healthy"}` when the service is running normally.

### Docker Compose Services

The `docker-compose.yml` must define the following services with these exact names:

| Service      | Description                          |
|--------------|--------------------------------------|
| `backend1`   | First backend app instance           |
| `backend2`   | Second backend app instance          |
| `backend3`   | Third backend app instance           |
| `nginx`      | Nginx load balancer                  |
| `prometheus`  | Prometheus monitoring               |
| `grafana`    | Grafana dashboard                    |

All services must be connected to a custom Docker bridge network named `lb-network`.

### Nginx Load Balancer Configuration

- Define an `upstream` block named `backend` that lists `backend1:5000`, `backend2:5000`, and `backend3:5000`.
- Use the `least_conn` load balancing method.
- Listen on port `80` for HTTP and redirect all HTTP traffic to HTTPS.
- Listen on port `443` for HTTPS using the self-signed SSL certificate and key from `/app/nginx/ssl/`.
- Proxy pass HTTPS requests to the `backend` upstream.
- Include a `location /health` block that returns HTTP 200 with body `ok` directly from Nginx (used as a load balancer health check endpoint).
- Set the following proxy headers: `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, and `Host`.

### SSL Termination

- Generate a self-signed SSL certificate and private key and place them at `/app/nginx/ssl/server.crt` and `/app/nginx/ssl/server.key`.
- The certificate must have a Common Name (CN) of `localhost`.
- The certificate must be valid for at least 365 days.

### Health Checks

In `docker-compose.yml`, each backend service (`backend1`, `backend2`, `backend3`) must include a Docker health check that:
- Sends a request to `http://localhost:5000/health`
- Has an interval of 10 seconds
- Has a timeout of 5 seconds
- Retries 3 times

### Port Mappings

Expose the following ports on the host:

| Service     | Host Port | Container Port |
|-------------|-----------|----------------|
| `nginx`     | 80        | 80             |
| `nginx`     | 443       | 443            |
| `prometheus`| 9090      | 9090           |
| `grafana`   | 3000      | 3000           |

Backend containers must NOT expose ports directly to the host.

### Prometheus Configuration

`/app/prometheus/prometheus.yml` must define a scrape configuration with at least one job named `nginx` that scrapes the Nginx service endpoint. The `scrape_interval` must be set to `15s`.

### Grafana

- The Grafana service must use the official `grafana/grafana` image.
- It must set the environment variable `GF_SECURITY_ADMIN_PASSWORD` to `admin`.

### Output

After all files are created, write a summary to `/app/output.json` with the following structure:

```json
{
  "services": ["backend1", "backend2", "backend3", "nginx", "prometheus", "grafana"],
  "network": "lb-network",
  "nginx_ports": [80, 443],
  "ssl_cn": "localhost",
  "lb_method": "least_conn",
  "backend_count": 3,
  "health_check_endpoint": "/health"
}
```
