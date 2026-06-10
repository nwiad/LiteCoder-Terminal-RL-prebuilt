## Reverse Proxy with NGINX and Dynamic Upstream Configuration

Set up a load-balanced NGINX reverse proxy that routes traffic to multiple Node.js backend servers, with health checks and automatic failover.

### Technical Requirements

- **Platform:** Linux with NGINX and Node.js installed
- **Working directory:** /app
- **Backend servers:** 3 Node.js HTTP servers running on ports 3001, 3002, and 3003
- **NGINX reverse proxy:** Listening on port 8080

### Backend Servers

Create a file `/app/backend/server.js` that starts a simple Node.js HTTP server. The server must accept a `PORT` environment variable to determine which port to listen on.

Each backend server must handle the following routes:

1. `GET /` — Returns a JSON response:
   ```json
   {"server": "backend-<PORT>", "status": "ok"}
   ```
   where `<PORT>` is the port number the server is running on (e.g., `"backend-3001"`).

2. `GET /health` — Health check endpoint. Returns:
   - HTTP 200 with body `{"status": "healthy"}` when the server is healthy.
   - The server must support a mechanism to toggle health status. Create a file-based toggle: if the file `/app/backend/unhealthy-<PORT>` exists (e.g., `/app/backend/unhealthy-3001`), the health endpoint returns HTTP 503 with body `{"status": "unhealthy"}`. Otherwise it returns HTTP 200.

3. All responses must include the header `Content-Type: application/json`.

Create a startup script `/app/start_backends.sh` (executable, bash) that starts all three backend servers (ports 3001, 3002, 3003) in the background and writes their PIDs to `/app/backend/pids.txt` (one PID per line, 3 lines total).

Create a stop script `/app/stop_backends.sh` (executable, bash) that reads `/app/backend/pids.txt` and kills all backend processes.

### NGINX Configuration

Create the NGINX configuration file at `/app/nginx/nginx.conf`. Requirements:

1. NGINX listens on port 8080.
2. Define an `upstream` block named `backend_servers` containing the three backend servers (127.0.0.1:3001, 127.0.0.1:3002, 127.0.0.1:3003).
3. Use `least_conn` load balancing method.
4. For `location /`, proxy requests to the `backend_servers` upstream. Include the following proxy headers:
   - `X-Real-IP` set to the client's remote address
   - `X-Forwarded-For` set to the proxy add forwarded-for value
   - `Host` set to the original host header
5. For `location /health`, proxy requests to the `backend_servers` upstream.
6. Configure `proxy_next_upstream` to retry on `error`, `timeout`, and `http_503` so that requests are automatically routed away from unhealthy backends.
7. Set `proxy_connect_timeout` to 2 seconds and `proxy_read_timeout` to 5 seconds.
8. Write access logs to `/app/nginx/access.log` and error logs to `/app/nginx/error.log`.
9. The configuration must be a complete, standalone NGINX config (including `events` block, `worker_processes`, `pid` directive set to `/app/nginx/nginx.pid`, etc.) so it can be started with `nginx -c /app/nginx/nginx.conf`.

Create a script `/app/start_nginx.sh` (executable, bash) that starts NGINX using the configuration at `/app/nginx/nginx.conf` (with `-c` flag using the absolute path). It must create the `/app/nginx/` directory if it doesn't exist.

Create a script `/app/stop_nginx.sh` (executable, bash) that stops the NGINX process gracefully.

### Directory Structure

```
/app/
├── backend/
│   └── server.js
├── nginx/
│   └── nginx.conf
├── start_backends.sh
├── stop_backends.sh
├── start_nginx.sh
└── stop_nginx.sh
```

### Functional Requirements

1. When all three backends are running and healthy, requests to `http://localhost:8080/` must return a valid JSON response from one of the backends and HTTP status 200.
2. When one backend is marked unhealthy (by creating its unhealthy toggle file), subsequent requests to `http://localhost:8080/` must still succeed (HTTP 200) by routing to healthy backends via `proxy_next_upstream`.
3. Requests to `http://localhost:8080/health` must proxy to a backend's `/health` endpoint.
4. Load balancing must distribute requests across multiple healthy backends (not always the same one). Making 10+ requests should show responses from at least 2 different backends.
5. If a backend process is killed entirely, NGINX must failover to remaining backends transparently.
