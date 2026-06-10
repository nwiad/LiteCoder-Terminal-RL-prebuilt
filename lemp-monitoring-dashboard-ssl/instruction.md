## Full-Stack LEMP Monitoring Dashboard with SSL and Docker

Create a fully containerized LEMP (Linux, Nginx, MySQL, PHP) stack with a web-based monitoring dashboard and SSL support, orchestrated via Docker Compose.

### Technical Requirements

- All project files must be created under `/app/`
- Docker Compose version: use Compose Specification (no legacy `version` field required)
- Base images: `nginx:1.24`, `mysql:8.0`, `php:8.1-fpm`

### Project Structure

```
/app/
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   └── ssl/
│       ├── server.crt
│       └── server.key
├── php/
│   ├── Dockerfile
│   └── src/
│       └── index.php
├── mysql/
│   └── init.sql
└── monitoring/
    └── prometheus.yml
```

### Docker Compose (`/app/docker-compose.yml`)

Must define the following services with these exact service names:

1. **nginx** — Reverse proxy and web server
   - Image: `nginx:1.24`
   - Ports: map host `8080` to container `80`, and host `8443` to container `443`
   - Depends on: `php`
   - Mount `/app/nginx/nginx.conf` to `/etc/nginx/nginx.conf`
   - Mount `/app/nginx/ssl/` to `/etc/nginx/ssl/`
   - Mount `/app/php/src/` to `/var/www/html/`
   - Connected to network `lemp_network`

2. **php** — PHP-FPM application server
   - Build from `/app/php/Dockerfile`
   - Mount `/app/php/src/` to `/var/www/html/`
   - Depends on: `mysql`
   - Connected to network `lemp_network`

3. **mysql** — Database server
   - Image: `mysql:8.0`
   - Environment variables: `MYSQL_ROOT_PASSWORD=rootpass123`, `MYSQL_DATABASE=app_db`, `MYSQL_USER=app_user`, `MYSQL_PASSWORD=app_pass`
   - Use a named volume `mysql_data` mounted to `/var/lib/mysql`
   - Mount `/app/mysql/init.sql` to `/docker-entrypoint-initdb.d/init.sql`
   - Connected to network `lemp_network`

4. **prometheus** — Monitoring service
   - Image: `prom/prometheus:latest`
   - Ports: map host `9090` to container `9090`
   - Mount `/app/monitoring/prometheus.yml` to `/etc/prometheus/prometheus.yml`
   - Connected to network `lemp_network`

Define a custom bridge network named `lemp_network` and a named volume `mysql_data`.

### Nginx Configuration (`/app/nginx/nginx.conf`)

- Listen on port `80` and redirect all HTTP traffic to HTTPS (port `443`)
- Listen on port `443` with SSL enabled
- SSL certificate path: `/etc/nginx/ssl/server.crt`
- SSL key path: `/etc/nginx/ssl/server.key`
- Proxy PHP requests (files ending in `.php`) to `php:9000` via FastCGI
- Set `root` to `/var/www/html`
- Set `index` to `index.php`

### SSL Certificates (`/app/nginx/ssl/`)

Generate a self-signed SSL certificate and key:
- `/app/nginx/ssl/server.crt` — self-signed certificate
- `/app/nginx/ssl/server.key` — private key
- Common Name (CN): `localhost`

### PHP Dockerfile (`/app/php/Dockerfile`)

- Base image: `php:8.1-fpm`
- Install extensions: `mysqli` and `pdo_mysql`
- Working directory: `/var/www/html`

### PHP Application (`/app/php/src/index.php`)

- The file must call `phpinfo()` to display PHP configuration details
- Before calling `phpinfo()`, attempt a PDO connection to the MySQL service (host: `mysql`, dbname: `app_db`, user: `app_user`, password: `app_pass`) and print `DB_CONNECTION_OK` if successful or `DB_CONNECTION_FAILED` if it fails

### MySQL Init Script (`/app/mysql/init.sql`)

- Create a table named `health_check` in the `app_db` database with columns: `id` (INT, AUTO_INCREMENT, PRIMARY KEY) and `status` (VARCHAR(50))
- Insert one row with `status` value `ok`

### Prometheus Configuration (`/app/monitoring/prometheus.yml`)

- Configure a scrape job named `nginx` targeting `nginx:80` with a scrape interval of `15s`
- Configure a scrape job named `mysql` targeting `mysql:3306` with a scrape interval of `15s`
