## Post-Incident Hardening & Audit Trail

After a suspected breach on an Ubuntu 22.04 web server, implement hardening measures and configure a tamper-evident log pipeline. You have root access in a fresh Ubuntu 22.04 container.

### Technical Requirements

- Environment: Ubuntu 22.04 (container with root access)
- All configuration changes must be made to actual system files
- Final report: `/app/hardening_report.txt`
- Hash-check test script: `/app/verify_logs.sh`
- Log-hash file: `/var/log/log-hashes.txt`

### Tasks

**1. SSH Hardening**

Configure `/etc/ssh/sshd_config` with the following:
- `PermitRootLogin no`
- `PasswordAuthentication no`
- `PubkeyAuthentication yes`
- Change the SSH listen port to `2222`
- Install `fail2ban` and configure it with a jail for sshd that sets `maxretry = 3` and `bantime = 3600`. The fail2ban jail config must be written to `/etc/fail2ban/jail.local`.

**2. Package Cleanup**

Remove non-essential pre-installed packages that are not required for serving static HTML via nginx. Write the list of removed packages (one per line) to `/app/removed_packages.txt`.

**3. Host Firewall**

Configure a stateful firewall using `iptables` or `nftables`. The rules must:
- Allow incoming TCP on ports `2222`, `80`, and `443`
- Allow established/related connections
- Drop all other incoming traffic
- Save the firewall rules to `/app/firewall_rules.txt` (output of `iptables-save` or `nft list ruleset`)

**4. Nginx with Systemd Hardening**

- Install nginx from the official Ubuntu repository
- Create a systemd hardening drop-in file at `/etc/systemd/system/nginx.service.d/hardening.conf`
- The drop-in must include at minimum:
  - `PrivateTmp=yes`
  - `ProtectSystem=strict`
  - `CapabilityBoundingSet=` (restricted capabilities)
  - `NoNewPrivileges=yes`
- Place a minimal static `index.html` at `/var/www/html/index.html` containing the text `Site is operational`.

**5. Deploy User Setup**

- Create a non-privileged user named `deploy` with home directory `/home/deploy`
- Set ownership of `/var/www` to `deploy:deploy`
- Configure command logging for the `deploy` user by adding a script-based session logger in `/home/deploy/.bashrc` that logs terminal sessions to `/var/log/deploy_sessions/`
- Ensure `/var/log/deploy_sessions/` directory exists with appropriate permissions

**6. Rsyslog + TLS Log Forwarding**

- Install `rsyslog` and `rsyslog-gnutls`
- Create rsyslog config at `/etc/rsyslog.d/60-forward.conf` that:
  - Forwards `authpriv`, `kern`, `daemon`, and nginx-related logs
  - Targets `log-receiver.example.com:6514` using TLS (gtls driver)
- Configure logrotate for these logs with 30-day retention in `/etc/logrotate.d/custom-logs`

**7. Log Hash Pipeline**

- Create a script at `/app/hash_logger.sh` that:
  - Reads log entries and appends a SHA-256 hash of each entry to `/var/log/log-hashes.txt`
  - Is executable (`chmod +x`)
- Create a cron job (in `/etc/cron.d/log-hash-ship`) that runs `scp` every hour to ship `/var/log/log-hashes.txt` to `log-receiver.example.com:/var/log/remote/` (with `StrictHostKeyChecking=accept-new`)

**8. Append-Only Log Protection**

- Set the append-only attribute on `/var/log/log-hashes.txt` using `chattr +a`
- Configure an AppArmor profile or local policy so that rsyslogd can still write to its required log paths. Place any AppArmor config under `/etc/apparmor.d/`.

**9. Tamper-Evidence Verification**

Create `/app/verify_logs.sh` (executable) that:
- Reads `/var/log/log-hashes.txt` and verifies the integrity of log entries against their stored hashes
- Exits with code `0` if all hashes are valid
- Exits with code `1` and prints `TAMPER DETECTED` to stdout if any hash mismatch is found

**10. Final Report**

Generate `/app/hardening_report.txt` that contains:
- A section for each task (1 through 9) with a header line formatted as `[Task N]` (e.g., `[Task 1]`, `[Task 2]`, etc.)
- Under each section, list the exact commands run and configuration changes made
- The report must contain all 9 section headers `[Task 1]` through `[Task 9]`
- Total length should not exceed 200 lines
