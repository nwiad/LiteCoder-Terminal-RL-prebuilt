## Multi-VHost Nginx & Application Setup

Set up a single Nginx instance to reverse-proxy three distinct Node.js applications, each on its own virtual host with DNS resolution via `/etc/hosts` and TLS termination.

### Technical Requirements

- **Language/Runtime:** Node.js (current LTS)
- **Reverse Proxy:** Nginx
- **OS Service Manager:** systemd

### Node.js Applications

Create three Node.js applications, one per port:

| Service   | Port   | Hostname       |
|-----------|--------|----------------|
| svc-a     | 3001   | svc-a.test     |
| svc-b     | 3002   | svc-b.test     |
| svc-c     | 3003   | svc-c.test     |

Each application must:
- Listen on its assigned port on `127.0.0.1`.
- Respond to HTTP GET requests on `/` with a JSON body in the following exact format:
  ```json
  {"service":"<vhost-name>","timestamp":"<ISO-8601 UTC timestamp>"}
  ```
  For example, svc-a must return: `{"service":"svc-a.test","timestamp":"2025-01-01T12:00:00.000Z"}` (timestamp varies).
- Return `Content-Type: application/json` header.
- Application source files must be placed at `/app/services/svc-a/index.js`, `/app/services/svc-b/index.js`, `/app/services/svc-c/index.js`.

### TLS Certificate

- Generate a self-signed wildcard certificate for `*.test`.
- Store the certificate at `/etc/ssl/test/wildcard.test.crt`.
- Store the private key at `/etc/ssl/test/wildcard.test.key`.

### DNS Resolution

- Add the following entries to `/etc/hosts`, all pointing to `127.0.0.1`:
  - `svc-a.test`
  - `svc-b.test`
  - `svc-c.test`

### Nginx Configuration

- Create three separate Nginx server block configuration files under `/etc/nginx/sites-enabled/`:
  - `svc-a.test.conf`
  - `svc-b.test.conf`
  - `svc-c.test.conf`
- Each server block must:
  - Listen on port `443` with SSL enabled, using the wildcard certificate and key above.
  - Set `server_name` to the corresponding hostname (e.g., `svc-a.test`).
  - `proxy_pass` requests to the corresponding Node.js application port on `127.0.0.1`.
- Configure a single catch-all server block (in any of the config files or a separate one) that listens on port `80` and issues a `301` permanent redirect from HTTP to HTTPS for all three vhosts.

### Custom Header

- For `svc-a.test` only, Nginx must add a custom response header:
  ```
  X-Service-Id: svc-a.test
  ```
  This header must be present in responses returned through the Nginx proxy on port 443.

### systemd Services

- Create three systemd unit files for the Node.js applications:
  - `/etc/systemd/system/svc-a.service`
  - `/etc/systemd/system/svc-b.service`
  - `/etc/systemd/system/svc-c.service`
- Each unit must:
  - Start the corresponding Node.js application.
  - Be enabled to start on boot.
  - Be in `active (running)` state after setup.
- Nginx service (`nginx.service`) must also be enabled and in `active (running)` state.

### Verification

After setup, the following must all succeed:

1. `curl -sk https://svc-a.test/` returns valid JSON with `"service":"svc-a.test"`.
2. `curl -sk https://svc-b.test/` returns valid JSON with `"service":"svc-b.test"`.
3. `curl -sk https://svc-c.test/` returns valid JSON with `"service":"svc-c.test"`.
4. `curl -sI http://svc-a.test/` returns HTTP 301 with a `Location` header pointing to `https://svc-a.test/`.
5. `curl -skI https://svc-a.test/` includes the header `X-Service-Id: svc-a.test`.
6. All three Node.js systemd services and Nginx are active and enabled.

### Documentation

Write a file `/app/verification.md` containing:
- The three systemd service names.
- The exact `curl` commands used for final verification of each service.
