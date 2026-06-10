## DNS Reverse Proxy with DNSMasq

Set up a local DNS reverse proxy using dnsmasq that resolves all `.local` domain queries to a specified IP address, forwards other queries to public DNS, and provides a web server that serves content based on the Host header along with a domain management script.

### Technical Requirements

- **OS:** Linux (Debian/Ubuntu-based)
- **Tools:** dnsmasq, Python 3.x (for web server and management script)
- **Working directory:** `/app`

### 1. DNSMasq Configuration

Install dnsmasq and create a configuration file at `/etc/dnsmasq.d/local-dev.conf` with the following behavior:

- All queries for `*.local` domains must resolve to `127.0.0.1`.
- All other DNS queries must be forwarded to the upstream DNS server `8.8.8.8`.
- dnsmasq must listen on `127.0.0.1`.
- DNS cache size must be set to `1000`.
- dnsmasq must not read `/etc/hosts` (i.e., `no-hosts` must be enabled).
- Logging of DNS queries must be enabled.

After writing the configuration, ensure the dnsmasq service is restarted/started so the configuration takes effect.

### 2. Web Server

Create a Python web server script at `/app/server.py` that:

- Listens on `127.0.0.1` port `8080`.
- Reads the `Host` header from incoming HTTP requests.
- Returns an HTTP `200` response with `Content-Type: application/json`.
- The JSON response body must have the following structure:

```json
{
  "hostname": "<value of Host header, without port>",
  "status": "ok",
  "message": "Welcome to <hostname>"
}
```

- If the `Host` header is missing or empty, return HTTP `400` with:

```json
{
  "hostname": null,
  "status": "error",
  "message": "Missing Host header"
}
```

The server must be runnable via `python3 /app/server.py` and must run in the foreground.

### 3. Domain Management Script

Create a script at `/app/manage_domains.py` that manages custom `.local` domain-to-IP mappings in a JSON file at `/app/domains.json`.

**`/app/domains.json` format:**

```json
{
  "domains": {
    "app1.local": "127.0.0.1",
    "api.local": "127.0.0.2"
  }
}
```

If `/app/domains.json` does not exist, the script must create it with `{"domains": {}}`.

**CLI interface:**

- `python3 /app/manage_domains.py add <domain> <ip>` — Adds or updates a domain mapping. The domain must end with `.local`; otherwise print `Error: Domain must end with .local` to stdout and exit with code `1`. The IP must be a valid IPv4 address; otherwise print `Error: Invalid IPv4 address` to stdout and exit with code `1`. On success, print `Added: <domain> -> <ip>` and exit with code `0`.

- `python3 /app/manage_domains.py remove <domain>` — Removes a domain mapping. If the domain does not exist in the file, print `Error: Domain not found` to stdout and exit with code `1`. On success, print `Removed: <domain>` and exit with code `0`.

- `python3 /app/manage_domains.py list` — Prints all current mappings to stdout, one per line in the format `<domain> -> <ip>`, sorted alphabetically by domain name. If no mappings exist, print `No domains configured` and exit with code `0`.

All successful `add` and `remove` operations must persist changes to `/app/domains.json` immediately.

### 4. System DNS Configuration

Configure the system to use the local dnsmasq instance as its DNS resolver by ensuring `/etc/resolv.conf` has `nameserver 127.0.0.1` as its first entry.
