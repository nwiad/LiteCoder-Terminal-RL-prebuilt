## Nginx Static Site & Reverse Proxy Setup

Configure a production-ready Nginx web server that hosts a static site at `company.local` and reverse-proxies a Node.js API at `api.company.local`, with self-signed SSL, HTTP-to-HTTPS redirect, rate limiting, and security headers.

### Technical Requirements

- OS packages: `nginx`, `ufw`, `openssl`, `nodejs` (any version available via apt)
- All configuration must be done on the local machine.
- Nginx must be installed, enabled, and running when the task is complete.

### 1. Firewall (UFW)

- Enable UFW.
- Allow the following ports only: **22/tcp (SSH)**, **80/tcp (HTTP)**, **443/tcp (HTTPS)**.
- Default incoming policy: **deny**.

### 2. Directory Structure & Static Site

Create the following directory tree with ownership `www-data:www-data` and permissions `755` for directories, `644` for files:

```
/var/www/company.local/
└── html/
    └── index.html
```

`/var/www/company.local/html/index.html` must contain a valid HTML5 page with:
- A `<title>` element containing the text `Company Home`.
- A `<h1>` element containing the text `Welcome to Company`.

### 3. Self-Signed SSL Certificates

Generate a self-signed SSL certificate and key:

| File | Path |
|------|------|
| Certificate | `/etc/ssl/certs/company.local.crt` |
| Private Key | `/etc/ssl/private/company.local.key` |

- Common Name (CN): `company.local`
- Validity: at least **365** days.
- Key size: **2048** bits or greater.

The same certificate/key pair must be used for both `company.local` and `api.company.local`.

### 4. Nginx Server Blocks

Create two Nginx server-block configuration files (and enable them via symlink in `/etc/nginx/sites-enabled/`):

#### a. `/etc/nginx/sites-available/company.local`

- Listen on port **443 ssl** for server name `company.local`.
- `root` set to `/var/www/company.local/html`.
- `index` set to `index.html`.
- SSL certificate and key paths as specified in Section 3.
- Include the following response headers on every response:
  - `X-Frame-Options`: `DENY`
  - `X-Content-Type-Options`: `nosniff`
  - `Referrer-Policy`: `strict-origin-when-cross-origin`
  - `X-XSS-Protection`: `1; mode=block`

#### b. `/etc/nginx/sites-available/api.company.local`

- Listen on port **443 ssl** for server name `api.company.local`.
- SSL certificate and key paths as specified in Section 3.
- Reverse proxy all requests (`location /`) to `http://127.0.0.1:3000`.
- Set the following proxy headers:
  - `Host`: `$host`
  - `X-Real-IP`: `$remote_addr`
  - `X-Forwarded-For`: `$proxy_add_x_forwarded_for`
  - `X-Forwarded-Proto`: `$scheme`
- Apply rate limiting using an Nginx `limit_req_zone` (zone name: `api_limit`, rate: **10r/s**, based on `$binary_remote_addr`). Apply the zone in the `location /` block with `burst=20 nodelay`.

### 5. HTTP → HTTPS Redirect

Add a server block (may be in either of the above files or a separate file) that:

- Listens on port **80** for both `company.local` and `api.company.local`.
- Returns a **301** redirect to `https://$host$request_uri` for all requests.

### 6. Node.js Backend Stub

Create a minimal Node.js HTTP server at `/app/api_server.js` that:

- Listens on `127.0.0.1:3000`.
- Responds to any request with HTTP 200 and JSON body: `{"status":"ok"}` (Content-Type: `application/json`).

This file does **not** need to be running as a service, but must be startable with `node /app/api_server.js`.

### 7. Log Rotation

Create a logrotate configuration file at `/etc/logrotate.d/nginx-custom` that:

- Targets `/var/log/nginx/*.log`.
- Rotates **daily**.
- Keeps **14** rotated files (`rotate 14`).
- Uses `compress` and `delaycompress`.
- Contains `sharedscripts` with a `postrotate` script that sends the USR1 signal to the Nginx master process (via its PID file).

### 8. Validation

When the task is complete, the following must hold true:

- `nginx -t` exits with code 0.
- `systemctl is-active nginx` returns `active`.
- `ufw status` shows rules for 22, 80, 443 and default deny incoming.
- `curl -k https://company.local/ --resolve company.local:443:127.0.0.1` returns the static HTML page with the required security headers.
- `curl -k https://api.company.local/ --resolve api.company.local:443:127.0.0.1` (with the Node.js stub running) proxies to the backend and returns `{"status":"ok"}`.
- `curl -I http://company.local/ --resolve company.local:80:127.0.0.1` returns a 301 redirect to HTTPS.
