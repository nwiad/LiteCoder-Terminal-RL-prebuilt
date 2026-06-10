## Containerized Multi-Service Web App with Nginx Reverse Proxy

Deploy a multi-container web application using Docker Compose, with Nginx as a reverse proxy routing requests to three backend services based on URL paths.

### Technical Requirements

- Language: Python 3 (Flask) for auth-svc and data-svc
- Orchestration: Docker Compose (version 3+)
- Reverse Proxy: Nginx
- Working directory: /app

### Project Structure

Create the following directory layout under /app:

```
/app/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── auth-svc/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── data-svc/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── static-svc/
    ├── Dockerfile
    └── html/
        └── index.html
```

### Service Specifications

**1. auth-svc (Authentication Service)**

- Flask app listening on port 5000 inside its container.
- `POST /auth/login` — accepts JSON body `{"username": "<string>", "password": "<string>"}`. If username is `admin` and password is `secret`, return HTTP 200 with JSON `{"token": "<any non-empty string>"}`. Otherwise return HTTP 401 with JSON `{"error": "Invalid credentials"}`.
- `GET /auth/health` — return HTTP 200 with JSON `{"status": "ok", "service": "auth-svc"}`.

**2. data-svc (Data Processing Service)**

- Flask app listening on port 5001 inside its container.
- `POST /data/process` — accepts JSON body `{"numbers": [<list of numbers>]}`. Return HTTP 200 with JSON `{"sum": <sum>, "count": <count>, "average": <average>}`. The `average` should be a float. If `numbers` is empty, return `{"sum": 0, "count": 0, "average": 0}`. If the request body is missing the `numbers` field or it is not a list, return HTTP 400 with JSON `{"error": "Invalid input"}`.
- `GET /data/health` — return HTTP 200 with JSON `{"status": "ok", "service": "data-svc"}`.

**3. static-svc (Static File Service)**

- Serve static files using Nginx (or any lightweight HTTP server) listening on port 80 inside its container.
- `GET /static/` should serve `index.html`.
- The `index.html` file must contain the text `Welcome to Static Service` somewhere in the body.

### Nginx Reverse Proxy Configuration

- Nginx listens on port 80 inside its container.
- The Nginx container's port 80 must be mapped to host port 8080 in docker-compose.yml.
- Routing rules:
  - Requests to `/auth/` are proxied to auth-svc on port 5000.
  - Requests to `/data/` are proxied to data-svc on port 5001.
  - Requests to `/static/` are proxied to static-svc on port 80.

### Docker Compose Requirements

- The file `/app/docker-compose.yml` must define at least four services: `nginx`, `auth-svc`, `data-svc`, `static-svc`.
- All services must be on the same Docker network so they can communicate by service name.
- The only port exposed to the host is `8080:80` on the nginx service.
- Running `docker compose up --build -d` from /app must start all services successfully.

### Verification Endpoints (via host port 8080)

After `docker compose up`, the following requests must succeed:

1. `GET http://localhost:8080/auth/health` → 200, JSON with `"service": "auth-svc"`
2. `POST http://localhost:8080/auth/login` with `{"username":"admin","password":"secret"}` → 200, JSON containing `"token"`
3. `POST http://localhost:8080/auth/login` with `{"username":"wrong","password":"wrong"}` → 401
4. `GET http://localhost:8080/data/health` → 200, JSON with `"service": "data-svc"`
5. `POST http://localhost:8080/data/process` with `{"numbers":[1,2,3]}` → 200, JSON with `"sum":6, "count":3, "average":2.0`
6. `POST http://localhost:8080/data/process` with `{}` → 400
7. `GET http://localhost:8080/static/` → 200, body contains `Welcome to Static Service`
