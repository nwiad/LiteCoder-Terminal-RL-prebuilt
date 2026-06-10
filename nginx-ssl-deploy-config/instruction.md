## Secure Web Service Deployment with Nginx and SSL/TLS

Generate the configuration files needed to deploy a secure Nginx web service that serves static content over HTTPS, redirects HTTP to HTTPS, enforces security headers, and restricts firewall access.

### Technical Requirements

- All output files must be written under `/app/output/`
- Domain name: `example.company.com`
- SSL certificate path: `/etc/letsencrypt/live/example.company.com/fullchain.pem`
- SSL private key path: `/etc/letsencrypt/live/example.company.com/privkey.pem`
- Static content root: `/var/www/example.company.com/html`

### Required Output Files

1. `/app/output/nginx_https.conf` — The main Nginx server block configuration for HTTPS (port 443).
2. `/app/output/nginx_http_redirect.conf` — A separate Nginx server block that listens on port 80 and redirects all HTTP requests to HTTPS with a 301 status code.
3. `/app/output/ufw_rules.sh` — A shell script that configures UFW firewall rules.
4. `/app/output/ssl_renew.sh` — A shell script for automated SSL certificate renewal.
5. `/app/output/index.html` — A simple static HTML test page.

### Specification Details

**nginx_https.conf:**
- Must listen on port `443` with `ssl` enabled.
- Must set `server_name` to `example.company.com`.
- Must reference the SSL certificate and key paths specified above.
- Must include the `root` directive pointing to the static content root.
- Must include all of the following security headers (via `add_header` directives):
  - `Strict-Transport-Security` with `max-age` of at least `31536000` and `includeSubDomains`
  - `X-Frame-Options` set to `DENY` or `SAMEORIGIN`
  - `X-Content-Type-Options` set to `nosniff`
  - `X-XSS-Protection`
- Must specify `ssl_protocols` that include `TLSv1.2` and `TLSv1.3` only (no TLSv1 or TLSv1.1).
- Must include an `ssl_ciphers` directive.
- Must include a `location /` block.

**nginx_http_redirect.conf:**
- Must listen on port `80`.
- Must set `server_name` to `example.company.com`.
- Must contain a `return 301 https://$host$request_uri;` directive (or equivalent rewrite that performs a 301 redirect to the HTTPS version).

**ufw_rules.sh:**
- Must be a valid shell script (starts with `#!/bin/bash` or `#!/bin/sh`).
- Must enable UFW (`ufw enable` or `ufw --force enable`).
- Must set the default incoming policy to deny (`ufw default deny incoming`).
- Must allow SSH (port 22).
- Must allow HTTP (port 80).
- Must allow HTTPS (port 443).
- Must NOT allow any other ports.

**ssl_renew.sh:**
- Must be a valid shell script (starts with `#!/bin/bash` or `#!/bin/sh`).
- Must invoke `certbot renew` (or `certbot` with renewal arguments).
- Must reload or restart Nginx after renewal (e.g., `systemctl reload nginx` or `nginx -s reload`).

**index.html:**
- Must be a valid HTML file containing a `<!DOCTYPE html>` declaration (case-insensitive).
- Must contain `<html>`, `<head>`, `<body>` tags.
- Must contain a `<title>` element.
