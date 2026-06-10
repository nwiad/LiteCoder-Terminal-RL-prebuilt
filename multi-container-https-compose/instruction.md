## Multi-Container HTTPS Web Application Stack

Use Docker Compose to orchestrate an Nginx reverse-proxy that terminates TLS, two Node.js app containers, a Redis cache, and a shared network, all behind a self-signed certificate. Everything must be runnable from a single `docker-compose.yml` at `/app/docker-compose.yml`.

### Project Structure

```
/app/
├── docker-compose.yml
├── hello/
│   ├── Dockerfile
│   ├── package.json
│   └── index.js
├── time/
│   ├── Dockerfile
│   ├── package.json
│   └── index.js
└── nginx/
    ├── nginx.conf
    └── certs/
        ├── cert.pem
        └── key.pem
```

### Technical Requirements

- **Language:** Node.js (use `node:18-alpine` or `node:20-alpine` as base image)
- **Compose version:** Docker Compose V2 format
- **Redis image:** `redis:7-alpine` (or compatible `redis:*-alpine`)

### Node.js Applications

**hello service** (`/app/hello/index.js`):
- Listens on port `3000`
- Connects to Redis at host `redis`, port `6379`
- On `GET /hello`, returns JSON: `{"message": "Hello World"}`
- Caches the value in Redis under key `hello:message` with a TTL of 10 seconds
- Content-Type: `application/json`

**time service** (`/app/time/index.js`):
- Listens on port `3000`
- Connects to Redis at host `redis`, port `6379`
- On `GET /time`, returns JSON: `{"time": "<ISO 8601 timestamp>"}`
- The `time` field must be an ISO 8601 string (e.g., `"2025-01-15T12:30:00.000Z"`)
- Caches the value in Redis under key `time:timestamp` with a TTL of 5 seconds
- When a cached value exists and has not expired, the cached timestamp is returned instead of generating a new one
- Content-Type: `application/json`

### Self-Signed Certificate

- Generate a self-signed TLS certificate and private key stored at `/app/nginx/certs/cert.pem` and `/app/nginx/certs/key.pem`
- Valid for 365 days
- Common Name (CN): `localhost`
- The certs directory must be mounted read-only into the Nginx container

### Nginx Configuration (`/app/nginx/nginx.conf`)

- Listen on port `443` with SSL enabled, using the generated certificate and key
- Reverse-proxy requests:
  - Path `/hello` → forwards to the `hello` service on port 3000
  - Path `/time` → forwards to the `time` service on port 3000
- Upstream connections to Node apps use plain HTTP

### Docker Compose (`/app/docker-compose.yml`)

- **Services** (exact service names):
  - `nginx` — builds or uses the official nginx image, mounts `nginx.conf` and `certs/`, exposes port `443` on the host
  - `hello` — builds from `./hello`
  - `time` — builds from `./time`
  - `redis` — uses the Redis Alpine image, no authentication required
- **Network:** All services must be on a single custom bridge network named `app-network`
- The `nginx` service must depend on `hello`, `time`, and `redis`
- Port mapping: host port `443` → container port `443` for the nginx service

### Endpoint Behavior

- `https://localhost/hello` returns `{"message": "Hello World"}` with HTTP 200
- `https://localhost/time` returns `{"time": "<ISO timestamp>"}` with HTTP 200
- Repeated requests to `/time` within 5 seconds return the same cached timestamp
- Repeated requests to `/hello` within 10 seconds return the same cached response
- After the respective TTL expires, the next request produces a fresh value
