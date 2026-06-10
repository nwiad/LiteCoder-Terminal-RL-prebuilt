Build a production-ready API gateway using Nginx that provides rate limiting, basic authentication, and request routing to three mock backend microservices, all orchestrated with Docker Compose.

## Technical Requirements

- Language/Tools: Python 3 (Flask) for mock backends, Nginx for the gateway, Docker Compose for orchestration
- Working directory: /app
- All services defined in `/app/docker-compose.yml`
- Nginx configuration in `/app/nginx/nginx.conf`
- Backend service code in `/app/services/user_service/app.py`, `/app/services/order_service/app.py`, `/app/services/analytics_service/app.py`
- Each backend service must have its own `Dockerfile` in its directory (e.g., `/app/services/user_service/Dockerfile`)
- Nginx Dockerfile or image config in `/app/nginx/`
- Authentication credentials file generated at `/app/nginx/.htpasswd`

## Service Architecture

### Docker Compose Services

The `docker-compose.yml` must define exactly these service names:
- `gateway` — Nginx API gateway, exposed on host port **8080** (HTTP)
- `user-service` — Flask app on internal port 5001
- `order-service` — Flask app on internal port 5002
- `analytics-service` — Flask app on internal port 5003

All services must be on a shared Docker network. Run all services with `docker compose up -d --build` from `/app`.

### Mock Backend Endpoints

Each Flask service must return JSON responses with `Content-Type: application/json`.

**User Service** (port 5001):
- `GET /users` → `{"service": "user-service", "data": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}`
- `GET /health` → `{"status": "healthy", "service": "user-service"}`

**Order Service** (port 5002):
- `GET /orders` → `{"service": "order-service", "data": [{"id": 101, "item": "Widget", "quantity": 3}]}`
- `GET /health` → `{"status": "healthy", "service": "order-service"}`

**Analytics Service** (port 5003):
- `GET /analytics` → `{"service": "analytics-service", "data": {"visits": 1000, "conversions": 42}}`
- `GET /health` → `{"status": "healthy", "service": "analytics-service"}`

## Nginx Gateway Configuration

### Routing Rules

The gateway on port 8080 must route requests as follows:
- `/api/users` → user-service `/users`
- `/api/orders` → order-service `/orders` (requires authentication)
- `/api/analytics` → analytics-service `/analytics` (requires authentication)
- `/health` → return `200 OK` directly from Nginx with body `{"status": "gateway-healthy"}`

### Authentication

- Use HTTP Basic Authentication via `htpasswd` for protected endpoints (`/api/orders`, `/api/analytics`).
- Create a user with username `admin` and password `secret123`.
- Unauthenticated requests to protected endpoints must return HTTP `401`.
- Unprotected endpoints (`/api/users`, `/health`) must be accessible without credentials.

### Rate Limiting

Configure Nginx rate limiting with two zones:
- **Authenticated requests**: limit to **10 requests per minute** per client IP on protected endpoints.
- **Anonymous/unprotected requests**: limit to **2 requests per minute** per client IP on `/api/users`.
- When the rate limit is exceeded, Nginx must return HTTP **429** (Too Many Requests).

### SSL/TLS Termination

- Generate a self-signed certificate and key at `/app/nginx/ssl/selfsigned.crt` and `/app/nginx/ssl/selfsigned.key`.
- The gateway must also listen on port **8443** for HTTPS (expose 8443 on the host in docker-compose).
- HTTPS on port 8443 must serve the same routes as HTTP on port 8080.

### Logging

- Nginx access logs must use a structured JSON log format.
- The JSON log entries must include at minimum these fields: `remote_addr`, `request`, `status`, `request_time`.
- Access log file path inside the container: `/var/log/nginx/access.log`.

## Startup and Verification

After `docker compose up -d --build` from `/app`, the following must all succeed:

1. `curl -s http://localhost:8080/health` returns 200 with `{"status": "gateway-healthy"}`
2. `curl -s http://localhost:8080/api/users` returns 200 with the user-service JSON response
3. `curl -s http://localhost:8080/api/orders` returns 401 (no credentials)
4. `curl -s -u admin:secret123 http://localhost:8080/api/orders` returns 200 with order-service JSON
5. `curl -s -u admin:secret123 http://localhost:8080/api/analytics` returns 200 with analytics-service JSON
6. `curl -sk https://localhost:8443/health` returns 200 (HTTPS works)
7. Rapid repeated unauthenticated requests to `/api/users` (more than 2 in quick succession) eventually return 429
