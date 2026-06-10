## Hardening SSH Access on a Corporate Server

Harden the SSH server configuration on an Ubuntu server to comply with CIS Benchmark recommendations, while preserving administrative access for authorized users.

### Requirements

1. **Backup**: Copy the current SSH server configuration file `/etc/ssh/sshd_config` to `/etc/ssh/sshd_config.bak` before making any changes.

2. **SSH Configuration**: Modify `/etc/ssh/sshd_config` to apply the following settings:

   - `Protocol 2` — only allow SSH protocol version 2.
   - `PermitRootLogin no` — disable root login via SSH.
   - `AllowUsers alice bob` — restrict SSH access to only these two users.
   - `PasswordAuthentication no` — disable password authentication.
   - `PubkeyAuthentication yes` — enforce key-based authentication.
   - `Port 9222` — use non-standard SSH port 9222.
   - `ClientAliveInterval 300` — set client alive check interval to 300 seconds.
   - `ClientAliveCountMax 0` — disconnect idle clients immediately after missed alive check.
   - `X11Forwarding no` — disable X11 forwarding.
   - `AllowTcpForwarding no` — disable TCP forwarding/tunneling.
   - `StrictModes yes` — enable strict mode for host key and file permission checks.
   - `MaxAuthTries 4` — limit authentication attempts to 4.
   - `IgnoreRhosts yes` — ignore rhosts-based authentication.
   - `HostbasedAuthentication no` — disable host-based authentication.
   - `PermitEmptyPasswords no` — disallow empty passwords.
   - `LogLevel INFO` — set logging level to INFO.

3. **Firewall**: Configure `ufw` to:
   - Allow incoming connections on port `9222/tcp`.
   - Deny incoming connections on port `22/tcp` (default SSH port).
   - Ensure `ufw` is active and enabled.

4. **SSH Banner**: Create a warning banner file at `/etc/ssh/banner.txt` with the following exact content:
   ```
   Authorized access only. All activity is monitored and logged.
   ```
   Set the `Banner` directive in `sshd_config` to `/etc/ssh/banner.txt`.

5. **Service**: Restart the SSH service (`sshd`) after applying all configuration changes.

6. **Change Log**: Write a summary of all changes made to `/app/ssh_hardening_log.txt`. The log file must contain at least the following keywords (one per relevant change): `Protocol`, `PermitRootLogin`, `AllowUsers`, `PasswordAuthentication`, `Port`, `ClientAliveInterval`, `X11Forwarding`, `StrictModes`, `Banner`, `ufw`.
