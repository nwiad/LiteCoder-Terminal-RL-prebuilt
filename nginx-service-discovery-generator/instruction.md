## Containerized Service Discovery & Nginx Load Balancer Config Generator

Build a Python-based service discovery system that reads container metadata, generates dynamic Nginx upstream configurations, and supports hot-reload signaling — simulating a zero-downtime load balancer for Docker microservices.

### Technical Requirements

- Language: Python 3.x (standard library only)
- Input file: `/app/containers.json`
- Output files:
  - `/app/nginx.conf` — generated Nginx configuration
  - `/app/discovery_result.json` — structured discovery output
  - `/app/reload_status.json` — reload operation status

### Input Specification

`/app/containers.json` contains an array of container objects. Each object has:

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `id`          | string  | Container ID (12-char hex string)                |
| `name`        | string  | Container name                                   |
| `service`     | string  | Service group name (e.g., `"web"`, `"api"`)      |
| `ip`          | string  | Container IP address                             |
| `port`        | integer | Container port number                            |
| `status`      | string  | One of: `"running"`, `"stopped"`, `"paused"`     |
| `health`      | string  | One of: `"healthy"`, `"unhealthy"`, `"starting"` |
| `weight`      | integer | Load balancing weight (1–10)                     |

Example input:
```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "web-1",
    "service": "web",
    "ip": "172.18.0.2",
    "port": 8080,
    "status": "running",
    "health": "healthy",
    "weight": 5
  },
  {
    "id": "b2c3d4e5f6a1",
    "name": "web-2",
    "service": "web",
    "ip": "172.18.0.3",
    "port": 8080,
    "status": "running",
    "health": "unhealthy",
    "weight": 3
  },
  {
    "id": "c3d4e5f6a1b2",
    "name": "api-1",
    "service": "api",
    "ip": "172.18.0.4",
    "port": 3000,
    "status": "stopped",
    "health": "healthy",
    "weight": 7
  }
]
```

### Task 1: Service Discovery (`discover.py`)

Create `/app/discover.py` that reads `/app/containers.json` and writes `/app/discovery_result.json`.

Discovery rules:
- Only include containers where `status` is `"running"` AND `health` is `"healthy"`.
- Group eligible containers by their `service` field.
- Sort services alphabetically by service name.
- Within each service group, sort containers by `name` alphabetically.

Output format for `/app/discovery_result.json`:
```json
{
  "services": {
    "api": {
      "endpoints": [
        {"id": "x1y2z3a4b5c6", "name": "api-1", "address": "172.18.0.4:3000", "weight": 7}
      ],
      "count": 1
    },
    "web": {
      "endpoints": [
        {"id": "a1b2c3d4e5f6", "name": "web-1", "address": "172.18.0.2:8080", "weight": 5}
      ],
      "count": 1
    }
  },
  "total_healthy": 2,
  "total_containers": 5,
  "excluded": [
    {"id": "b2c3d4e5f6a1", "name": "web-2", "reason": "unhealthy"},
    {"id": "c3d4e5f6a1b2", "name": "api-2", "reason": "stopped"}
  ]
}
```

The `excluded` array lists all containers not included, sorted by `name` alphabetically. The `reason` field should be:
- `"stopped"` if `status` is not `"running"` (check status first)
- `"unhealthy"` if `health` is not `"healthy"`
- `"paused"` if `status` is `"paused"` (check status first)

`total_containers` is the total number of containers in the input. `total_healthy` is the number of containers that passed both filters.

### Task 2: Nginx Config Generation (`generate_config.py`)

Create `/app/generate_config.py` that reads `/app/discovery_result.json` and writes `/app/nginx.conf`.

The generated Nginx config must follow this exact structure:

```
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    upstream <service_name> {
        server <ip>:<port> weight=<weight>;
        server <ip>:<port> weight=<weight>;
    }

    server {
        listen 80;

        location /<service_name>/ {
            proxy_pass http://<service_name>/;
        }
    }
}
```

Rules:
- Generate one `upstream` block per service, in alphabetical order by service name.
- Within each upstream block, list servers in the same order as in `discovery_result.json`.
- Generate one `location` block per service inside a single `server` block, in alphabetical order.
- If a service has zero endpoints, skip it entirely (no upstream, no location).
- Use exactly 4-space indentation throughout.
- End the file with a single trailing newline.

### Task 3: Reload Status (`reload.py`)

Create `/app/reload.py` that reads both `/app/discovery_result.json` and `/app/nginx.conf`, then writes `/app/reload_status.json`.

This script simulates a hot-reload check. It must:
1. Verify that `/app/nginx.conf` exists and is non-empty.
2. Verify that every service in `discovery_result.json` (with count > 0) has a corresponding `upstream` block in `nginx.conf`.
3. Verify that every endpoint address in `discovery_result.json` appears as a `server` line in `nginx.conf`.

Output format for `/app/reload_status.json`:
```json
{
  "config_valid": true,
  "services_matched": ["api", "web"],
  "missing_services": [],
  "missing_endpoints": [],
  "reload_command": "nginx -s reload",
  "status": "ready"
}
```

- `config_valid`: `true` only if all services and endpoints are found in the config.
- `services_matched`: alphabetically sorted list of services found in both files.
- `missing_services`: alphabetically sorted list of services in discovery but not in nginx config.
- `missing_endpoints`: list of `"ip:port"` strings found in discovery but missing from nginx config, sorted alphabetically.
- `status`: `"ready"` if `config_valid` is `true`, otherwise `"error"`.

### Edge Cases

- If `/app/containers.json` is an empty array `[]`, all output files should still be generated with empty/zero values.
- If all containers are excluded, `nginx.conf` should contain only the base structure (worker_processes, events, http with an empty server block listening on port 80 with no location blocks).
- Container entries with missing or null fields should be excluded and listed in the `excluded` array with reason `"invalid"`.
