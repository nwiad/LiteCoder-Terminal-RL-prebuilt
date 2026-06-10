## Network Service Resilience Tuning

Build a fully containerized two-node HAProxy + Keepalived active/passive failover stack using Docker Compose. The active node owns a virtual IP (VIP) and forwards HTTP traffic to backend Nginx servers. If the active node fails, Keepalived must move the VIP to the standby node automatically.

### Requirements

All project files must be created under `/app/`.

#### 1. Docker Compose File

- File: `/app/docker-compose.yml`
- Must define the following services:
  - `haproxy-master`: Active HAProxy + Keepalived node (priority MASTER)
  - `haproxy-backup`: Standby HAProxy + Keepalived node (priority BACKUP)
  - `web1`: Nginx backend server 1
  - `web2`: Nginx backend server 2
- Must define a custom Docker network named `ha_network` using the `bridge` driver with subnet `172.30.0.0/24`.
- The VIP `172.30.0.200` must be managed by Keepalived across the two HAProxy nodes.
- `haproxy-master` and `haproxy-backup` containers must have `cap_add: - NET_ADMIN` to allow VIP management.
- Both HAProxy nodes must use a custom image built from a Dockerfile (see below).
- `web1` and `web2` must use the `nginx:alpine` image and be connected to `ha_network`.

#### 2. Custom Dockerfile

- File: `/app/Dockerfile`
- Based on a lightweight Linux base image (e.g., `alpine`).
- Must install both `haproxy` and `keepalived` inside the image.
- Must copy the configuration files and health-check script into the image.
- Must define an entrypoint or command that starts both `keepalived` and `haproxy` within the same container.

#### 3. HAProxy Configuration

- File: `/app/haproxy.cfg`
- Must contain a `frontend` section that binds to `*:80`.
- Must contain a `backend` section that load-balances (round-robin) across `web1` and `web2` using their container hostnames on port 80.
- Must include a `stats` section accessible on port `8404` at path `/stats`.
- Must enable HTTP health checks for the backend servers.

#### 4. Keepalived Configuration

Two configuration files, one per node:

- `/app/keepalived-master.conf` — for the MASTER node
- `/app/keepalived-backup.conf` — for the BACKUP node

Each file must define:
- A `vrrp_script` block that calls the health-check script to verify HAProxy is running.
- A `vrrp_instance` block with:
  - `virtual_router_id`: `51`
  - `interface`: `eth0`
  - `virtual_ipaddress`: `172.30.0.200/24`
  - MASTER priority: `101`
  - BACKUP priority: `100`
  - `advert_int`: `1`

#### 5. Health-Check Script

- File: `/app/check_haproxy.sh`
- A shell script that checks whether HAProxy is running/responsive.
- Must exit with code `0` if HAProxy is healthy, non-zero otherwise.
- Must be executable (`chmod +x`).

#### 6. Backend Web Servers

- `web1` must serve a page containing the text `web1`.
- `web2` must serve a page containing the text `web2`.
- Custom HTML files:
  - `/app/web1/index.html` — contains at minimum `<h1>web1</h1>`
  - `/app/web2/index.html` — contains at minimum `<h1>web2</h1>`
- These directories must be volume-mounted into the respective Nginx containers at `/usr/share/nginx/html`.

### Validation Criteria

- `docker compose -f /app/docker-compose.yml config` must succeed (valid compose syntax).
- The compose file must define exactly the 4 services listed above and the `ha_network` network.
- `haproxy.cfg` must contain `frontend`, `backend`, and `stats` sections.
- Both keepalived config files must reference `virtual_router_id 51`, VIP `172.30.0.200`, and the health-check script.
- `check_haproxy.sh` must be a valid shell script (starts with `#!/bin/sh` or `#!/bin/bash`) and be executable.
- `web1/index.html` and `web2/index.html` must exist and contain their respective identifiers.
