## Local DNS Sinkhole with Pi-hole

Deploy a Pi-hole instance inside Docker to block ads/trackers, configure custom blocklists, upstream DNS, and produce a verification report.

### Technical Requirements

- Docker and Docker Compose must be available
- All configuration files under `/app/`
- Python 3.x for the verification script

### Step 1: Docker Compose Configuration

Create `/app/docker-compose.yml` with the following requirements:

- Container name: `pihole`
- Image: `pihole/pihole:latest`
- Port mappings:
  - Host port `5353` → container port `53/tcp` (DNS TCP)
  - Host port `5353` → container port `53/udp` (DNS UDP)
  - Host port `8080` → container port `80/tcp` (Web interface)
- Volumes (bind mounts for persistence):
  - `./etc-pihole` → `/etc/pihole`
  - `./etc-dnsmasq.d` → `/etc/dnsmasq.d`
- Environment variables:
  - `WEBPASSWORD` set to `testpass123`
  - `PIHOLE_DNS_` set to `1.1.1.1;1.0.0.1` (Cloudflare upstream DNS)
  - `TZ` set to `UTC`
- Restart policy: `unless-stopped`

### Step 2: Deploy and Configure

- Start the Pi-hole container using Docker Compose from `/app/`
- The container must be in a running state after deployment
- Add at least 2 custom blocklists (beyond Pi-hole defaults) to the Pi-hole instance. Write the list of added custom blocklist URLs to `/app/custom_blocklists.txt`, one URL per line.

### Step 3: Verification Script and Report

Create and run a Python script `/app/verify.py` that performs the following checks and writes results to `/app/output.json`:

The output JSON must have this exact structure:

```json
{
  "container_running": <bool>,
  "container_name": "pihole",
  "dns_port_mapped": <bool>,
  "web_port_mapped": <bool>,
  "upstream_dns": ["1.1.1.1", "1.0.0.1"],
  "custom_blocklists_count": <int>,
  "dns_resolution_test": {
    "query": "google.com",
    "resolved": <bool>
  },
  "ad_blocking_test": {
    "blocked_domains": [
      {
        "domain": "<known ad domain tested>",
        "blocked": <bool>
      }
    ]
  },
  "web_interface_accessible": <bool>
}
```

Field definitions:
- `container_running`: true if the `pihole` container is in running state
- `dns_port_mapped`: true if host port 5353 is mapped to container port 53
- `web_port_mapped`: true if host port 8080 is mapped to container port 80
- `upstream_dns`: list of configured upstream DNS servers
- `custom_blocklists_count`: number of custom blocklists added (must be >= 2)
- `dns_resolution_test.resolved`: true if `google.com` resolves successfully via Pi-hole DNS at `127.0.0.1:5353`
- `ad_blocking_test.blocked_domains`: test at least 2 known ad-serving domains (e.g., `ads.google.com`, `tracking.example.com`) and report whether each is blocked (resolves to `0.0.0.0` or `NXDOMAIN`)
- `web_interface_accessible`: true if HTTP GET to `http://localhost:8080/admin/` returns status 200

### Expected Output Files

| File | Description |
|---|---|
| `/app/docker-compose.yml` | Docker Compose configuration |
| `/app/custom_blocklists.txt` | Custom blocklist URLs, one per line (>= 2 lines) |
| `/app/verify.py` | Verification script |
| `/app/output.json` | Verification report in the JSON format above |
