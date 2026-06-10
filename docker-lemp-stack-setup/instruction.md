## Single-Host LEMP Stack with Docker Containers

Set up a fully functional LEMP (Linux, Nginx, MySQL, PHP-FPM) web stack using Docker containers connected through a custom bridge network. All configuration files, application code, and management scripts must be created under `/app`.

### Technical Requirements

- Docker and Docker CLI
- All files created under `/app`

### Network Configuration

Create a custom Docker bridge network with these exact settings:

- Network name: `lemp_network`
- Driver: `bridge`
- Subnet: `172.20.0.0/16`
- Gateway: `172.20.0.1`

### Container Specifications

Launch the following containers, all attached to `lemp_network`:

1. **MySQL 8.0** container:
   - Container name: `lemp_mysql`
   - Image: `mysql:8.0`
   - Static IP: `172.20.0.10`
   - Port mapping: `3306:3306`
   - Environment variables:
     - `MYSQL_ROOT_PASSWORD=rootpass123`
     - `MYSQL_DATABASE=lemp_db`
     - `MYSQL_USER=lemp_user`
     - `MYSQL_PASSWORD=lemp_pass`
   - A named volume `lemp_mysql_data` mounted at `/var/lib/mysql`

2. **PHP-FPM** container:
   - Container name: `lemp_php`
   - Image: must be based on `php:8.2-fpm` (custom Dockerfile allowed to install `mysqli` and `pdo_mysql` extensions)
   - Static IP: `172.20.0.11`
   - Mount `/app/www` to `/var/www/html` in the container

3. **Nginx** container:
   - Container name: `lemp_nginx`
   - Image: `nginx:latest`
   - Static IP: `172.20.0.12`
   - Port mapping: `8080:80`
   - Mount `/app/www` to `/var/www/html` in the container
   - Mount `/app/nginx/default.conf` to `/etc/nginx/conf.d/default.conf` in the container

### Configuration Files

- `/app/nginx/default.conf` — Nginx server configuration that:
  - Listens on port 80
  - Sets document root to `/var/www/html`
  - Serves `index.php` as the default index file
  - Proxies `.php` requests to `lemp_php:9000` via FastCGI

- `/app/php/Dockerfile` — (if needed) Dockerfile extending `php:8.2-fpm` to install `mysqli` and `pdo_mysql` extensions.

### Application Files

- `/app/www/index.php` — A PHP page that:
  - Connects to MySQL using host `lemp_mysql`, user `lemp_user`, password `lemp_pass`, database `lemp_db`
  - Outputs a JSON response with `Content-Type: application/json` header
  - On success, returns: `{"status":"ok","server_info":"<mysql_server_info_string>"}`
  - On failure, returns: `{"status":"error","message":"<error_description>"}`

### Scripts

- `/app/setup.sh` — A bash script that:
  - Creates the Docker network (if it doesn't already exist)
  - Builds any custom images (if needed)
  - Starts all three containers in the correct order (MySQL first, then PHP-FPM, then Nginx)
  - Is executable and uses `#!/bin/bash` shebang
  - Exits with code 0 on success

- `/app/cleanup.sh` — A bash script that:
  - Stops and removes all three containers (`lemp_mysql`, `lemp_php`, `lemp_nginx`)
  - Removes the `lemp_network` network
  - Removes the `lemp_mysql_data` volume
  - Is executable and uses `#!/bin/bash` shebang
  - Exits with code 0 on success

### Network Report

- `/app/network_report.json` — Generated after all containers are running. JSON file containing:

```json
{
  "network_name": "lemp_network",
  "subnet": "172.20.0.0/16",
  "gateway": "172.20.0.1",
  "containers": {
    "lemp_mysql": "172.20.0.10",
    "lemp_nginx": "172.20.0.12",
    "lemp_php": "172.20.0.11"
  }
}
```

### Verification

After running `/app/setup.sh` and waiting for MySQL to be ready:

- `curl -s http://localhost:8080/` must return valid JSON with `"status":"ok"`.
- `docker network inspect lemp_network` must show all three containers attached.
- All three containers (`lemp_mysql`, `lemp_php`, `lemp_nginx`) must be in running state.
