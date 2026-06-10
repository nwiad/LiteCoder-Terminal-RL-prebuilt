## Configuring a Private File Exchange Service

Set up a secure, self-hosted file upload/download service using lighttpd that serves files over HTTPS on port 4443 from a dedicated directory, with Basic Auth protecting uploads while allowing anonymous downloads.

### Requirements

1. **Package Installation**
   - Install `lighttpd` and its TLS/SSL module (e.g., `mod_openssl`).

2. **Service Directory**
   - Create the directory `/srv/filedrop/`.
   - Set ownership so the lighttpd process user (typically `www-data`) can read and write into it.
   - Permissions must allow the web server to create and serve files.

3. **TLS Certificate**
   - Generate a self-signed TLS certificate for the Common Name `filedrop.local`.
   - Store the certificate and key under `/etc/lighttpd/ssl/`.
   - The certificate file must be named `filedrop.local.pem` and the key file `filedrop.local.key` (or a combined PEM file named `filedrop.local.pem` containing both).

4. **Lighttpd Configuration**
   - Listen on port `4443` with HTTPS only (no plain HTTP listener).
   - Enable the necessary modules: at minimum `mod_openssl`, `mod_webdav`, `mod_auth`, `mod_authn_file`.
   - Map the URL path `/drop/` to the physical directory `/srv/filedrop/`.
   - Enable WebDAV on the `/drop/` path so that PUT requests can upload files.

5. **Authentication**
   - Use HTTP Basic Authentication to protect upload methods (PUT, POST) on the `/drop/` path.
   - Create a credential entry with username `partner` and password `DropSecure2025`.
   - Store the credentials in an htdigest or htpasswd file at `/etc/lighttpd/htpasswd`.
   - GET requests (downloads) on `/drop/` must remain open to unauthenticated users.

6. **Systemd Service**
   - Ensure a systemd unit file exists for the lighttpd service.
   - The service must be **enabled** (starts on boot).
   - The service must be **active (running)** after setup is complete.

7. **Verification**
   - After the service is running, upload a test file by executing a curl PUT request:
     Upload a file named `testfile.txt` containing the text `hello filedrop` to `https://localhost:4443/drop/testfile.txt` using the credentials above (use `-k` to skip certificate verification).
   - The uploaded file must be physically present at `/srv/filedrop/testfile.txt` with the content `hello filedrop`.
   - A subsequent anonymous GET request to `https://localhost:4443/drop/testfile.txt` (no credentials, `-k` flag) must return the file content successfully (HTTP 200).
   - An unauthenticated PUT request must be rejected (HTTP 401).

8. **Partner Documentation**
   - Create the file `/root/HELP.txt` containing curl one-liner commands for partners:
     - One line showing how to **upload** a file (using `-u partner:DropSecure2025`, `-T`, `-k`, targeting `https://<host>:4443/drop/<filename>`).
     - One line showing how to **download** a file (anonymous GET with `-k`, targeting `https://<host>:4443/drop/<filename>`).
