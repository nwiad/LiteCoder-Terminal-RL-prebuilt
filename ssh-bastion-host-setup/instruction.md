## Secure Remote Administration Hub

Transform this Ubuntu 22.04 container into a hardened, key-only SSH bastion host. The box must expose only an SSH daemon on a non-default port, accept only key-based logins, rate-limit brute-force attempts, and proxy traffic to an internal web service. A non-root sudoer account must be created for a junior admin team, and all services must auto-start on boot.

### Technical Requirements

- **Environment:** Ubuntu 22.04 container (packages may need to be installed via apt)
- **Output file:** `/app/handover.txt`

### 1. System Preparation

- Run a full package update (`apt update && apt upgrade`).
- Remove or disable any unnecessary services that are not required for SSH or nginx operation.

### 2. User Account: `jadmin`

- Create a non-root user named `jadmin`.
- The user's password must be locked (no password-based login allowed; `passwd -S jadmin` must show `L`).
- The user must have sudo privileges (member of the `sudo` group).
- Home directory: `/home/jadmin`.

### 3. SSH Daemon Configuration

The SSH daemon config at `/etc/ssh/sshd_config` (or a drop-in under `/etc/ssh/sshd_config.d/`) must enforce all of the following:

- **Port:** `2222` (not the default 22)
- **PermitRootLogin:** `no`
- **PasswordAuthentication:** `no`
- **PubkeyAuthentication:** `yes`
- **PermitEmptyPasswords:** `no`
- **HostbasedAuthentication:** `no`
- **X11Forwarding:** `no`
- **ClientAliveInterval:** a positive integer value (> 0)
- **ClientAliveCountMax:** a positive integer value (> 0)
- **MaxStartups:** must be explicitly set

An SSH key pair must be generated and the public key installed into `/home/jadmin/.ssh/authorized_keys`. The `.ssh` directory must have permission `700` and `authorized_keys` must have permission `600`, both owned by `jadmin`.

### 4. Fail2ban

- Install and enable `fail2ban`.
- The fail2ban service must be active and running.
- An SSH jail must be enabled that monitors the SSH service on port `2222`. This can be configured via `/etc/fail2ban/jail.local` or a file under `/etc/fail2ban/jail.d/`.

### 5. Nginx Reverse Proxy

- Install nginx.
- Configure nginx to listen on `127.0.0.1:80` and proxy requests to `127.0.0.1:8080`.
- The proxy configuration must include a `proxy_pass` directive pointing to `http://127.0.0.1:8080`.
- Nginx must be running and listening on port 80 on the loopback interface.

### 6. Service Persistence

- Both `sshd` (or `ssh`) and `nginx` services must be enabled to start automatically on boot.
- After a simulated restart of services (`systemctl restart ssh nginx`), both services must come back up healthy and listening on their respective ports.

### 7. Sysctl Hardening

Apply network hardening via `/etc/sysctl.conf` or a file under `/etc/sysctl.d/`. At minimum the following must be set:

- `net.ipv4.conf.all.accept_redirects = 0`
- `net.ipv4.conf.all.send_redirects = 0`

### 8. Handover File

Generate a plain-text file at `/app/handover.txt` containing exactly two sections:

```
LISTENING_PORTS:
<port1>
<port2>
...

KEY_FINGERPRINT:
<SHA256 fingerprint of jadmin's authorized public key>
```

- The `LISTENING_PORTS` section must list each listening port number (one per line, digits only), and must include at least `2222` and `80`.
- The `KEY_FINGERPRINT` section must contain exactly one line with the SHA256 fingerprint of the public key installed for `jadmin` (format: `SHA256:...`).
- No banners, decorative text, or extra commentary in this file.
