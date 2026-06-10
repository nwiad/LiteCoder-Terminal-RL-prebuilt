## Secure Docker Host Hardening

Harden the security of a Docker host by configuring SSH, firewall, Docker daemon, fail2ban, kernel parameters, logging, and login banners according to the requirements below.

### Technical Requirements

- Operating System: Ubuntu 22.04
- All configuration changes must be applied to the actual system config files at their standard paths.

### 1. SSH Daemon Configuration

Edit `/etc/ssh/sshd_config` to apply the following settings:

- Disable root login: `PermitRootLogin no`
- Disable password authentication: `PasswordAuthentication no`
- Set max authentication tries to 3: `MaxAuthTries 3`
- Disable X11 forwarding: `X11Forwarding no`
- Set login grace time to 60 seconds: `LoginGraceTime 60`
- Set client alive interval to 300: `ClientAliveInterval 300`
- Set client alive count max to 2: `ClientAliveCountMax 2`
- Restrict SSH protocol to version 2: `Protocol 2`

### 2. Firewall (UFW) Configuration

Configure UFW with the following rules:

- Default incoming policy: deny
- Default outgoing policy: allow
- Allow SSH (port 22/tcp)
- Allow HTTP (port 80/tcp)
- Allow HTTPS (port 443/tcp)
- Enable UFW

### 3. Docker Daemon Configuration

Create or edit `/etc/docker/daemon.json` with the following JSON settings:

- `"icc": false` (disable inter-container communication)
- `"no-new-privileges": true`
- `"userns-remap": "default"`
- `"log-driver": "json-file"`
- `"log-opts": {"max-size": "10m", "max-file": "3"}`
- `"live-restore": true`
- `"storage-driver": "overlay2"`

The file must be valid JSON.

### 4. File System Permissions

Set the following file permissions:

- `/etc/docker/daemon.json`: mode `644`
- `/etc/ssh/sshd_config`: mode `600`

### 5. Fail2ban Configuration

Install fail2ban and create a jail configuration file at `/etc/fail2ban/jail.local` with an `[sshd]` jail containing:

- `enabled = true`
- `port = ssh`
- `maxretry = 3`
- `bantime = 3600`
- `findtime = 600`

### 6. Kernel Security Parameters

Add or edit `/etc/sysctl.d/99-security.conf` with the following parameters:

- `net.ipv4.ip_forward = 1`
- `net.ipv4.conf.all.send_redirects = 0`
- `net.ipv4.conf.default.send_redirects = 0`
- `net.ipv4.conf.all.accept_redirects = 0`
- `net.ipv4.conf.default.accept_redirects = 0`
- `net.ipv4.conf.all.rp_filter = 1`
- `net.ipv4.conf.default.rp_filter = 1`
- `net.ipv4.icmp_echo_ignore_broadcasts = 1`
- `kernel.randomize_va_space = 2`

### 7. Rsyslog Configuration

Install rsyslog and create `/etc/rsyslog.d/50-docker.conf` that configures Docker container log forwarding to `/var/log/docker-containers.log`. The config file must:

- Contain a reference to `docker` for program name or syslog tag matching
- Specify `/var/log/docker-containers.log` as the output log file path

### 8. Login Security Banner

Create `/etc/issue.net` containing a security warning banner. The banner must:

- Contain the word "authorized" (case-insensitive)
- Contain the word "monitored" (case-insensitive)
- Be at least 50 characters long

Configure SSH to use this banner by setting `Banner /etc/issue.net` in `/etc/ssh/sshd_config`.
