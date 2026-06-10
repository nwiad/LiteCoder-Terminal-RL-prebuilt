## Custom Web Proxy with Authentication

Build a Python 3 HTTP proxy server that adds Basic Authentication to all proxied requests, logs traffic details, and forwards requests to target servers. The proxy must be self-contained (no external proxy frameworks like Squid, Nginx, mitmproxy, etc.) and use only Python standard library modules.

### Technical Requirements

- Language: Python 3
- Proxy script: `/app/proxy.py`
- Log file: `/var/log/proxy.log` (permissions: 644, readable by any user)
- Startup script: `/app/start_proxy.sh` (a shell script that starts the proxy in the background)
- The proxy must listen on `127.0.0.1:8080`

### Proxy Behavior

1. **HTTP Forwarding:** Accept and forward standard HTTP requests (GET, POST, etc.) to the intended target server, returning the response to the client.

2. **HTTPS Tunneling:** Accept CONNECT method requests for HTTPS tunneling and establish a tunnel to the target server.

3. **Basic Authentication:**
   - Valid credentials: username=`devuser`, password=`devpass`
   - Every request to the proxy MUST include a `Proxy-Authorization` header with valid Basic Authentication credentials.
   - If the header is missing or credentials are invalid, the proxy MUST respond with HTTP status `407 Proxy Authentication Required` and include a `Proxy-Authenticate: Basic realm="Proxy"` response header.
   - Credentials are checked using standard HTTP Basic Authentication encoding (Base64 of `username:password`).

4. **Logging:** Every processed request (both successful and rejected) must be logged to `/var/log/proxy.log`. Each log entry is a single line in pipe-delimited format with exactly these 5 fields:

   ```
   <timestamp>|<user>|<method>|<url>|<status_code>
   ```

   - `timestamp`: ISO 8601 format (e.g., `2025-01-15T10:30:00`)
   - `user`: The authenticated username, or `-` if authentication failed or was not provided
   - `method`: The HTTP method (GET, POST, CONNECT, etc.)
   - `url`: The full request URL or host:port for CONNECT
   - `status_code`: The HTTP response status code returned to the client (e.g., `200`, `407`)

### Startup Script

`/app/start_proxy.sh` must:
- Start the proxy server in the background
- Be executable (`chmod +x`)
- Exit cleanly after launching the proxy (i.e., not block)

### Demonstration Requirements

The proxy must correctly handle these scenarios when tested via `curl`:
- A request with valid credentials through the proxy to an HTTP URL returns the target's response.
- A request with no `Proxy-Authorization` header returns `407`.
- A request with invalid credentials returns `407`.
