## Password-Protected Web App with PAM and Docker Secrets

Securely deploy a Python Flask web application that authenticates users via PAM against the container's `/etc/shadow`, with all credentials and TLS material injected through Docker Swarm Secrets.

### Technical Requirements

- Language/Framework: Python 3.x with Flask
- Container Runtime: Docker with Swarm mode (`docker stack deploy`)
- OS Base Image: Ubuntu 22.04
- All project files must reside under `/app/`

### Project Structure

Produce the following files at minimum:

```
/app/
├── app.py                  # Flask application
├── Dockerfile              # Container image build
├── docker-stack.yml        # Docker Swarm stack definition
├── fail2ban/
│   ├── jail.local          # fail2ban jail configuration
│   └── filter.d/
│       └── flask-auth.conf # fail2ban filter for Flask auth failures
├── generate_certs.sh       # Script to generate self-signed TLS cert+key
├── entrypoint.sh           # Container entrypoint script
└── README.md               # Ops team documentation
```

### Flask Application (`app.py`)

1. The app must listen on port `5000` inside the container.
2. Routes:
   - `POST /login` — Accepts `application/x-www-form-urlencoded` with fields `username` and `password`. Authenticates the user via PAM against the container's local `/etc/shadow`.
     - On success: return HTTP `200` with JSON body `{"status": "ok", "user": "<username>"}`.
     - On failure: return HTTP `401` with JSON body `{"status": "error", "message": "authentication failed"}`.
   - `GET /health` — Returns HTTP `200` with JSON body `{"status": "healthy"}`. This endpoint does **not** require authentication.
3. Every failed login attempt must be logged to `/var/log/flask-auth.log` in the format:
   ```
   YYYY-MM-DD HH:MM:SS FAILED LOGIN for <username> from <source_ip>
   ```
4. The app must serve HTTPS using the TLS certificate and key provided via Docker Secrets (mounted at `/run/secrets/tls_cert` and `/run/secrets/tls_key`).

### Dockerfile

1. Base image: `ubuntu:22.04`.
2. Install at minimum: `python3`, `python3-pip`, `libpam0g-dev`, `fail2ban`, `openssl`.
3. Install Python packages: `flask`, `python-pam`.
4. Copy application files and fail2ban configuration into the image.
5. Use `entrypoint.sh` as the container entrypoint.
6. Expose port `5000`.

### Docker Swarm Stack (`docker-stack.yml`)

1. Define a single service named `dashboard`.
2. The service must declare the following external secrets:
   - `tls_cert` — the PEM-encoded certificate file
   - `tls_key` — the PEM-encoded private key file
   - `shadow_file` — the `/etc/shadow` content for allowed users
3. Map container port `5000` to host port `8443`.
4. The stack must be deployable with: `docker stack deploy -c docker-stack.yml dashboard`

### Self-Signed Certificate Generation (`generate_certs.sh`)

1. Must be a standalone bash script that generates:
   - `/app/certs/server.crt` (PEM certificate, valid for at least 365 days, CN=localhost)
   - `/app/certs/server.key` (PEM RSA private key, minimum 2048 bits)
2. The script must create the `/app/certs/` directory if it does not exist.
3. Exit with code `0` on success.

### Entrypoint Script (`entrypoint.sh`)

1. On container start, copy `/run/secrets/shadow_file` to `/etc/shadow` and set permissions to `640`.
2. Start `fail2ban` service.
3. Launch the Flask application in the foreground.

### fail2ban Configuration

1. Jail (`fail2ban/jail.local`):
   - Monitor `/var/log/flask-auth.log`.
   - Ban an IP after `3` failed attempts within `300` seconds (5 minutes).
   - Ban duration: `600` seconds (10 minutes).
2. Filter (`fail2ban/filter.d/flask-auth.conf`):
   - Match the log format produced by the Flask app for failed logins.
   - Extract the source IP from log lines.

### Secret Rotation

The design must support rotating the `shadow_file` secret without rebuilding the image or restarting the container. Document the exact rotation procedure in `README.md`. The `entrypoint.sh` (or a watcher mechanism) must detect when the secret file changes and re-apply it to `/etc/shadow`.

### README.md

Provide operational documentation that includes:
1. Prerequisites (Docker, Swarm init).
2. How to build the image.
3. How to create Docker secrets from the generated files.
4. How to deploy the stack.
5. How to test a successful login (example `curl` command).
6. How to test a failed login and observe the IP ban.
7. How to rotate the shadow secret without downtime.
