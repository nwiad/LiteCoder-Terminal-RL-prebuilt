## Configuring Docker Logging on Ubuntu

Set up centralized logging for Docker containers using the syslog logging driver, with rsyslog receiving logs and logrotate managing log rotation.

### Technical Requirements

- Operating System: Ubuntu (with systemd)
- Services: Docker, rsyslog
- Tools: logrotate

### Task Steps

**1. Configure rsyslog to receive Docker container logs**

- Create an rsyslog configuration file at `/etc/rsyslog.d/30-docker.conf`.
- This configuration must:
  - Listen for syslog messages on UDP port `514`.
  - Listen for syslog messages on TCP port `514`.
  - Filter messages with the syslog tag starting with `docker/` and write them to `/var/log/docker/containers.log`.
  - Stop processing matched messages after writing (do not duplicate to other log files).
- Ensure the rsyslog service is restarted/reloaded after configuration changes.

**2. Create the Docker log directory structure**

- Create the directory `/var/log/docker/`.
- Set ownership to `syslog:adm`.
- Set permissions to `0755`.

**3. Configure Docker daemon to use syslog logging driver globally**

- Create or modify the Docker daemon configuration file at `/etc/docker/daemon.json`.
- The file must be valid JSON containing at minimum:
  - `"log-driver"` set to `"syslog"`
  - `"log-opts"` object containing:
    - `"syslog-address"` set to `"udp://127.0.0.1:514"`
    - `"tag"` set to `"docker/{{.Name}}"`
- Restart the Docker service after applying the configuration.

**4. Configure log rotation for Docker container logs**

- Create a logrotate configuration file at `/etc/logrotate.d/docker-containers`.
- The configuration must target `/var/log/docker/containers.log` and include:
  - Rotate daily.
  - Keep 7 rotated log files.
  - Use `compress` for rotated files.
  - Use `delaycompress` (do not compress the most recently rotated file).
  - Handle missing log files gracefully (`missingok`).
  - Do not error on empty log files (`notifempty`).
  - Set file creation mode to `0640`, owner `syslog`, group `adm`.
  - Include a `postrotate` script that sends HUP signal to rsyslog to reopen log files (e.g., via `systemctl reload rsyslog` or equivalent).

**5. Verify the configuration**

- Run a test Docker container that produces log output: `docker run --name logtest --rm alpine echo "docker-logging-test-message"`.
- After running, confirm that the message `docker-logging-test-message` appears in `/var/log/docker/containers.log`.
- Validate that the logrotate configuration has correct syntax by running: `logrotate -d /etc/logrotate.d/docker-containers` (dry run, should exit without errors).
