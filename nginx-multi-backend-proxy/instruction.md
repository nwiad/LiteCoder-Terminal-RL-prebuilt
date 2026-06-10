Set up an Nginx reverse proxy that routes requests to three backend services based on URL path, with each backend generating JSON responses.

## Technical Requirements

- **Nginx** as the reverse proxy, listening on port **8080**
- **Python Flask** backend on port **5001**
- **Node.js Express** backend on port **5002**
- **Go** (net/http) backend on port **5003**
- All services run on `localhost`

## Backend Services

### Flask API (port 5001)
- Source file: `/app/flask_app.py`
- `GET /api/flask/health` → returns JSON: `{"service": "flask", "status": "healthy"}`
- `GET /api/flask/echo?message=<text>` → returns JSON: `{"service": "flask", "echo": "<text>"}` where `<text>` is the value of the `message` query parameter. If the `message` parameter is missing, return `{"service": "flask", "echo": ""}`.

### Express API (port 5002)
- Source file: `/app/express_app.js`
- `GET /api/express/health` → returns JSON: `{"service": "express", "status": "healthy"}`
- `GET /api/express/echo?message=<text>` → returns JSON: `{"service": "express", "echo": "<text>"}` where `<text>` is the value of the `message` query parameter. If the `message` parameter is missing, return `{"service": "express", "echo": ""}`.

### Go API (port 5003)
- Source file: `/app/go_app.go`
- `GET /api/go/health` → returns JSON: `{"service": "go", "status": "healthy"}`
- `GET /api/go/echo?message=<text>` → returns JSON: `{"service": "go", "echo": "<text>"}` where `<text>` is the value of the `message` query parameter. If the `message` parameter is missing, return `{"service": "go", "echo": ""}`.

All backend responses must have `Content-Type: application/json`.

## Nginx Configuration

- Configuration file: `/app/nginx.conf`
- Nginx listens on port **8080**
- Routing rules (path-based proxying):
  - Requests to `/api/flask/` → proxy to `http://127.0.0.1:5001`
  - Requests to `/api/express/` → proxy to `http://127.0.0.1:5002`
  - Requests to `/api/go/` → proxy to `http://127.0.0.1:5003`
- The original request URI (including path and query string) must be preserved when proxying.

## Startup Script

- Create `/app/start.sh` — a bash script that starts all four processes (three backends + Nginx).
- The script must be executable (`chmod +x`).
- After running `bash /app/start.sh`, all services must be reachable through Nginx on port 8080.
- The script should start processes in the background and return (not block).

## Verification

After startup, the following curl commands through the Nginx proxy (port 8080) must succeed:

```
curl http://localhost:8080/api/flask/health
curl http://localhost:8080/api/express/health
curl http://localhost:8080/api/go/health
curl "http://localhost:8080/api/flask/echo?message=hello"
curl "http://localhost:8080/api/express/echo?message=world"
curl "http://localhost:8080/api/go/echo?message=test"
```

Each must return valid JSON with the correct `service`, `status`/`echo` fields as specified above.
