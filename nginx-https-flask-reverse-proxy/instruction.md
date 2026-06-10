## Configure Nginx as a Secure HTTPS Reverse Proxy for a Python Flask Application

Set up Nginx as a reverse proxy with SSL/TLS termination to securely serve a Python Flask application running on localhost:5000.

### Flask Application

Create a Flask application at `/app/app.py` with the following requirements:

- The app listens on `0.0.0.0:5000`.
- It exposes at least two routes:
  - `GET /` — returns a JSON response `{"status": "ok", "message": "Hello from Flask"}` with content type `application/json`.
  - `GET /health` — returns a JSON response `{"healthy": true}` with content type `application/json`.
- Install all necessary Python dependencies (Flask, etc.) so the app can run.

### SSL Certificate

Generate a self-signed SSL certificate and key:

- Certificate path: `/etc/nginx/ssl/server.crt`
- Key path: `/etc/nginx/ssl/server.key`
- The certificate must be a valid X.509 PEM-encoded certificate.
- The key must be a PEM-encoded RSA or EC private key.

### Nginx Configuration

Configure Nginx as a reverse proxy at `/etc/nginx/conf.d/flask_proxy.conf` (or modify the appropriate Nginx config) with these requirements:

- Nginx listens on port `443` with SSL enabled.
- SSL is configured using the self-signed certificate and key generated above.
- All requests to `https://localhost/` are proxied to `http://127.0.0.1:5000`.
- The configuration must include the `proxy_pass` directive pointing to the Flask backend.
- The following proxy headers must be set:
  - `proxy_set_header Host $host;`
  - `proxy_set_header X-Real-IP $remote_addr;`
  - `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
  - `proxy_set_header X-Forwarded-Proto $scheme;`
- Nginx must pass its configuration test (`nginx -t` succeeds).
- Nginx service must be running after setup.

### HTTP to HTTPS Redirect (Optional but Recommended)

Configure Nginx to listen on port `80` and redirect all HTTP traffic to HTTPS (port 443).

### Verification

After setup, the following must hold true:

1. The Flask app process is running and responding on `http://127.0.0.1:5000/`.
2. Nginx is running (`systemctl is-active nginx` or equivalent returns active, or the nginx process is running).
3. `nginx -t` reports configuration is valid.
4. `curl -k https://localhost/` returns the JSON `{"status": "ok", "message": "Hello from Flask"}`.
5. `curl -k https://localhost/health` returns the JSON `{"healthy": true}`.
6. The SSL certificate file at `/etc/nginx/ssl/server.crt` is a valid PEM certificate.
7. The Nginx config contains `proxy_pass` directive pointing to `http://127.0.0.1:5000`.
