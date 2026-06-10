## Task: Docker-Nginx Web Server Configuration

Deploy a containerized Nginx web server with SSL, reverse proxy capabilities, and static content delivery.

## Technical Requirements

- Docker and Docker Compose
- Nginx (Alpine-based image)
- Self-signed SSL certificate
- Static HTML content serving
- Reverse proxy configuration

## Implementation Requirements

### 1. Docker Configuration

Create a `Dockerfile` that:
- Uses Alpine Linux as the base image
- Installs Nginx
- Copies custom Nginx configuration from `/app/nginx.conf`
- Copies SSL certificates from `/app/certs/` directory
- Exposes ports 80 and 443

### 2. SSL Certificate

Generate a self-signed SSL certificate with the following specifications:
- Certificate file: `/app/certs/server.crt`
- Private key file: `/app/certs/server.key`
- Valid for at least 365 days
- Common Name (CN): `localhost`

### 3. Nginx Configuration

Create `/app/nginx.conf` with:
- HTTP to HTTPS redirect (port 80 → 443)
- SSL configuration using the generated certificates
- Static content serving from `/usr/share/nginx/html`
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`
- Gzip compression enabled for text-based content
- Reverse proxy configuration for `/api` path to `http://api-service:3000`
- Rate limiting: maximum 10 requests per second per IP address

### 4. Docker Compose

Create `/app/docker-compose.yml` that defines:
- `web` service: Nginx container built from the Dockerfile
- `api-service` service: Node.js placeholder (use `node:alpine` image with a simple command)
- Port mapping: host port 8080 → container port 443
- Volume mounts for certificates and static content

### 5. Static Content

Create `/app/static/index.html` with:
- Valid HTML5 structure
- Page title: "Welcome to Our Platform"
- At least one heading and one paragraph of content

### 6. Documentation

Create `/app/README.md` containing:
- Brief description of the setup
- Commands to build and start the services
- Command to test HTTPS access using curl
- Command to stop the services

## Output Files

- `/app/Dockerfile`
- `/app/nginx.conf`
- `/app/docker-compose.yml`
- `/app/static/index.html`
- `/app/certs/server.crt`
- `/app/certs/server.key`
- `/app/README.md`

## Validation

The setup should allow:
- Accessing `https://localhost:8080` returns the static HTML page
- HTTP requests to port 8080 are redirected to HTTPS
- Response headers include the configured security headers
- The `/api` path proxies to the backend service
