## Automating NGINX Server Hardening and Deployment

Create a bash script that automates the deployment of a hardened NGINX server with SSL/TLS and a simple web application on Ubuntu.

### Technical Requirements

- Language: Bash
- Main script: `/app/deploy.sh` (must be executable, `chmod +x`)
- The script must be idempotent (safe to run multiple times without errors)
- All generated config files and assets must be placed under their proper system paths as described below

### Script Responsibilities

`/app/deploy.sh` must perform the following in order:

1. **Install and configure NGINX**
   - Install NGINX via `apt-get` if not already installed
   - Create a dedicated non-privileged system user `webdeploy` (if it doesn't already exist) to be used as the NGINX worker process user
   - Update the NGINX main config (`/etc/nginx/nginx.conf`) so the `user` directive is set to `webdeploy`

2. **Deploy a simple web application**
   - Create the web root directory at `/var/www/secureapp`
   - Place an `index.html` file at `/var/www/secureapp/index.html` containing at minimum:
     - An `<h1>` element with the text `Secure App`
     - A `<link>` tag referencing `style.css`
     - A `<script>` tag referencing `app.js`
   - Place a `style.css` file at `/var/www/secureapp/style.css` (non-empty)
   - Place an `app.js` file at `/var/www/secureapp/app.js` (non-empty)

3. **Generate self-signed SSL/TLS certificates using OpenSSL**
   - Private key: `/etc/ssl/private/secureapp.key` (RSA, minimum 2048-bit)
   - Certificate: `/etc/ssl/certs/secureapp.crt` (valid for at least 365 days, subject CN=`localhost`)

4. **Create NGINX site configuration**
   - Config file: `/etc/nginx/sites-available/secureapp`
   - Symlink to: `/etc/nginx/sites-enabled/secureapp`
   - Remove the default site symlink `/etc/nginx/sites-enabled/default` if it exists
   - The HTTPS server block (port 443) must include:
     - `ssl_certificate` and `ssl_certificate_key` pointing to the generated cert/key
     - `root /var/www/secureapp;`
     - `index index.html;`
     - The following security headers:
       - `X-Frame-Options` set to `DENY`
       - `X-Content-Type-Options` set to `nosniff`
       - `X-XSS-Protection` set to `1; mode=block`
       - `Strict-Transport-Security` with `max-age` of at least `31536000`
       - `Referrer-Policy` set to `no-referrer`
     - `ssl_protocols` restricted to `TLSv1.2 TLSv1.3` only
     - `server_tokens off;`
   - An HTTP server block (port 80) that returns a 301 redirect to HTTPS for all requests

5. **Configure firewall using UFW**
   - Allow ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
   - Enable UFW (use `--force` to avoid interactive prompt)
   - Default incoming policy: deny

6. **Validate and restart NGINX**
   - Run `nginx -t` to validate configuration
   - Restart or reload NGINX

7. **Generate a system report**
   - Output file: `/app/report.json`
   - The JSON file must contain the following top-level keys:
     - `nginx_version`: string, output of `nginx -v` (stderr captured)
     - `ssl_certificate_subject`: string, the subject line from the generated certificate (output of `openssl x509 -noout -subject -in /etc/ssl/certs/secureapp.crt`)
     - `ssl_certificate_expiry`: string, the expiry date from the certificate (output of `openssl x509 -noout -enddate -in /etc/ssl/certs/secureapp.crt`)
     - `open_ports`: array of integers, the UFW allowed ports (e.g., `[22, 80, 443]`)
     - `security_headers`: object with keys `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Strict-Transport-Security`, `Referrer-Policy` and their configured values as strings
     - `nginx_user`: string, the configured NGINX worker user (should be `webdeploy`)
     - `ssl_protocols`: string, the configured SSL protocols value
     - `server_tokens`: string, `"off"`

### Output

- `/app/deploy.sh` — main deployment script
- `/app/report.json` — system report (generated when `deploy.sh` is executed)
