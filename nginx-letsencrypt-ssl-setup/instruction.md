## Secure Web Service with Nginx and Let's Encrypt

Set up configuration files and scripts for a secure Nginx reverse proxy with SSL termination, targeting an upstream application on port 5000.

### Technical Requirements

- All output files must be placed under `/app/`
- Target OS: Ubuntu 22.04
- Web server: Nginx
- SSL certificate tool: Certbot (Let's Encrypt)
- Domain: `example.startup.com`
- Upstream application: `127.0.0.1:5000`

### Deliverables

#### 1. Nginx Configuration — `/app/nginx/sites-available/example.startup.com`

A complete Nginx server block configuration file that includes:

- An HTTP server block (port 80) that redirects all traffic to HTTPS (301 redirect).
- An HTTPS server block (port 443) with:
  - `ssl_certificate` pointing to `/etc/letsencrypt/live/example.startup.com/fullchain.pem`
  - `ssl_certificate_key` pointing to `/etc/letsencrypt/live/example.startup.com/privkey.pem`
  - TLS protocols limited to TLSv1.2 and TLSv1.3 only (via `ssl_protocols`).
  - A `location /` block that reverse-proxies to `http://127.0.0.1:5000`, including at minimum these proxy headers:
    - `proxy_set_header Host $host;`
    - `proxy_set_header X-Real-IP $remote_addr;`
    - `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`
    - `proxy_set_header X-Forwarded-Proto $scheme;`
  - Security headers:
    - `X-Frame-Options` set to `DENY` or `SAMEORIGIN`
    - `X-Content-Type-Options` set to `nosniff`
    - `Strict-Transport-Security` with `max-age` of at least 31536000

#### 2. Setup Script — `/app/setup.sh`

A Bash script (must start with `#!/bin/bash`) that performs the following steps in order. Each step must be clearly present as commands in the script:

1. Update package lists (`apt-get update`).
2. Install Nginx (`apt-get install` nginx).
3. Install Certbot and its Nginx plugin (`apt-get install` certbot python3-certbot-nginx).
4. Configure UFW firewall to allow ports 80 and 443 (using `ufw allow`).
5. Copy or symlink the Nginx site config into the appropriate Nginx directory.
6. Obtain an SSL certificate using `certbot` with `--nginx` flag for domain `example.startup.com`.
7. Enable and start/reload Nginx.

#### 3. Renewal Script — `/app/renew_cert.sh`

A Bash script (must start with `#!/bin/bash`) that:

- Runs `certbot renew`.
- Reloads Nginx after renewal (using `systemctl reload nginx` or `nginx -s reload`).

#### 4. Cron Job Configuration — `/app/crontab_renewal`

A crontab-format file containing a single cron entry that:

- Runs the renewal script (`/app/renew_cert.sh`) automatically.
- Executes at least once per day or twice per day (the schedule must be a valid 5-field cron expression).

#### 5. Test Application — `/app/app.py`

A minimal Python 3 HTTP server script that:

- Listens on `0.0.0.0` port `5000`.
- Responds to GET requests on `/` with HTTP 200 and a JSON body: `{"status": "ok"}` with `Content-Type: application/json`.

#### 6. Output Summary — `/app/output.json`

A JSON file summarizing the setup with the following structure:

```json
{
  "domain": "example.startup.com",
  "upstream": "127.0.0.1:5000",
  "ssl_certificate": "/etc/letsencrypt/live/example.startup.com/fullchain.pem",
  "ssl_certificate_key": "/etc/letsencrypt/live/example.startup.com/privkey.pem",
  "tls_protocols": ["TLSv1.2", "TLSv1.3"],
  "http_redirect": true,
  "security_headers": ["X-Frame-Options", "X-Content-Type-Options", "Strict-Transport-Security"],
  "files_created": [
    "/app/nginx/sites-available/example.startup.com",
    "/app/setup.sh",
    "/app/renew_cert.sh",
    "/app/crontab_renewal",
    "/app/app.py",
    "/app/output.json"
  ]
}
```

All six keys must be present. `tls_protocols` must be an array of exactly two strings. `security_headers` must be an array of at least three strings. `files_created` must list all six files above.
