## Local DNS Hijacking for Development Testing

Redirect a specific domain (`example.com`) to a local web server by modifying the system's hosts file and configuring a web server, simulating DNS hijacking for development testing.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based)
- **Web Server:** nginx
- **Working Directory:** /app

### Steps

1. **Install nginx** on the local machine.

2. **Create an HTML page** at `/var/www/html/index.html` with the following exact content:
   ```html
   <html>
   <head><title>Local Dev - example.com</title></head>
   <body><h1>Welcome to the local version of example.com</h1></body>
   </html>
   ```

3. **Configure nginx** to serve the HTML page on port 80:
   - The server must respond to requests with `Host: example.com`.
   - The nginx configuration file for this site should be placed at `/etc/nginx/sites-available/example.com.conf`.
   - A symbolic link must be created at `/etc/nginx/sites-enabled/example.com.conf` pointing to the file above.
   - The `server_name` directive must be set to `example.com`.
   - The `root` directive must point to `/var/www/html`.
   - Ensure nginx is running and serving requests after configuration.

4. **Modify the hosts file** (`/etc/hosts`) to redirect `example.com` to `127.0.0.1`:
   - Add an entry mapping `example.com` to `127.0.0.1`.
   - Do not remove or alter any existing entries in `/etc/hosts`.

5. **Verify the setup** and write a verification report to `/app/output.json` in the following JSON format:
   ```json
   {
     "hosts_entry_added": true,
     "nginx_running": true,
     "curl_example_com": "<full HTML body returned by: curl -s http://example.com>",
     "ping_resolves_to": "<IP address that example.com resolves to, extracted from ping output>",
     "normal_dns_unaffected": true
   }
   ```
   - `hosts_entry_added`: `true` if `/etc/hosts` contains a line mapping `example.com` to `127.0.0.1`.
   - `nginx_running`: `true` if nginx process is active and listening on port 80.
   - `curl_example_com`: The raw HTML string returned by `curl -s http://example.com`. Must match the HTML page created in Step 2.
   - `ping_resolves_to`: The resolved IP address for `example.com` as shown by `ping -c 1 example.com`. Should be `127.0.0.1`.
   - `normal_dns_unaffected`: `true` if DNS resolution for domains other than `example.com` (e.g., `google.com`) is not affected by the hosts file change (i.e., `google.com` does NOT resolve to `127.0.0.1`).

6. **Write a removal guide** to `/app/removal_guide.txt` that documents:
   - How to revert the `/etc/hosts` change (the exact line to remove).
   - How to disable and stop the nginx site configuration.
   - The file must contain at least 3 non-empty lines.
