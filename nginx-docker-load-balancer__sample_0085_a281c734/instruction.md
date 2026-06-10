## Multi-Server Load Balancing with Nginx and Docker Compose

Set up a multi-container web application using Docker Compose where Nginx acts as a load balancer distributing traffic across multiple backend Node.js application instances.

### Technical Requirements

- Language/Runtime: Node.js (no external npm dependencies allowed; use only built-in `http` and `os` modules)
- Containerization: Docker and Docker Compose
- Load Balancer: Nginx
- All project files must be created under `/app/`

### Project Structure

```
/app/
├── app/
│   ├── server.js
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
└── docker-compose.yml
```

### Node.js Application (`/app/app/server.js`)

- Create an HTTP server listening on port `3000`
- For any request, respond with a JSON object containing exactly these fields:
  - `hostname`: the container's hostname (from `os.hostname()`)
  - `timestamp`: current ISO 8601 timestamp (from `new Date().toISOString()`)
  - `message`: the string `"Hello from backend"`
- Response must have `Content-Type: application/json` header
- HTTP status code: `200`

Example response:
```json
{
  "hostname": "abc123def",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "message": "Hello from backend"
}
```

### Dockerfile (`/app/app/Dockerfile`)

- Use `node:18-alpine` as the base image
- Set working directory to `/usr/src/app`
- Copy `server.js` into the container
- Expose port `3000`
- Start the application with `node server.js`

### Docker Compose (`/app/docker-compose.yml`)

- Define two services: `app` and `nginx`
- The `app` service:
  - Build from `./app` directory
  - Deploy exactly **3 replicas**
  - Expose port `3000` (internal only, not published to host)
- The `nginx` service:
  - Use the `nginx:alpine` image
  - Mount `./nginx/nginx.conf` to `/etc/nginx/nginx.conf` as a read-only bind mount
  - Map host port `8080` to container port `80`
  - Must depend on the `app` service

### Nginx Configuration (`/app/nginx/nginx.conf`)

- Define an `upstream` block named `backend` that references the `app` service on port `3000` using Docker Compose DNS resolution
- Use `round-robin` load balancing (Nginx default)
- Define a `server` block listening on port `80`
- The `location /` block must proxy requests to the `backend` upstream
- Include `proxy_set_header Host $host` and `proxy_set_header X-Real-IP $remote_addr` headers in the proxy configuration

### Verification

After running `docker compose up -d --build` from `/app/`:
1. All containers (3 app replicas + 1 nginx) should be running
2. HTTP requests to `http://localhost:8080/` must return valid JSON with the three required fields (`hostname`, `timestamp`, `message`)
3. Multiple sequential requests to `http://localhost:8080/` should show different `hostname` values, demonstrating load balancing across replicas
