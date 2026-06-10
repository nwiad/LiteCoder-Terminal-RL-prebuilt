Deploy a secure, containerized WordPress site using Docker Compose on Ubuntu 22.04 with SSL termination via Nginx, MariaDB as the database, and MinIO as an S3-compatible backup target.

## Technical Requirements

- OS: Ubuntu 22.04
- Tools: Docker, Docker Compose (latest stable)
- Working directory: /app

## Project Structure

Create the following project layout under `/app`:

```
/app/
├── docker-compose.yml
├── .env.example
├── README.md
├── nginx/
│   └── default.conf
├── backup/
│   ├── backup.sh
│   └── restore.sh
└── healthcheck.sh
```

## docker-compose.yml

Define the following services in `/app/docker-compose.yml`:

1. **wordpress1** and **wordpress2**: Two WordPress containers using the `wordpress:latest` image. Both must connect to the same MariaDB database and share a named volume `wp_uploads` mounted at `/var/www/html`. Each must expose port 8080 internally.
2. **db**: A MariaDB container using `mariadb:latest`. It must use a named volume `db_data` mounted at `/var/lib/mysql`. The database name, user, password, and root password must all be configured via environment variables referencing the `.env.example` keys (see below).
3. **nginx**: An Nginx container that acts as a reverse proxy. It must map host port `80` to container port `80` and host port `443` to container port `443`. It must mount `./nginx/default.conf` into the container and depend on both wordpress1 and wordpress2.
4. **minio**: A MinIO container using `minio/minio:latest`. It must expose port `9000` for the S3 API and port `9001` for the console. Access key and secret key must be configured via environment variables. It must use a named volume `minio_data`.
5. **certbot**: A Certbot container using `certbot/certbot:latest`. It must share a volume with the nginx container for certificate storage. The volume name must be `certbot_etc` mounted at `/etc/letsencrypt`.
6. **backup**: A sidecar container that mounts the `db_data` and `wp_uploads` volumes and has access to the backup scripts in `./backup/`.

All services must be on a shared Docker network named `wp_network`.

The file must define these named volumes at the top level: `db_data`, `wp_uploads`, `minio_data`, `certbot_etc`.

## Nginx Configuration

Create `/app/nginx/default.conf` with the following requirements:

- Define an `upstream` block named `wordpress` that load-balances between `wordpress1:8080` and `wordpress2:8080`.
- Include a `server` block listening on port `80` that redirects all HTTP traffic to HTTPS (return 301).
- Include a `server` block listening on port `443` with `ssl` enabled.
- The SSL server block must reference certificate paths under `/etc/letsencrypt/`.
- The SSL server block must proxy requests to the `wordpress` upstream.
- Disable weak TLS protocols: only `TLSv1.2` and `TLSv1.3` are allowed (via `ssl_protocols` directive).
- Set `ssl_ciphers` to `HIGH:!aNULL:!MD5`.
- Include `proxy_set_header` directives for `Host`, `X-Real-IP`, and `X-Forwarded-Proto`.

## Backup Script

Create `/app/backup/backup.sh` (executable, `#!/bin/bash`):

- The script must use `mysqldump` to dump the WordPress database to a `.sql` file.
- The script must use the `mc` (MinIO Client) CLI or `aws s3 cp` (with `--endpoint-url`) to upload both the SQL dump and the WordPress uploads directory (as a tar.gz archive) to a MinIO bucket named `backups`.
- The backup filenames must include a date stamp in the format `YYYY-MM-DD` (e.g., `db-2025-01-15.sql`, `uploads-2025-01-15.tar.gz`).
- Database connection parameters (host, user, password, database name) must be read from environment variables, not hardcoded.

## Restore Script

Create `/app/backup/restore.sh` (executable, `#!/bin/bash`):

- The script must accept one argument: the date stamp (e.g., `2025-01-15`) identifying which backup to restore.
- It must download the corresponding `.sql` and `.tar.gz` files from the MinIO `backups` bucket.
- It must restore the database using `mysql` CLI import.
- It must extract the uploads archive back to the WordPress uploads path.
- On success, print exactly: `Restore completed successfully`
- On failure (e.g., missing backup files), print exactly: `Restore failed` and exit with code 1.

## .env.example

Create `/app/.env.example` containing at minimum these keys (with placeholder values):

```
MYSQL_ROOT_PASSWORD=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
WORDPRESS_DB_HOST=
WORDPRESS_DB_USER=
WORDPRESS_DB_PASSWORD=
WORDPRESS_DB_NAME=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
DOMAIN=
```

Each key must have a comment above or inline explaining its purpose.

## README.md

Create `/app/README.md` that includes at minimum:

- A section explaining how to start the stack (must reference `docker compose up`).
- A section explaining how to stop/tear down the stack (must reference `docker compose down`).
- A section explaining how to restore from backup (must reference `restore.sh`).

## Health Check Script

Create `/app/healthcheck.sh` (executable, `#!/bin/bash`):

- The script must check that all containers defined in docker-compose.yml are running.
- The script must attempt an HTTPS request to `https://localhost` (allowing self-signed certs).
- If all containers are running AND the HTTPS request returns HTTP 200, print exactly: `OK`
- Otherwise, print exactly: `FAIL` and exit with code 1.

## Security Hardening

- In `docker-compose.yml`, the `db` service must not publish any ports to the host.
- The Nginx SSL configuration must not allow `TLSv1` or `TLSv1.1`.
- Backup scripts must not contain hardcoded passwords.
