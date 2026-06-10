## Multi-Site WordPress Network Setup with Docker

Create a fully functional multi-site WordPress network using Docker containers, with each site accessible via custom sub-domains and an Nginx reverse proxy handling HTTPS termination.

### Technical Requirements

- All configuration files must be placed under `/app/`
- Docker Compose version: use Compose Specification (no `version` field required, or use `"3.8"` or above)
- All containers must be defined in `/app/docker-compose.yml`

### Required Services in `docker-compose.yml`

The Compose file must define the following services (exact service names):

1. **`db`** — MySQL 8.0 database
   - Image: `mysql:8.0`
   - Environment variables must include: `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE` (set to `wordpress`), `MYSQL_USER` (set to `wordpress`), `MYSQL_PASSWORD`
   - Must use a named volume `db_data` mounted to `/var/lib/mysql`

2. **`wordpress`** — WordPress application
   - Image: `wordpress:latest` (or a specific `wordpress:6.x` tag)
   - Must depend on the `db` service
   - Environment variables must include: `WORDPRESS_DB_HOST` (set to `db:3306`), `WORDPRESS_DB_USER`, `WORDPRESS_DB_PASSWORD`, `WORDPRESS_DB_NAME` (set to `wordpress`)
   - Must use a named volume `wordpress_data` mounted to `/var/www/html`
   - Must NOT directly expose port 80 to the host (Nginx handles external traffic)

3. **`nginx`** — Nginx reverse proxy
   - Image: `nginx:latest` (or a specific stable tag)
   - Must depend on the `wordpress` service
   - Must expose port `443` to the host (mapped as `443:443`)
   - Must expose port `80` to the host (mapped as `80:80`)
   - Must bind-mount the Nginx configuration from `./nginx/default.conf` to `/etc/nginx/conf.d/default.conf` (read-only preferred)
   - Must bind-mount a directory `./certs/` to `/etc/nginx/certs/` for SSL certificates

### Nginx Configuration

Create the file `/app/nginx/default.conf` with the following requirements:

- Define an `upstream` block named `wordpress` pointing to the `wordpress` container on port 80
- Server block listening on port `80` that redirects all HTTP traffic to HTTPS (return 301)
- Server block listening on port `443` with SSL enabled
- `server_name` must handle wildcard subdomains: `company.local *.company.local`
- SSL certificate path: `/etc/nginx/certs/selfsigned.crt`
- SSL certificate key path: `/etc/nginx/certs/selfsigned.key`
- Proxy pass to the `wordpress` upstream
- Must set the following proxy headers: `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`

### SSL Certificates

Generate self-signed SSL certificates for testing purposes. Create a script at `/app/generate-certs.sh` that:

- Creates the `/app/certs/` directory if it doesn't exist
- Generates a self-signed certificate and key at `/app/certs/selfsigned.crt` and `/app/certs/selfsigned.key`
- The certificate must cover `company.local` and `*.company.local` (wildcard) as Subject Alternative Names
- The script must be executable (`chmod +x`)

### WordPress Multisite Configuration

Create a file `/app/wp-config-multisite.php` containing the PHP constants needed to enable WordPress multisite in sub-domain mode. It must define at minimum:

- `WP_ALLOW_MULTISITE` set to `true`
- `MULTISITE` set to `true`
- `SUBDOMAIN_INSTALL` set to `true`
- `DOMAIN_CURRENT_SITE` set to `'company.local'`
- `PATH_CURRENT_SITE` set to `'/'`
- `SITE_ID_CURRENT_SITE` set to `1`
- `BLOG_ID_CURRENT_SITE` set to `1`

### Directory Structure

The final file layout under `/app/` must be:

```
/app/
├── docker-compose.yml
├── nginx/
│   └── default.conf
├── certs/
│   ├── selfsigned.crt
│   └── selfsigned.key
├── generate-certs.sh
└── wp-config-multisite.php
```

### Validation Criteria

- `docker-compose.yml` must be valid YAML and parseable by `docker compose config`
- `nginx/default.conf` must be syntactically valid Nginx configuration
- `generate-certs.sh` must be executable and produce valid certificate files when run
- `wp-config-multisite.php` must be valid PHP syntax
- All named volumes (`db_data`, `wordpress_data`) must be declared in a top-level `volumes` section in the Compose file
- All services must be on a shared custom Docker network named `wp_network`, declared in a top-level `networks` section
