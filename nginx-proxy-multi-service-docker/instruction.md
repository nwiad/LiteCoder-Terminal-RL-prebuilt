## Containerized Multi-Service Web Application with Nginx Proxy

Create a multi-container web application using Docker Compose. Nginx acts as a reverse proxy, routing traffic to three backend services based on URL paths: a static website, a Node.js Express API, and a Python Flask API.

### Project Structure

All files must be created under `/app/` with the following layout:

```
/app/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── static-site/
│   ├── Dockerfile
│   └── index.html
├── node-api/
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
└── flask-api/
    ├── Dockerfile
    ├── requirements.txt
    └── app.py
```

### Technical Requirements

- Docker Compose file version: `"3"` (or compatible)
- All services must be defined in a single `docker-compose.yml`
- Nginx must be the only service exposing a port to the host: **port 8080** mapped to container port 80
- The three backend services must NOT publish ports to the host directly; they communicate with Nginx via the internal Docker network only

### Service Specifications

**1. Static Site (`static-site`)**
- Serves a static HTML page via a lightweight HTTP server (e.g., Nginx, Python http.server, or similar)
- The container listens internally on port **80**
- `/app/static-site/index.html` must contain:
  - An `<h1>` element with the exact text: `Welcome to the Multi-Service App`
  - A `<p>` element with id `timestamp`

**2. Node.js API (`node-api`)**
- Built with Express.js
- The container listens internally on port **3000**
- Exposes a `GET /` endpoint that returns JSON with **at least** these fields:
  - `service` (string): must be `"node-api"`
  - `timestamp` (string): current ISO 8601 timestamp
  - `hostname` (string): the container hostname
- Response `Content-Type` must be `application/json`

**3. Flask API (`flask-api`)**
- Built with Flask
- The container listens internally on port **5000**
- Exposes a `GET /` endpoint that returns JSON with **at least** these fields:
  - `service` (string): must be `"flask-api"`
  - `timestamp` (string): current ISO 8601 timestamp
  - `python_version` (string): the running Python version
- Response `Content-Type` must be `application/json`

### Nginx Routing Rules

Configure Nginx in `/app/nginx/nginx.conf` with the following location-based routing:

| URL Path Prefix | Upstream Service | Behavior |
|---|---|---|
| `/` | `static-site:80` | Serve the static website (exact `/` or static assets) |
| `/api/node/` | `node-api:3000` | Proxy to Node.js API, stripping the `/api/node` prefix |
| `/api/flask/` | `flask-api:5000` | Proxy to Flask API, stripping the `/api/flask` prefix |

After `docker compose up -d` (or `docker-compose up -d`), the following requests through the host must succeed:

- `curl http://localhost:8080/` → returns the static HTML page containing `Welcome to the Multi-Service App`
- `curl http://localhost:8080/api/node/` → returns JSON with `"service": "node-api"`
- `curl http://localhost:8080/api/flask/` → returns JSON with `"service": "flask-api"`

### Dockerfiles

- Each service directory must contain its own `Dockerfile`
- `static-site/Dockerfile`: use a lightweight base image to serve static files
- `node-api/Dockerfile`: use a Node.js base image, install dependencies via `npm install`, and start the server
- `flask-api/Dockerfile`: use a Python base image, install dependencies via `pip install`, and start the Flask app

### Validation Criteria

1. `docker compose up -d` from `/app/` starts all four containers (nginx, static-site, node-api, flask-api) successfully
2. All containers reach a running state
3. `http://localhost:8080/` returns HTML containing `Welcome to the Multi-Service App`
4. `http://localhost:8080/api/node/` returns valid JSON with a `service` field equal to `"node-api"`
5. `http://localhost:8080/api/flask/` returns valid JSON with a `service` field equal to `"flask-api"`
6. Only port 8080 is published to the host
