## Containerized WordPress with HTTPS

Set up a secure, containerized WordPress site served by Nginx reverse proxy on the domain `blog.example.test`, with auto-renewed TLS certificates and wp-admin IP restriction.

### Requirements

1. **Host DNS Entry**
   - Add `127.0.0.1 blog.example.test` to `/etc/hosts`.

2. **Project Directory**
   - All project files must reside under `/app/wordpress/`.

3. **Docker Compose** (`/app/wordpress/docker-compose.yml`)
   - Use Compose file format version `3` (or higher).
   - Define at minimum these four services:
     - `db` — MariaDB (image: `mariadb:10.6` or later). Must set `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD` via environment variables. Data must be persisted using a named volume `db_data`.
     - `wordpress` — WordPress (image: `wordpress:php8.1-fpm` or later FPM variant). Must link to `db` via `WORDPRESS_DB_HOST`, `WORDPRESS_DB_USER`, `WORDPRESS_DB_PASSWORD`, and `WORDPRESS_DB_NAME` environment variables. WordPress files must be persisted using a named volume `wordpress_data`.
     - `nginx` — Nginx (image: `nginx:latest` or pinned stable version). Must expose ports `80` and `443` on the host. Must bind-mount the Nginx config file and the certificate/key directories. Must also mount the `wordpress_data` volume (read-only is acceptable).
     - `certbot` — Certbot (image: `certbot/certbot`). Must share the certificate volume with `nginx` and share a webroot challenge volume with `nginx` for ACME HTTP-01 validation.
   - All four services must be on a shared custom Docker network named `wp_network`.

4. **Nginx Configuration** (`/app/wordpress/nginx.conf`)
   - Listen on port `80` and port `443` with `ssl`.
   - `server_name` must be `blog.example.test`.
   - Port 80 must serve the ACME challenge path `/.well-known/acme-challenge/` from the certbot webroot, and redirect all other HTTP traffic to HTTPS.
   - HTTPS server block must reference SSL certificate and key files under `/etc/letsencrypt/live/blog.example.test/`.
   - Proxy or pass PHP requests to the `wordpress` service (via FastCGI to port 9000 or proxy_pass).
   - Restrict access to `/wp-admin/` so that only the IP `203.0.113.42` is allowed; all other IPs must be denied.

5. **TLS Certificates**
   - Use Let's Encrypt **staging** environment (`--staging` flag) to obtain a certificate for `blog.example.test` via the certbot container.
   - Before a real certificate is available, provide a self-signed certificate placeholder at:
     - `/app/wordpress/certs/blog.example.test/fullchain.pem`
     - `/app/wordpress/certs/blog.example.test/privkey.pem`
     so that Nginx can start without errors.

6. **Automatic Certificate Renewal**
   - Set up a cron job (in the host crontab) or a systemd timer that runs certbot renewal at least twice per day.
   - The renewal mechanism must execute `docker compose -f /app/wordpress/docker-compose.yml run --rm certbot renew` (or equivalent) and then reload Nginx.
   - If using cron, the entry must be present in the output of `crontab -l` for the current user or in a file under `/etc/cron.d/`.

7. **Running State**
   - After setup, `docker compose -f /app/wordpress/docker-compose.yml ps` must show all four services (`db`, `wordpress`, `nginx`, `certbot`) have been created, with `db`, `wordpress`, and `nginx` in a running state.
   - `curl -k https://blog.example.test` (executed from the host) must return an HTTP response containing the string `WordPress` or `wp-` (indicating the WordPress site is being served).
   - `curl -I http://blog.example.test` must return a `301` or `302` redirect to `https://blog.example.test`.
