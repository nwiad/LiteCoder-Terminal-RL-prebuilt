## Multi-Container Web-App with Persistent Data and Reverse-Proxy

Build a production-ready, multi-tier WordPress application with data persistence and an nginx reverse-proxy gateway, all containerised and isolated on a custom Docker bridge network.

### Requirements

1. **Docker Network**: Create a user-defined bridge network named `charity_net` with subnet `172.30.0.0/16` and gateway `172.30.0.1`.

2. **Nginx Reverse Proxy**:
   - Write a Dockerfile at `/app/Dockerfile.nginx` that builds a custom nginx image.
   - The image must enable SSL using a self-signed certificate and reverse-proxy HTTPS traffic to the WordPress container on port 80.
   - Tag the built image as `charity/nginx:latest`.
   - Run it as a container named `proxy`, attached only to `charity_net`.
   - The proxy container must publish port 443 to the host (i.e., `https://localhost` reaches the proxy).

3. **WordPress Container**:
   - Run an official `wordpress` image container named `wordpress` on `charity_net`.
   - Assign static IPv4 address `172.30.0.3`.
   - Set restart policy to `unless-stopped`.
   - Do NOT expose any host ports directly.
   - Configure environment variables to connect to the `db` container (host: `db`, database: `wordpress`, user: `wordpress`, password: `wordpress_pass`).

4. **MySQL 8 Container**:
   - Run an official `mysql:8` image container named `db` on `charity_net`.
   - Assign static IPv4 address `172.30.0.2`.
   - Set restart policy to `unless-stopped`.
   - Do NOT expose any host ports directly.
   - Set environment variables: `MYSQL_ROOT_PASSWORD=root_pass`, `MYSQL_DATABASE=wordpress`, `MYSQL_USER=wordpress`, `MYSQL_PASSWORD=wordpress_pass`.

5. **Persistent Volume**: Create a Docker volume named `mysql_data` and mount it at `/var/lib/mysql` in the `db` container.

6. **Image Export**: Save the custom nginx image to a tar file at `/app/charity-nginx.tar` using `docker save`.

7. **Docker Compose File**: Generate a file at `/app/stack.yml` in Docker Compose v3 format (version field `"3"` or any `"3.x"` variant) that declaratively describes the entire setup:
   - All three services (`proxy`, `wordpress`, `db`) with the same configurations described above.
   - The `charity_net` network definition with the specified subnet and gateway.
   - The `mysql_data` volume definition.
   - The `proxy` service must reference the local build context for the nginx Dockerfile.

8. **Stack Lifecycle**: Stop and remove the running containers (leave the network and volume intact), then bring up the entire stack using `docker compose -f /app/stack.yml up -d` (or `docker-compose`) and confirm all three services are running.

### Deliverables

| Artifact | Path |
|---|---|
| Nginx Dockerfile | `/app/Dockerfile.nginx` |
| Nginx image tar | `/app/charity-nginx.tar` |
| Docker Compose file | `/app/stack.yml` |

### Final State

After all steps are complete, the following must hold true:

- `docker network inspect charity_net` shows subnet `172.30.0.0/16` and gateway `172.30.0.1`.
- `docker volume inspect mysql_data` succeeds.
- Three containers (`proxy`, `wordpress`, `db`) are running (status `Up`) on `charity_net`.
- The `db` container has static IP `172.30.0.2` and the `wordpress` container has static IP `172.30.0.3`.
- No host ports are published for `wordpress` or `db`.
- The `proxy` container can reach the `wordpress` container by hostname (HTTP 200 or 301/302 redirect from WordPress).
- `/app/charity-nginx.tar` is a valid Docker image archive containing the `charity/nginx:latest` image.
- `/app/stack.yml` is valid YAML, uses Compose v3 format, and defines services `proxy`, `wordpress`, and `db`, network `charity_net`, and volume `mysql_data`.
