## Deploy a Zabbix Monitoring Stack with Docker Compose

Set up a production-ready Zabbix monitoring stack using Docker Compose with separate containers for the database, server, web frontend, and agent, connected via isolated networks with persistent storage.

### Requirements

1. **Docker & Docker Compose:** Ensure Docker and Docker Compose (v2) are installed and functional on the host.

2. **Compose File:** Write a Docker Compose file at `/app/docker-compose.yml`. All services must use `restart: always` (or equivalent) so they come up automatically after reboot.

3. **Docker Networks:** Define exactly two custom bridge networks in the compose file:
   - `zabbix-net` — used by the database, Zabbix server, and Zabbix agent.
   - `zabbix-frontend-net` — used by the Zabbix server and Zabbix web frontend.

4. **Services and Images:** Define the following four services with the exact service names and base images specified:

   | Service Name       | Image Base                               |
   |--------------------|------------------------------------------|
   | `postgres-server`  | `postgres:15`                            |
   | `zabbix-server`    | `zabbix/zabbix-server-pgsql:ubuntu-6.4-latest` |
   | `zabbix-web`       | `zabbix/zabbix-web-nginx-pgsql:ubuntu-6.4-latest` |
   | `zabbix-agent`     | `zabbix/zabbix-agent:ubuntu-6.4-latest`  |

5. **PostgreSQL (`postgres-server`):**
   - Connected to `zabbix-net` only.
   - Environment variables must set: database user `zabbix`, database name `zabbix`, and a non-empty password.
   - A named volume or host bind mount must persist data at the container path `/var/lib/postgresql/data`.

6. **Zabbix Server (`zabbix-server`):**
   - Connected to both `zabbix-net` and `zabbix-frontend-net`.
   - Must expose host port `10051` mapped to container port `10051`.
   - Environment must reference the PostgreSQL connection (host, user, password, database) matching the `postgres-server` configuration.
   - Must mount host directories for alert scripts and external scripts into the container (paths `/usr/lib/zabbix/alertscripts` and `/usr/lib/zabbix/externalscripts` inside the container).
   - Must depend on `postgres-server`.

7. **Zabbix Web Frontend (`zabbix-web`):**
   - Connected to `zabbix-frontend-net` only.
   - Must expose host port `8080` mapped to container port `8080`.
   - Environment must reference the Zabbix server and PostgreSQL connection details matching the other services.
   - Must set the timezone to `UTC` via the `PHP_TZ` environment variable.
   - Must depend on `zabbix-server`.

8. **Zabbix Agent (`zabbix-agent`):**
   - Connected to `zabbix-net` only.
   - Must expose host port `10050` mapped to container port `10050`.
   - Environment variable `ZBX_HOSTNAME` must be set (e.g., `zabbix-agent-host`).
   - Environment variable `ZBX_SERVER_HOST` must point to the Zabbix server service.

9. **Persistent Host Directories:** Create the following directories on the host before starting the stack:
   - `/app/zbx_env/var/lib/postgresql/data`
   - `/app/zbx_env/usr/lib/zabbix/alertscripts`
   - `/app/zbx_env/usr/lib/zabbix/externalscripts`

10. **Stack Startup:** Run the stack from `/app` using `docker compose up -d`. After startup, all four containers must be in `running` state.
