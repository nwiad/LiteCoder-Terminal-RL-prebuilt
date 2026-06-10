## Custom HTTP Load Balancer with Application-Level Health Checks

Implement a Python-based HTTP load balancer that distributes traffic across multiple backend servers using round-robin scheduling, performs application-level health checks, and dynamically removes/re-adds servers based on health status.

### Technical Requirements

- Language: Python 3.x (standard library only; no third-party packages)
- Load balancer entry point: `/app/load_balancer.py`
- Configuration file: `/app/config.json`
- Runtime status output: `/app/status.json`

### Configuration (`/app/config.json`)

The load balancer reads its configuration from this JSON file at startup:

```json
{
  "listen_port": 8080,
  "backends": [
    {"host": "127.0.0.1", "port": 8001},
    {"host": "127.0.0.1", "port": 8002},
    {"host": "127.0.0.1", "port": 8003}
  ],
  "health_check": {
    "path": "/health",
    "interval_seconds": 5,
    "timeout_seconds": 2,
    "unhealthy_threshold": 3,
    "healthy_threshold": 1
  }
}
```

- `listen_port`: The port the load balancer listens on.
- `backends`: List of backend servers. Each has `host` and `port`.
- `health_check.path`: The endpoint to probe on each backend.
- `health_check.interval_seconds`: Time between consecutive health checks for each backend.
- `health_check.timeout_seconds`: Maximum time to wait for a health check response.
- `health_check.unhealthy_threshold`: Number of consecutive failed health checks before marking a server as unhealthy.
- `health_check.healthy_threshold`: Number of consecutive successful health checks before marking a server as healthy again.

### Load Balancer Behavior

1. **Proxying**: The load balancer accepts HTTP requests on `listen_port` and forwards them to healthy backend servers. It returns the backend's response status code and body to the client.

2. **Round-Robin**: Requests are distributed to healthy backends in strict round-robin order. When a server is removed from or re-added to the healthy pool, round-robin continues from the next healthy server in the original backend list order.

3. **Health Checks**: A background process periodically sends `GET` requests to each backend's health check path. A health check is considered successful only if the backend responds with HTTP 200 and the response body is valid JSON containing `{"status": "ok"}` (the `status` field must equal `"ok"`). Any other response, timeout, or connection error counts as a failure.

4. **Unhealthy Removal**: After `unhealthy_threshold` consecutive health check failures, the backend is marked unhealthy and excluded from receiving traffic.

5. **Healthy Re-addition**: After `healthy_threshold` consecutive successful health checks, a previously unhealthy backend is marked healthy and re-added to the rotation.

6. **No Healthy Backends**: If all backends are unhealthy, the load balancer responds with HTTP 503 and the JSON body `{"error": "no healthy backends"}`.

### Load Balancer Endpoints

In addition to proxying, the load balancer itself exposes:

- `GET /status` — Returns a JSON object describing current state. This response is served directly by the load balancer (not proxied). The format:

```json
{
  "backends": [
    {
      "host": "127.0.0.1",
      "port": 8001,
      "healthy": true,
      "requests_served": 10
    },
    {
      "host": "127.0.0.1",
      "port": 8002,
      "healthy": false,
      "requests_served": 5
    },
    {
      "host": "127.0.0.1",
      "port": 8003,
      "healthy": true,
      "requests_served": 9
    }
  ],
  "total_requests": 24
}
```

- `requests_served`: Number of requests successfully proxied to that backend.
- `total_requests`: Sum of all `requests_served` values.

### Status File (`/app/status.json`)

The load balancer writes the same JSON structure as the `/status` endpoint to `/app/status.json` whenever a health check cycle completes or a request is served. This file must always reflect the latest state.

### Logging

The load balancer prints log lines to stdout with the format:

```
[YYYY-MM-DD HH:MM:SS] EVENT_TYPE message
```

Required `EVENT_TYPE` values:
- `STARTUP` — When the load balancer starts listening.
- `HEALTH_OK` — When a backend passes a health check.
- `HEALTH_FAIL` — When a backend fails a health check.
- `BACKEND_UP` — When a backend transitions from unhealthy to healthy.
- `BACKEND_DOWN` — When a backend transitions from healthy to unhealthy.
- `REQUEST` — When a request is proxied, including the target backend.
- `NO_BACKEND` — When a request is rejected due to no healthy backends.
- `SHUTDOWN` — When the load balancer receives SIGINT or SIGTERM and shuts down gracefully.

### Graceful Shutdown

On receiving `SIGINT` or `SIGTERM`, the load balancer:
1. Stops accepting new connections.
2. Writes the final state to `/app/status.json`.
3. Logs a `SHUTDOWN` event.
4. Exits with code 0.

### Backend Test Servers

Also provide `/app/backend_server.py` — a minimal HTTP server that can be started as:

```
python3 /app/backend_server.py --port PORT
```

This server:
- Responds to `GET /health` with HTTP 200 and body `{"status": "ok"}`.
- Responds to any other request with HTTP 200 and body `{"server_port": PORT}`.
- Accepts an optional `--unhealthy` flag. When started with this flag, the `/health` endpoint returns HTTP 500 and body `{"status": "error"}` instead.
