## Load Balancer Setup with HAProxy

Generate a complete HAProxy load balancer configuration and supporting artifacts for distributing traffic across three backend web servers with health checks, SSL termination, rate limiting, and logging.

### Technical Requirements

- Language/Tools: Shell scripting (Bash), HAProxy configuration syntax
- All output files must be placed under `/app/`

### Deliverables

1. **HAProxy configuration file:** `/app/haproxy.cfg`
2. **SSL certificate generation script:** `/app/generate_cert.sh`
3. **Status report:** `/app/report.json`

---

### 1. HAProxy Configuration (`/app/haproxy.cfg`)

Write a valid HAProxy configuration file with the following sections and requirements:

**`global` section:**
- Set `maxconn` to 4096
- Configure logging to use `/dev/log` with `local0` facility and `info` level
- Run as daemon
- Specify `chroot` to `/var/lib/haproxy`
- Set user and group to `haproxy`

**`defaults` section:**
- Mode: `http`
- Apply logging from global
- Set `retries` to 3
- Set `timeout connect` to `5000ms`
- Set `timeout client` to `50000ms`
- Set `timeout server` to `50000ms`
- Enable the `httplog` option
- Enable the `dontlognull` option

**`frontend http_front` section:**
- Bind to `*:80`
- Define a default backend named `web_servers`
- Add an ACL and redirect rule so that all HTTP traffic is redirected to HTTPS (301 redirect)

**`frontend https_front` section:**
- Bind to `*:443` with SSL using certificate path `/etc/haproxy/certs/server.pem`
- Set default backend to `web_servers`
- Configure stick-table based rate limiting: track source IPs with a stick-table (type `ip`, size `200k`, expire `30s`, store `http_req_rate(10s)`). Deny requests (HTTP 429) when the rate exceeds 100 requests per 10 seconds.

**`backend web_servers` section:**
- Balance algorithm: `roundrobin`
- Configure HTTP health checks using `option httpchk` with `GET /health`
- Define exactly three servers:
  - `web1` at `192.168.1.101:80`
  - `web2` at `192.168.1.102:80`
  - `web3` at `192.168.1.103:80`
- Each server must have the `check` option enabled, with `inter 5s`, `rise 2`, and `fall 3` parameters.

**`listen stats` section:**
- Bind to `*:8404`
- Enable stats with `stats enable`
- Set stats URI to `/stats`
- Set stats refresh to `10s`
- Set stats realm to `HAProxy\ Statistics`
- Configure stats auth with username `admin` and password `admin123`

---

### 2. SSL Certificate Generation Script (`/app/generate_cert.sh`)

Create an executable Bash script that:
- Creates the directory `/etc/haproxy/certs/` if it does not exist
- Generates a self-signed SSL certificate using `openssl req` with:
  - RSA key size: 2048
  - Validity: 365 days
  - Subject: `/CN=loadbalancer.local`
  - Outputs a combined PEM file at `/etc/haproxy/certs/server.pem` (private key + certificate in one file)
- The script must start with `#!/bin/bash`
- The script must use the `-nodes` flag (no passphrase)
- The script must use the `-x509` flag

---

### 3. Status Report (`/app/report.json`)

Generate a JSON file with the following exact structure:

```json
{
  "load_balancer": {
    "frontend_http_port": 80,
    "frontend_https_port": 443,
    "stats_port": 8404,
    "ssl_certificate_path": "/etc/haproxy/certs/server.pem",
    "rate_limit_requests_per_10s": 100
  },
  "backend_servers": [
    {
      "name": "web1",
      "address": "192.168.1.101",
      "port": 80,
      "health_check_endpoint": "/health",
      "health_check_interval": "5s",
      "rise": 2,
      "fall": 3
    },
    {
      "name": "web2",
      "address": "192.168.1.102",
      "port": 80,
      "health_check_endpoint": "/health",
      "health_check_interval": "5s",
      "rise": 2,
      "fall": 3
    },
    {
      "name": "web3",
      "address": "192.168.1.103",
      "port": 80,
      "health_check_endpoint": "/health",
      "health_check_interval": "5s",
      "rise": 2,
      "fall": 3
    }
  ],
  "balance_algorithm": "roundrobin",
  "logging": {
    "facility": "local0",
    "level": "info"
  }
}
```

The JSON must be valid and parseable. All field names and values must match exactly as specified above.
