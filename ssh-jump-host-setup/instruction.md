## Setup a Comprehensive SSH Jump Host with User Restrictions

Configure a hardened SSH jump host (bastion) on this Ubuntu container that allows specific restricted users to connect to an internal target while maintaining audit logs and preventing direct shell access on the jump host itself. The container simulates both the jump host and target server roles.

### Requirements

1. **OpenSSH Server Configuration**
   - OpenSSH server must be installed and running on port `2222` (jump host role).
   - A second SSH server instance must run on port `2223` (simulating the internal target server), using a separate config file at `/etc/ssh/sshd_config_internal`.
   - The main jump host sshd config must be at `/etc/ssh/sshd_config`.

2. **Restricted User Accounts**
   - Create three users: `jumpuser1`, `jumpuser2`, and `jumpadmin`.
   - `jumpuser1` and `jumpuser2` must have their shell set to `/usr/sbin/nologin` (no interactive shell on the jump host).
   - `jumpadmin` must have a normal shell (`/bin/bash`) for administrative purposes.
   - All three users must belong to a group named `jumpers`.

3. **SSH Daemon Hardening (port 2222)**
   - The jump host sshd on port `2222` must have the following settings in `/etc/ssh/sshd_config`:
     - `PasswordAuthentication no`
     - `PermitRootLogin no`
     - `AllowTcpForwarding yes`
     - `GatewayPorts no`
     - `X11Forwarding no`
     - `AllowGroups jumpers`
     - `MaxAuthTries 3`
     - `ClientAliveInterval 300`
     - `ClientAliveCountMax 2`

4. **SSH Key-Based Authentication**
   - Generate an SSH key pair (Ed25519) for each of the three users (`jumpuser1`, `jumpuser2`, `jumpadmin`).
   - Keys must be stored at the default location: `/home/<username>/.ssh/id_ed25519` and `/home/<username>/.ssh/id_ed25519.pub`.
   - Each user's public key must be added to their own `/home/<username>/.ssh/authorized_keys`.
   - The `.ssh` directory must have permission `700` and `authorized_keys` must have permission `600`.

5. **Forced Command Restrictions**
   - For `jumpuser1`, the `authorized_keys` file must contain a forced command restriction that limits the user to only TCP forwarding. The `authorized_keys` entry must include the options: `command="/bin/echo 'No shell access'",no-pty,no-X11-forwarding`.
   - For `jumpuser2`, apply the same forced command restriction as `jumpuser1`.
   - `jumpadmin` must NOT have forced command restrictions.

6. **Logging Configuration**
   - The jump host sshd (port 2222) must set `LogLevel VERBOSE` in `/etc/ssh/sshd_config`.
   - Create a dedicated log file at `/var/log/jump_host_auth.log`.
   - Configure rsyslog (file: `/etc/rsyslog.d/ssh-jump.conf`) to direct auth/authpriv facility messages to `/var/log/jump_host_auth.log`.
   - Ensure the rsyslog service is running.

7. **Internal Target Server (port 2223)**
   - The second sshd instance on port `2223` must use config file `/etc/ssh/sshd_config_internal`.
   - It must allow `PasswordAuthentication no` and `PermitRootLogin no`.
   - `jumpadmin` must be able to authenticate to port `2223` using their SSH key.

8. **Verification Script**
   - Create a script at `/app/verify_setup.sh` that outputs a JSON report to `/app/verification_report.json`.
   - The JSON report must contain the following top-level keys with boolean values:
     - `sshd_running_2222`: whether sshd is listening on port 2222
     - `sshd_running_2223`: whether sshd is listening on port 2223
     - `jumpuser1_exists`: whether user jumpuser1 exists
     - `jumpuser2_exists`: whether user jumpuser2 exists
     - `jumpadmin_exists`: whether user jumpadmin exists
     - `jumpuser1_nologin`: whether jumpuser1's shell is `/usr/sbin/nologin`
     - `jumpuser2_nologin`: whether jumpuser2's shell is `/usr/sbin/nologin`
     - `jumpadmin_bash`: whether jumpadmin's shell is `/bin/bash`
     - `jumpers_group_exists`: whether the `jumpers` group exists
     - `key_auth_jumpuser1`: whether `/home/jumpuser1/.ssh/authorized_keys` exists and is non-empty
     - `key_auth_jumpuser2`: whether `/home/jumpuser2/.ssh/authorized_keys` exists and is non-empty
     - `key_auth_jumpadmin`: whether `/home/jumpadmin/.ssh/authorized_keys` exists and is non-empty
     - `log_file_exists`: whether `/var/log/jump_host_auth.log` exists
     - `rsyslog_configured`: whether `/etc/rsyslog.d/ssh-jump.conf` exists and is non-empty
   - Example output format for `/app/verification_report.json`:
     ```json
     {
       "sshd_running_2222": true,
       "sshd_running_2223": true,
       "jumpuser1_exists": true,
       "jumpuser2_exists": true,
       "jumpadmin_exists": true,
       "jumpuser1_nologin": true,
       "jumpuser2_nologin": true,
       "jumpadmin_bash": true,
       "jumpers_group_exists": true,
       "key_auth_jumpuser1": true,
       "key_auth_jumpuser2": true,
       "key_auth_jumpadmin": true,
       "log_file_exists": true,
       "rsyslog_configured": true
     }
     ```
