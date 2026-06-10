## Nginx-Based Reverse Proxy with SSL Termination

Set up Nginx as a reverse proxy that routes traffic to two backend services based on URL path, with SSL termination using a self-signed certificate.

### Technical Requirements

- OS packages: Nginx
- Backend services: two simple HTTP servers (Python, Node.js, or any lightweight approach)
- SSL: self-signed certificate (simulating Let's Encrypt)

### Backend Services

1. **Service A** — listens on `127.0.0.1:8080`
   - Responds to HTTP GET requests with a plain-text body: `Service A is running`

2. **Service B** — listens on `127.0.0.1:8081`
   - Responds to HTTP GET requests with a plain-text body: `Service B is running`

Provide startup scripts or systemd units so both services can be launched. Place backend service source files under `/app/backends/`.

- `/app/backends/service_a.py` (or equivalent) — Service A
- `/app/backends/service_b.py` (or equivalent) — Service B
- `/app/backends/start_backends.sh` — a single shell script that starts both backend services in the background

`start_backends.sh` must be executable (`chmod +x`) and, when run, leave both services listening and ready to accept connections.

### SSL Certificate

Generate a self-signed certificate and private key:

- Certificate path: `/etc/nginx/ssl/server.crt`
- Private key path: `/etc/nginx/ssl/server.key`
- Common Name (CN): `localhost`
- Validity: at least 365 days

### Nginx Configuration

Place the main site configuration at `/etc/nginx/sites-available/reverse_proxy.conf` and symlink it to `/etc/nginx/sites-enabled/reverse_proxy.conf`.

The configuration must satisfy:

| Requirement | Detail |
|---|---|
| Listen (HTTPS) | Port `443` with SSL enabled |
| Listen (HTTP) | Port `80`, redirect all HTTP requests to HTTPS (301) |
| `server_name` | `localhost` |
| Path `/service_a/` | Proxy to `http://127.0.0.1:8080/` |
| Path `/service_b/` | Proxy to `http://127.0.0.1:8081/` |
| Proxy headers | Set `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto` headers on proxied requests |
| Root path `/` | Serve a static HTML landing page |

### Landing Page

Create `/app/index.html` and configure Nginx to serve it at the root path `/`. The page must contain:

- An `<a>` link with `href="/service_a/"` containing the text `Service A`
- An `<a>` link with `href="/service_b/"` containing the text `Service B`

### Final State

After all setup is complete:

1. Both backend services are running (ports 8080 and 8081 responding).
2. Nginx is running with the configuration loaded (`nginx -t` passes).
3. `curl -k https://localhost/service_a/` returns a response body containing `Service A is running`.
4. `curl -k https://localhost/service_b/` returns a response body containing `Service B is running`.
5. `curl -k https://localhost/` returns HTML containing both service links.
6. `curl -I http://localhost/` returns a `301` redirect to HTTPS.
