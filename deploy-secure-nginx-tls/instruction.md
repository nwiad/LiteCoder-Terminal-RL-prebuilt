## Deploy and Secure Nginx with TLS/SSL

Set up a hardened Nginx web server on Ubuntu that serves HTTPS traffic on port 443 using a self-signed certificate, while redirecting all HTTP (port 80) traffic to HTTPS.

### Requirements

1. **Install Nginx**: Ensure Nginx is installed and running.

2. **Self-Signed TLS Certificate**:
   - Generate a self-signed certificate and private key using OpenSSL.
   - Certificate path: `/etc/ssl/certs/nginx-selfsigned.crt`
   - Private key path: `/etc/ssl/private/nginx-selfsigned.key`
   - Key size: 2048-bit RSA minimum.
   - Certificate validity: 365 days.
   - Subject CN (Common Name): `localhost`

3. **HTTPS Configuration (port 443)**:
   - Nginx must listen on port 443 with SSL enabled.
   - The SSL configuration must reference the certificate and key paths above.
   - Serving a default page that returns HTTP 200 on `https://localhost/`.

4. **HTTP to HTTPS Redirect (port 80)**:
   - Nginx must listen on port 80.
   - All HTTP requests to port 80 must return a 301 redirect to the equivalent HTTPS URL.
   - For example, `http://localhost/` must redirect to `https://localhost/`.

5. **Security Hardening**:
   - Disable SSLv3 and TLSv1.0 (only TLSv1.2 and/or TLSv1.3 should be enabled).
   - Include the following response headers on HTTPS responses:
     - `Strict-Transport-Security` (HSTS) with a `max-age` of at least 31536000.
     - `X-Content-Type-Options` set to `nosniff`.
     - `X-Frame-Options` set to `DENY` or `SAMEORIGIN`.
   - Hide the Nginx version number from response headers (`server_tokens off`).

6. **Service Persistence**:
   - Nginx must be enabled to start on boot (via systemd).

7. **Documentation**:
   - Write a summary file to `/app/setup_summary.txt` containing:
     - The certificate file path and key file path used.
     - The key size and certificate validity period.
     - The TLS protocols enabled.
     - A brief description of the HTTP-to-HTTPS redirect behavior.

### Validation Notes

- `nginx -t` must pass without errors.
- `systemctl is-active nginx` must return `active`.
- `systemctl is-enabled nginx` must return `enabled`.
- A curl request to `http://localhost/` must receive a 301 redirect to `https://localhost/`.
- A curl request to `https://localhost/` (with `-k` for self-signed cert) must return HTTP 200.
- HTTPS responses must include the required security headers listed above.
