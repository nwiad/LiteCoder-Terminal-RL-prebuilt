## Local Domain Website with HTTPS

Configure the local domain `myapp.local` to serve a simple website over HTTPS using a self-signed certificate, with Nginx as the web server and dnsmasq for local DNS resolution.

### Technical Requirements

- **OS:** Linux (Debian/Ubuntu-based)
- **Packages:** nginx, openssl, dnsmasq
- **Domain:** `myapp.local`
- **Working directory:** /app

### 1. Local DNS Resolution

- Install and configure dnsmasq so that `myapp.local` resolves to `127.0.0.1`.
- The dnsmasq configuration must include an address entry for `myapp.local`.
- Ensure the system's `/etc/resolv.conf` uses `127.0.0.1` as a nameserver so local resolution works.
- After configuration, `getent hosts myapp.local` or equivalent must resolve to `127.0.0.1`.

### 2. HTML Website

Create a website with exactly 3 HTML pages served from `/var/www/myapp.local/`:

- `/var/www/myapp.local/index.html` — Home page. Must contain an `<h1>` tag with the text `Welcome to MyApp`.
- `/var/www/myapp.local/about.html` — About page. Must contain an `<h1>` tag with the text `About MyApp`.
- `/var/www/myapp.local/contact.html` — Contact page. Must contain an `<h1>` tag with the text `Contact Us`.

Each page must be valid HTML (with `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` tags) and must contain at least one navigation link (`<a>` tag) to another page on the site.

### 3. Self-Signed SSL Certificate

Generate a self-signed SSL certificate and key for `myapp.local`:

- Certificate file: `/etc/ssl/certs/myapp.local.crt`
- Key file: `/etc/ssl/private/myapp.local.key`
- The certificate Common Name (CN) or Subject Alternative Name (SAN) must include `myapp.local`.
- The certificate must be valid (not expired) at the time of testing.

### 4. Nginx Configuration

- Create an Nginx server block configuration file at `/etc/nginx/sites-available/myapp.local`.
- Enable the site by symlinking to `/etc/nginx/sites-enabled/myapp.local`.
- The server block must:
  - Listen on port `443` with SSL enabled.
  - Set `server_name` to `myapp.local`.
  - Use the generated certificate and key files from Step 3.
  - Set the document root to `/var/www/myapp.local/`.
- Nginx must be running and serving the site after configuration.

### 5. Verification

After all configuration is complete:

- `curl -k https://myapp.local/` must return the content of `index.html` (HTTP 200).
- `curl -k https://myapp.local/about.html` must return the content of `about.html` (HTTP 200).
- `curl -k https://myapp.local/contact.html` must return the content of `contact.html` (HTTP 200).

Write the output of `curl -k -s -o /dev/null -w "%{http_code}" https://myapp.local/` to `/app/output.txt`. The file must contain exactly `200`.

### 6. Documentation

Create `/app/README.md` documenting the configuration steps performed, including:
- How DNS resolution was configured
- How the SSL certificate was generated
- How Nginx was configured
- How to verify the setup
