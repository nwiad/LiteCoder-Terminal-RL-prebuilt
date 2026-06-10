## Custom Nginx Configuration with SSL and Auto-renewal

Create a production-ready Nginx configuration setup with SSL support, HTTP-to-HTTPS redirection, security headers, a static website, and an automatic certificate renewal mechanism. All files should be generated under `/app/`.

### Technical Requirements

- Shell scripts must use `#!/bin/bash` shebang
- All shell scripts must be executable (chmod +x)
- Nginx configuration must use valid Nginx syntax

### File Structure

Generate the following files:

1. `/app/nginx/nginx.conf` — Main Nginx configuration file
2. `/app/nginx/conf.d/default.conf` — Default server block configuration
3. `/app/nginx/conf.d/ssl.conf` — SSL server block configuration
4. `/app/www/index.html` — Static website homepage
5. `/app/www/css/style.css` — Stylesheet for the static site
6. `/app/scripts/renew-certs.sh` — SSL certificate auto-renewal script
7. `/app/scripts/setup-firewall.sh` — Firewall setup script allowing HTTP (80) and HTTPS (443)

### Nginx Configuration Specifications

**`nginx.conf`:**
- Must include a `worker_processes` directive
- Must include an `http` block
- Must include a `mime.types` reference inside the `http` block
- Must include directives to load config files from `conf.d/` directory (using `include`)

**`default.conf` (HTTP server block — port 80):**
- Must listen on port `80`
- Must set `server_name` to `example.com www.example.com`
- Must contain a redirect rule (return 301) that redirects all HTTP requests to `https://$host$request_uri`

**`ssl.conf` (HTTPS server block — port 443):**
- Must listen on port `443` with `ssl` enabled
- Must set `server_name` to `example.com www.example.com`
- Must specify `ssl_certificate` pointing to `/etc/letsencrypt/live/example.com/fullchain.pem`
- Must specify `ssl_certificate_key` pointing to `/etc/letsencrypt/live/example.com/privkey.pem`
- Must set `ssl_protocols` to allow only `TLSv1.2 TLSv1.3`
- Must include the following security headers (via `add_header`):
  - `X-Frame-Options` set to `DENY`
  - `X-Content-Type-Options` set to `nosniff`
  - `Strict-Transport-Security` with `max-age` of at least `31536000` and `includeSubDomains`
  - `X-XSS-Protection` set to `1; mode=block`
- Must set `root` to `/app/www`
- Must include a `location /` block with a `try_files` directive

### Static Website Specifications

**`index.html`:**
- Must be valid HTML5 (starts with `<!DOCTYPE html>`)
- Must contain a `<title>` element
- Must link to `css/style.css` via a `<link>` tag
- Must contain at least one `<h1>` heading element

**`style.css`:**
- Must be a non-empty CSS file containing at least one style rule

### Script Specifications

**`renew-certs.sh`:**
- Must contain a `certbot renew` command
- Must contain a command to reload or restart Nginx after renewal (e.g., `nginx -s reload` or `systemctl reload nginx`)
- Must include logging output (redirect or `echo`) indicating renewal attempt

**`setup-firewall.sh`:**
- Must contain commands to allow traffic on port `80`
- Must contain commands to allow traffic on port `443`
- Must reference a firewall tool (e.g., `ufw` or `iptables` or `firewall-cmd`)
