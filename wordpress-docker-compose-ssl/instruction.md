Set up a multi-container WordPress development environment using Docker Compose with an nginx reverse proxy, self-signed SSL, MySQL database, and persistent storage.

## Technical Requirements

- Docker and Docker Compose
- All project files must reside under `/app/`
- The main compose file must be `/app/docker-compose.yml`

## Project Structure

Create the following files at minimum:

```
/app/
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   └── certs/
│       ├── self-signed.crt
│       └── self-signed.key
```

## Docker Compose Specification

The `/app/docker-compose.yml` must define exactly these four services with these exact service names:

1. **nginx** — Reverse proxy and SSL termination
   - Must expose port `443` on the host (mapped as `443:443`)
   - Must expose port `80` on the host (mapped as `80:80`)
   - Must mount the nginx config and SSL certificates
   - Must depend on the `wordpress` service

2. **wordpress** — WordPress application (use official `wordpress` image with an Apache or FPM variant)
   - Must NOT expose any ports directly to the host
   - Must use environment variables to connect to the `db` service
   - Must use a named volume called `wordpress_data` mounted at `/var/www/html`

3. **db** — MySQL database (use official `mysql:8.0` image)
   - Must NOT expose any ports directly to the host
   - Must use a named volume called `db_data` mounted at `/var/lib/mysql`
   - Must set the following environment variables:
     - `MYSQL_DATABASE` = `wordpress`
     - `MYSQL_USER` = `wpuser`
     - `MYSQL_PASSWORD` = `wppass`
     - `MYSQL_ROOT_PASSWORD` = `rootpass`

4. **phpmyadmin** (optional but if present, must use service name `phpmyadmin`)

## Named Volumes

The compose file must declare these top-level named volumes:
- `wordpress_data`
- `db_data`

## Networks

Define at least one custom bridge network named `wp_network`. All services (`nginx`, `wordpress`, `db`) must be attached to `wp_network`. Do not use the default network.

## Nginx Configuration

The file `/app/nginx/nginx.conf` must:
- Listen on port `443` with SSL enabled
- Listen on port `80` and redirect all HTTP traffic to HTTPS
- Proxy pass requests to the `wordpress` service on its internal port
- Reference the SSL certificate at `/etc/nginx/certs/self-signed.crt` and key at `/etc/nginx/certs/self-signed.key` (these paths are inside the container)

## SSL Certificates

Generate a self-signed certificate and key and place them at:
- `/app/nginx/certs/self-signed.crt`
- `/app/nginx/certs/self-signed.key`

The certificate must be a valid X.509 PEM-encoded certificate (parseable by `openssl x509 -in self-signed.crt -noout`).

## Validation

After setup, running `docker compose -f /app/docker-compose.yml config` must succeed without errors (valid compose syntax).
