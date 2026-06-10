## Custom DNS Server Setup with Web Dashboard

Set up a custom DNS server using dnsmasq that resolves specific domains to custom IP addresses, managed through a Python Flask web dashboard with a REST API.

### Technical Requirements

- **Language/Framework:** Python 3 with Flask
- **DNS Server:** dnsmasq
- **Flask app file:** `/app/dns_dashboard/app.py`
- **Flask port:** 5000 (host `0.0.0.0`)
- **Domain mappings persistence file:** `/app/dns_dashboard/mappings.json`
- **dnsmasq custom config file:** `/etc/dnsmasq.d/custom_domains.conf`

### Data Format

`/app/dns_dashboard/mappings.json` stores all domain-to-IP mappings as a JSON array:

```json
[
  {"domain": "app.local", "ip": "192.168.1.10"},
  {"domain": "api.local", "ip": "192.168.1.20"}
]
```

Each entry must have both `domain` (non-empty string) and `ip` (valid IPv4 address) fields.

### dnsmasq Configuration

Each mapping must produce a line in `/etc/dnsmasq.d/custom_domains.conf` in the format:

```
address=/app.local/192.168.1.10
address=/api.local/192.168.1.20
```

After writing the config file, dnsmasq must be restarted to apply changes.

### REST API Endpoints

All API endpoints consume and produce `application/json`.

**1. GET /api/domains**

Returns all current domain mappings.

- Response `200`:
```json
{"domains": [{"domain": "app.local", "ip": "192.168.1.10"}]}
```

**2. POST /api/domains**

Adds a new domain mapping.

- Request body:
```json
{"domain": "app.local", "ip": "192.168.1.10"}
```
- Response `201`:
```json
{"message": "Domain added successfully", "domain": "app.local", "ip": "192.168.1.10"}
```
- Response `400` if `domain` or `ip` is missing/empty:
```json
{"error": "Domain and IP are required"}
```
- Response `409` if the domain already exists:
```json
{"error": "Domain already exists"}
```

**3. DELETE /api/domains/<domain>**

Deletes a domain mapping by domain name.

- Response `200`:
```json
{"message": "Domain deleted successfully"}
```
- Response `404` if domain not found:
```json
{"error": "Domain not found"}
```

**4. POST /api/restart**

Restarts the dnsmasq service to apply configuration changes.

- Response `200`:
```json
{"message": "DNS server restarted successfully"}
```
- Response `500` if restart fails:
```json
{"error": "Failed to restart DNS server"}
```

### Web Dashboard

The Flask app must serve an HTML page at `GET /` that provides a simple interface to:
- View all current domain mappings
- Add a new domain mapping (form with domain and IP fields)
- Delete an existing mapping

### Systemd Services

- Configure a systemd service file at `/etc/systemd/system/dns-dashboard.service` to run the Flask app.
- Ensure dnsmasq is installed and its service is enabled.

### Persistence Behavior

- On startup, the Flask app must load existing mappings from `/app/dns_dashboard/mappings.json`. If the file does not exist, start with an empty list.
- Every add or delete operation must update both `mappings.json` and `/etc/dnsmasq.d/custom_domains.conf`, then restart dnsmasq.
