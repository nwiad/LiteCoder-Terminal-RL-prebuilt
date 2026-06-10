## Multi-site WordPress with CDN and SSL via Docker Compose

Set up a fully Dockerized multi-site WordPress platform with an Nginx reverse proxy (SSL termination, rate-limiting), a CDN container for static assets, and a MySQL backend — all orchestrated by a single `docker-compose.yml`.

### Technical Requirements

- **Language / Tools:** Docker, Docker Compose, Nginx, WordPress, MySQL
- **Working directory:** `/app`
- **Primary file:** `/app/docker-compose.yml`

### Docker Compose Services

The `docker-compose.yml` must define exactly these service names:

| Service | Image / Base | Exposed Host Port |
|---|---|---|
| `reverse-proxy` | Nginx | `443` (HTTPS), `80` (HTTP, redirect only) |
| `wordpress` | WordPress (official image) | None (internal only) |
| `db` | MySQL 5.7 or 8.x | None (internal only) |
| `cdn` | Nginx | None (reached via reverse-proxy) |

### Network Topology

1. Create a Docker network named `frontend` — only `reverse-proxy` and `cdn` are attached.
2. Create a Docker network named `backend` — `reverse-proxy`, `wordpress`, `cdn`, and `db` are attached.
3. The `wordpress` and `db` containers must NOT be directly reachable from the Docker host; only the `reverse-proxy` container may publish ports to the host.

### SSL Configuration

- The `reverse-proxy` must terminate TLS using a self-signed certificate.
- Store the certificate and key at these paths inside the reverse-proxy container: `/etc/nginx/ssl/selfsigned.crt` and `/etc/nginx/ssl/selfsigned.key`.
- All plain HTTP requests on port 80 must return a `301` redirect to the HTTPS equivalent.

### Nginx Reverse Proxy Configuration

- Place the Nginx config file(s) for the reverse proxy at `/app/nginx/reverse-proxy/default.conf` (mounted into the container).
- Proxy HTTPS traffic to the `wordpress` service on port 80.
- Enable rate-limiting: **10 requests/second per client IP**, burst of **20**, with `nodelay`.
- Log rate-limited (status 503) requests to `/var/log/nginx/rate-limit.log` inside the `reverse-proxy` container.

### WordPress Multisite

- Enable WordPress multisite in **sub-directory** mode (not sub-domain).
- After the platform is up, the WordPress instance must be configured so that multisite is active. The `wp-config.php` inside the WordPress container must contain `define('WP_ALLOW_MULTISITE', true);` and `define('MULTISITE', true);`.

### CDN Container

- The CDN Nginx container must serve WordPress static files (wp-content: themes, plugins, uploads).
- Place the CDN Nginx config at `/app/nginx/cdn/default.conf`.
- The CDN must be accessible through the reverse proxy at the path prefix `/cdn/` over HTTPS (e.g., `https://localhost/cdn/`).
- The CDN container must share a Docker volume named `wp-content` with the `wordpress` container to access static files.

### README

- Create `/app/README.md` containing:
  1. **Architecture** — a text-based diagram showing how containers, networks, and volumes connect.
  2. **Testing** — step-by-step instructions to verify SSL, CDN, multisite, and rate-limiting.
  3. **Curl Commands** — copy-paste `curl` commands that demonstrate:
     - HTTPS access works (and HTTP redirects to HTTPS).
     - Static assets are served through the `/cdn/` path.
     - Rate-limiting returns HTTP 503 when exceeded.

### Lifecycle

- Running `docker-compose up -d` from `/app` must bring the entire platform up with no manual steps.
- Provide a script `/app/cleanup.sh` that stops and removes all containers, networks, and volumes created by this project.
