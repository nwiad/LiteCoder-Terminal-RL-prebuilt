## Configure Docker Container to Host Flask App with Nginx Reverse Proxy and SSL

Set up a Flask application inside a Docker container, reverse-proxied through Nginx with HTTPS support, using Docker Compose to orchestrate the services. The entire setup must be reproducible and located under `/app`.

### Technical Requirements

- Language/Runtime: Python 3.x (Flask)
- Containerization: Docker, Docker Compose
- Reverse Proxy: Nginx
- SSL: Self-signed certificate (simulating Let's Encrypt workflow)
- Working directory: `/app`

### Required File Structure

All files must be created under `/app`:

```
/app/
├── docker-compose.yml
├── flask_app/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── ssl/
│   ├── cert.pem
│   └── key.pem
└── renew_cert.sh
```

### Flask Application (`/app/flask_app/app.py`)

- Must use Flask framework.
- Must define at least two routes:
  - `GET /` — returns a JSON response: `{"message": "Hello, World!"}` with content type `application/json` and HTTP 200.
  - `GET /health` — returns a JSON response: `{"status": "healthy"}` with content type `application/json` and HTTP 200.
- Must listen on port `5000` inside the container.

### Flask Dependencies (`/app/flask_app/requirements.txt`)

- Must list `flask` as a dependency (at minimum).

### Dockerfile (`/app/flask_app/Dockerfile`)

- Must use a Python base image (e.g., `python:3.x-slim` or similar).
- Must copy the application code into the container.
- Must install dependencies from `requirements.txt`.
- Must expose port `5000`.
- Must define a `CMD` or `ENTRYPOINT` that starts the Flask app.

### Docker Compose (`/app/docker-compose.yml`)

- Must define at least two services:
  - `flask_app` (or `flask` or `web`): builds from `/app/flask_app/Dockerfile`.
  - `nginx`: uses an official `nginx` image.
- The `nginx` service must:
  - Depend on the Flask service.
  - Map host port `443` to container port `443` (HTTPS).
  - Map host port `80` to container port `80` (HTTP).
  - Mount the Nginx config from `/app/nginx/nginx.conf`.
  - Mount the SSL certificates from `/app/ssl/`.
- Must use a shared network or Docker Compose default networking so Nginx can reach the Flask container.

### Nginx Configuration (`/app/nginx/nginx.conf`)

- Must listen on port `80` and redirect all HTTP traffic to HTTPS (port `443`).
- Must listen on port `443` with SSL enabled.
- Must reference SSL certificate at `/etc/nginx/ssl/cert.pem` and key at `/etc/nginx/ssl/key.pem` (inside the container).
- Must proxy pass requests to the Flask application service on port `5000`.
- Must include `proxy_set_header Host $host;` and `proxy_set_header X-Forwarded-Proto $scheme;` directives.

### SSL Certificates (`/app/ssl/`)

- Generate a self-signed certificate and private key:
  - `/app/ssl/cert.pem` — PEM-encoded X.509 certificate.
  - `/app/ssl/key.pem` — PEM-encoded RSA private key.
- The certificate must be valid (parseable as a proper X.509 certificate).

### Certificate Renewal Script (`/app/renew_cert.sh`)

- Must be an executable shell script (shebang line `#!/bin/bash` or `#!/bin/sh`).
- Must contain a `certbot` renewal command (e.g., `certbot renew`).
- Must contain a command to reload or restart the Nginx service/container after renewal.
