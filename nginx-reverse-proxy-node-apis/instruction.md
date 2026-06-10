## Host Multiple Node.js APIs with Nginx Reverse Proxy

Configure Nginx as a reverse proxy to serve three Node.js API microservices on different sub-paths of a single domain (port 80).

### Technical Requirements

- **OS:** Ubuntu (container environment)
- **Stack:** Node.js, npm, Nginx
- **All three Node.js services and Nginx must be running** when the task is complete.

### Node.js API Services

Create three separate Node.js HTTP services. Each service must listen on its assigned port and respond to `GET /` requests with a JSON response (Content-Type: `application/json`).

| Service | Port | Response Body |
|---------|------|---------------|
| Service 1 | 3001 | `{"service": "api1", "port": 3001, "status": "ok"}` |
| Service 2 | 3002 | `{"service": "api2", "port": 3002, "status": "ok"}` |
| Service 3 | 3003 | `{"service": "api3", "port": 3003, "status": "ok"}` |

Each service must return HTTP status code `200` for `GET` requests to its root path.

### Nginx Reverse Proxy Configuration

Nginx must listen on port `80` and route requests based on URL sub-paths to the corresponding Node.js service:

| URL Path Prefix | Proxied To |
|-----------------|------------|
| `/api1/` | `http://localhost:3001/` |
| `/api2/` | `http://localhost:3002/` |
| `/api3/` | `http://localhost:3003/` |

Requests to each sub-path must be forwarded to the root (`/`) of the corresponding backend service. For example, a request to `http://localhost/api1/` must be proxied to `http://localhost:3001/` and return the JSON response from Service 1.

### Verification

After setup, the following requests must all succeed and return the correct JSON:

- `curl http://localhost/api1/` → `{"service": "api1", "port": 3001, "status": "ok"}`
- `curl http://localhost/api2/` → `{"service": "api2", "port": 3002, "status": "ok"}`
- `curl http://localhost/api3/` → `{"service": "api3", "port": 3003, "status": "ok"}`

Each response must have HTTP status `200` and Content-Type `application/json`.
