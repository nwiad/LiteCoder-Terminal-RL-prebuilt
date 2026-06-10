## HTTP Load Balancer with Dynamic Backend Discovery

Build a Python-based HTTP load balancer that dynamically discovers backend servers from a registry file, performs health checks, and routes requests using round-robin balancing.

### Technical Requirements

- Language: Python 3.x
- Use `asyncio` and `aiohttp` for the load balancer
- Use `Flask` for backend services
- Input config: `/app/config.json`
- Backend registry: `/app/registry.json`
- Output metrics: `/app/output.json`

### Input Specification

`/app/config.json` defines the load balancer configuration:

```json
{
  "load_balancer": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "health_check": {
    "interval_seconds": 5,
    "timeout_seconds": 2,
    "unhealthy_threshold": 3
  },
  "registry_poll_interval_seconds": 3
}
```

`/app/registry.json` is a dynamic file that lists available backend servers. The load balancer must poll this file periodically (per `registry_poll_interval_seconds`) to discover new backends or remove deregistered ones:

```json
{
  "services": [
    {"id": "backend-1", "host": "127.0.0.1", "port": 5001},
    {"id": "backend-2", "host": "127.0.0.1", "port": 5002},
    {"id": "backend-3", "host": "127.0.0.1", "port": 5003}
  ]
}
```

### Components

1. **Backend Service** (`/app/backend.py`): A Flask application that:
   - Accepts a `--port` command-line argument to specify the listening port
   - Exposes `GET /` returning JSON `{"service_id": "<id>", "port": <port>}`
   - Exposes `GET /health` returning HTTP 200 with `{"status": "healthy"}`

2. **Load Balancer** (`/app/load_balancer.py`): An asyncio/aiohttp application that:
   - Reads `/app/config.json` on startup
   - Polls `/app/registry.json` at the configured interval to discover/remove backends
   - Performs periodic health checks on each registered backend by calling `GET /health`
   - Marks a backend as unhealthy after consecutive failures reaching `unhealthy_threshold`
   - Routes incoming HTTP requests only to healthy backends using round-robin
   - Exposes `GET /status` returning JSON with current backend states (see output format)
   - Exposes `GET /metrics` returning JSON with collected metrics (see output format)
   - Proxies all other requests to healthy backends

3. **Metrics Writer** (integrated in load balancer): On receiving `SIGTERM` or `SIGINT`, or when `GET /metrics/dump` is called, writes the current metrics snapshot to `/app/output.json`.

### Output Specification

`/app/output.json` must have this structure:

```json
{
  "total_requests": 0,
  "successful_requests": 0,
  "failed_requests": 0,
  "backends": {
    "backend-1": {
      "host": "127.0.0.1",
      "port": 5001,
      "healthy": true,
      "requests_served": 0,
      "consecutive_failures": 0
    }
  },
  "active_backends": 2,
  "total_backends": 3
}
```

The `/status` endpoint must return:

```json
{
  "backends": [
    {"id": "backend-1", "host": "127.0.0.1", "port": 5001, "healthy": true},
    {"id": "backend-2", "host": "127.0.0.1", "port": 5002, "healthy": false}
  ]
}
```

### Behavior Requirements

- When a new backend appears in `registry.json`, the load balancer must detect it within one poll interval and begin health-checking it. A newly discovered backend is assumed healthy until a health check fails.
- When a backend is removed from `registry.json`, the load balancer must stop routing to it within one poll interval.
- Round-robin must distribute requests evenly across healthy backends only, skipping unhealthy ones.
- If all backends are unhealthy, the load balancer must return HTTP 503 with `{"error": "no healthy backends available"}`.
- If `registry.json` is missing or malformed, the load balancer must retain the last known good backend list and log a warning.
- Health checks must run concurrently (not sequentially) for all backends.
