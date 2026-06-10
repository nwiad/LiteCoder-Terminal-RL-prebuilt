## Create a WebDAV Server with Nginx

Configure a WebDAV server using Nginx on Ubuntu with user authentication, per-user directory access controls, and SSL/TLS encryption via a self-signed certificate.

### Requirements

1. **Install Nginx with WebDAV support**
   - Install `nginx` and the `nginx-extras` package (which includes `libnginx-mod-http-dav-ext` for full WebDAV method support: PROPFIND, OPTIONS, LOCK, UNLOCK, COPY, MOVE).
   - Nginx must be running after setup completes.

2. **Directory structure**
   - Create the WebDAV root directory at `/srv/webdav/`.
   - Create two per-user directories: `/srv/webdav/alice/` and `/srv/webdav/bob/`.
   - All directories under `/srv/webdav/` must be owned by `www-data:www-data` and have permissions `0755`.

3. **User authentication**
   - Create an htpasswd file at `/etc/nginx/.htpasswd`.
   - Add two users with Basic authentication:
     - Username: `alice`, Password: `alice_pass`
     - Username: `bob`, Password: `bob_pass`
   - Passwords must be hashed (not stored in plaintext).

4. **SSL/TLS certificate**
   - Generate a self-signed SSL certificate and key:
     - Certificate: `/etc/nginx/ssl/webdav.crt`
     - Key: `/etc/nginx/ssl/webdav.key`
   - The certificate subject CN must be set to `localhost`.

5. **Nginx configuration**
   - Create or modify the Nginx server block configuration file at `/etc/nginx/sites-enabled/webdav`.
   - The server must listen on HTTPS port `443` with SSL enabled.
   - The `server_name` must be set to `localhost`.
   - WebDAV must be served at the location `/webdav/`.
   - The configuration must:
     - Enable `dav_methods PUT DELETE MKNOD COPY MOVE`.
     - Enable `dav_ext_methods PROPFIND OPTIONS`.
     - Set `dav_access user:rw group:r`.
     - Use Basic authentication with realm `"WebDAV"` and the htpasswd file from step 3.
     - Set `client_body_temp_path /tmp/nginx_dav`.
     - Set `create_full_put_path on`.
     - Set `autoindex on`.
   - Per-user access control: configure separate location blocks for `/webdav/alice/` and `/webdav/bob/` so that each user can only access their own directory. Use Nginx `if` directives or `auth_request` or `map` to restrict access — when a user accesses the other user's directory, Nginx must return HTTP `403 Forbidden`.

6. **Service state**
   - The default Nginx site (`/etc/nginx/sites-enabled/default`) should be removed if it exists, to avoid port conflicts.
   - Nginx configuration must pass `nginx -t` validation.
   - Nginx must be running and enabled after all configuration is complete.

### Verification

After setup, the following should work:

- `curl -k -u alice:alice_pass https://localhost/webdav/alice/` returns HTTP 200 or 207.
- `curl -k -u alice:alice_pass -X PUT -d "hello" https://localhost/webdav/alice/test.txt` succeeds (HTTP 201 or 204).
- `curl -k -u alice:alice_pass https://localhost/webdav/bob/` returns HTTP 403.
- `curl -k -u bob:bob_pass https://localhost/webdav/bob/` returns HTTP 200 or 207.
- `curl -k -u bob:bob_pass https://localhost/webdav/alice/` returns HTTP 403.
- Unauthenticated requests return HTTP 401.
