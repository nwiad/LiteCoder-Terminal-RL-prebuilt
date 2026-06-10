## High-Availability WordPress Cluster with GlusterFS

Build a resilient three-node WordPress cluster that shares files via GlusterFS and is front-ended by an HAProxy load balancer, all running inside Docker containers on a single host using Docker Compose.

### Technical Requirements

- All configuration must be defined in a single Docker Compose file at `/app/docker-compose.yml`.
- An HAProxy configuration file must be provided at `/app/haproxy.cfg`.
- A cleanup script must be provided at `/app/cleanup.sh` (executable, bash).

### Network

- Define a user-defined bridge network named `wpcluster` in the Compose file.
- All services must be attached to the `wpcluster` network.

### Services

All services below must be defined in `docker-compose.yml`:

1. **GlusterFS nodes** — 3 containers named `gluster1`, `gluster2`, `gluster3`.
   - Use the `gluster/gluster-centos` image (or equivalent GlusterFS image).
   - Each must expose ports `24007/tcp` and `24008/tcp` (mapped to non-conflicting host ports if needed).
   - Together they must form a trusted storage pool and create a replicated volume named `wp-content` with replica count 3.
   - The `wp-content` volume must be mountable at `/var/www/html/wp-content` inside WordPress containers.

2. **MySQL** — 1 container named `wpdb`.
   - Use the `mysql:8.0` image.
   - Environment variables: `MYSQL_ROOT_PASSWORD=rootpass`, `MYSQL_DATABASE=wordpress`, `MYSQL_USER=wpuser`, `MYSQL_PASSWORD=wppass`.
   - Expose port `3306/tcp` internally on the `wpcluster` network (no host port binding required).

3. **WordPress nodes** — 3 containers named `wp1`, `wp2`, `wp3`.
   - Use the `wordpress:latest` image.
   - Environment variables must point to the `wpdb` service: `WORDPRESS_DB_HOST=wpdb`, `WORDPRESS_DB_USER=wpuser`, `WORDPRESS_DB_PASSWORD=wppass`, `WORDPRESS_DB_NAME=wordpress`.
   - Each must mount the GlusterFS `wp-content` replicated volume at `/var/www/html/wp-content`.
   - Each must expose port `80/tcp` internally (no direct host port binding required).

4. **HAProxy** — 1 container named `haproxy`.
   - Use the `haproxy:latest` (or `haproxy:2.8-lts`) image.
   - Bind-mount `/app/haproxy.cfg` into the container as the HAProxy configuration file.
   - Publish host port `80` → container port `80` (frontend traffic).
   - Publish host port `8404` → container port `8404` (stats page).

### HAProxy Configuration (`/app/haproxy.cfg`)

The HAProxy config must satisfy:

- A `frontend` section listening on `*:80` that forwards traffic to a backend.
- A `backend` section named `wordpress_backend` using `roundrobin` balance algorithm.
- The backend must list servers `wp1`, `wp2`, `wp3` on port 80 with HTTP health checks enabled (`option httpchk` with a `GET /` check expecting HTTP 200).
- A `listen stats` section bound to `*:8404` with stats enabled (`stats enable`), accessible at URI `/stats`.

### Cleanup Script (`/app/cleanup.sh`)

- Must be a valid bash script (starting with `#!/bin/bash`).
- Must stop and remove all containers defined in the Compose file and remove the `wpcluster` network.
- The script must be executable (`chmod +x`).

### Verification Criteria

- `docker compose -f /app/docker-compose.yml config` must validate successfully.
- The `wpcluster` network must be defined in the Compose file.
- All 8 services (`gluster1`, `gluster2`, `gluster3`, `wpdb`, `wp1`, `wp2`, `wp3`, `haproxy`) must be defined.
- HAProxy config must contain `roundrobin`, `httpchk`, stats on port `8404`, and references to all three WordPress backends.
- `/app/cleanup.sh` must exist and be executable.
