## Build a REST API Server in Go with Rate Limiting, Structured Logging, and Reverse Proxy Configuration

Build a production-style REST API server in Go with IP-based rate limiting middleware, structured JSON logging, a Caddy reverse proxy configuration, and a Bash test script.

### Technical Requirements

- Language: Go (1.18+)
- Reverse proxy config: Caddyfile format
- Test script: Bash
- All source files placed under `/app/`

### Deliverables

1. **Go API server** — source at `/app/server.go`
2. **Caddy config** — `/app/Caddyfile`
3. **Test script** — `/app/test.sh` (executable)
4. **README** — `/app/README.md`

---

### 1. Go REST API (`/app/server.go`)

The server must listen on port `8080` and implement the following endpoints:

| Endpoint | Method | Response |
|---|---|---|
| `/api/status` | GET | JSON: `{"status":"ok","timestamp":"<RFC3339>"}` |
| `/api/health` | GET | JSON: `{"healthy":true}` |
| Any other path | Any | HTTP 404 with JSON: `{"error":"not found"}` |

Requirements:
- All responses must have `Content-Type: application/json`.
- The `/api/status` `timestamp` field must be a valid RFC 3339 formatted time string.
- The server must implement **IP-based rate limiting middleware** applied to all routes:
  - Maximum **10 requests per second** per source IP.
  - When the limit is exceeded, respond with HTTP `429` and JSON body: `{"error":"rate limit exceeded"}`.
- The server must implement **structured JSON logging** to stdout. Each log line must be a valid JSON object containing at least these fields:
  - `time` — RFC 3339 timestamp
  - `method` — HTTP method
  - `path` — request path
  - `status` — HTTP response status code (integer)
  - `ip` — client IP address
- The server must handle **graceful shutdown** on SIGINT or SIGTERM: stop accepting new connections and finish in-flight requests before exiting.
- The Go program must compile without errors via `go build -o /app/apiserver /app/server.go` (a `go.mod` at `/app/go.mod` is allowed if external modules are used; if so, all dependencies must be fetchable via `go mod tidy`).

### 2. Caddyfile (`/app/Caddyfile`)

Provide a Caddyfile that configures Caddy as a reverse proxy:
- Listen on port `443` for the hostname `api.example.com`.
- Enable automatic HTTPS (TLS) via Let's Encrypt (default Caddy behavior).
- Reverse proxy all requests to `localhost:8080`.
- Include a `rate_limit` directive or ordered configuration that limits each client IP to **10 requests per second** (use Caddy's syntax; the directive may reference a plugin — just ensure the config is syntactically valid Caddyfile format).
- Enable structured JSON access logging to the file path `/var/log/caddy/access.log`.

### 3. Test Script (`/app/test.sh`)

A Bash script that tests the API (assumes the server is running on `localhost:8080`):
- The script must be executable (`chmod +x`).
- It must start with `#!/bin/bash`.
- It must test at minimum:
  - A GET to `/api/status` and verify HTTP 200 and that the response contains `"status":"ok"`.
  - A GET to `/api/health` and verify HTTP 200 and that the response contains `"healthy":true`.
  - A GET to a non-existent path (e.g., `/api/nonexistent`) and verify HTTP 404.
  - A rate-limit burst test: send more than 10 rapid requests to `/api/status` and verify that at least one response returns HTTP 429.
- The script must print `PASS` or `FAIL` for each test case to stdout.
- The script must exit with code `0` if all tests pass, non-zero otherwise.

### 4. README (`/app/README.md`)

A Markdown document that includes:
- A brief description of the project.
- Instructions to build and run the Go server.
- An explanation of the rate limiting strategy.
- Instructions to run the test script.
