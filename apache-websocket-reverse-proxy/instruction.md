## Apache Reverse Proxy for WebSockets

Configure Apache as a reverse proxy to handle both regular HTTP traffic and WebSocket connections for a Node.js chat application using Socket.IO. The Node.js app runs on port 3000 and must be accessible through Apache on HTTPS (port 443) with SSL termination, and HTTP (port 80) redirecting to HTTPS.

### Technical Requirements

- **OS packages:** Apache2 (with required modules), Node.js (v16.x or higher), npm
- **Apache modules that must be enabled:** `proxy`, `proxy_http`, `proxy_wstunnel`, `ssl`, `rewrite`, `headers`
- **SSL:** Self-signed certificate for testing

### Node.js Chat Application

Create a minimal Socket.IO-based chat application at `/app/chat-app/`:

- `/app/chat-app/package.json` — must declare `express` and `socket.io` as dependencies.
- `/app/chat-app/server.js` — a Node.js server that:
  - Listens on port `3000` on `127.0.0.1`.
  - Serves a static HTML client at the root path (`/`).
  - Uses Socket.IO to handle real-time `chat message` events, broadcasting received messages to all connected clients.
- `/app/chat-app/public/index.html` — a simple HTML chat client that connects to the Socket.IO server, allows sending messages, and displays received messages.

Install dependencies so that `/app/chat-app/node_modules/` exists.

### SSL Certificate

Generate a self-signed SSL certificate and key:

- Certificate: `/etc/ssl/certs/apache-selfsigned.crt`
- Key: `/etc/ssl/private/apache-selfsigned.key`
- Common Name (CN): `localhost`

### Apache Configuration

Create an Apache virtual host configuration file at `/etc/apache2/sites-available/chat-proxy.conf` that includes:

1. **Port 80 VirtualHost:** Redirects all HTTP traffic to HTTPS using a `301` redirect.
2. **Port 443 VirtualHost** with SSL enabled:
   - References the self-signed certificate and key paths above.
   - `ProxyPass` and `ProxyPassReverse` directives that forward `/` to `http://127.0.0.1:3000/`.
   - A `RewriteRule` or `ProxyPass` directive that upgrades WebSocket connections at `/socket.io/` to `ws://127.0.0.1:3000/socket.io/` using `mod_proxy_wstunnel`.
   - Sets `ProxyPreserveHost On`.

Enable this site configuration and disable the default site (`000-default`). Ensure Apache is configured to listen on both port 80 and port 443.

### Verification

After completing all configuration:

1. Start the Node.js chat application (as a background process).
2. Restart or reload Apache so the new configuration is active.
3. Run the following verification checks and write results to `/app/output.json` as a JSON object with these boolean fields:

```json
{
  "apache_running": <true if Apache process is active>,
  "node_app_running": <true if the Node.js app is listening on port 3000>,
  "modules_enabled": <true if all required modules (proxy, proxy_http, proxy_wstunnel, ssl, rewrite, headers) are enabled>,
  "ssl_cert_exists": <true if the certificate and key files exist>,
  "https_accessible": <true if curl to https://localhost/ returns HTTP 200 (use -k for self-signed)>,
  "http_redirects": <true if curl to http://localhost/ returns a 301 redirect to https>,
  "websocket_proxy_configured": <true if the chat-proxy.conf contains wstunnel or ws:// proxy directives>,
  "site_enabled": <true if chat-proxy.conf is enabled in Apache>
}
```
