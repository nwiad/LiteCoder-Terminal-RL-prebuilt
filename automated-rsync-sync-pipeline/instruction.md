## Networked Secure File Transfer Infrastructure

Build an automated, encrypted file-transfer pipeline between two Ubuntu 22.04 hosts that synchronizes the `/srv/secure-data/` directory nightly with strict key-based authentication and minimal firewall rules.

**Technical Requirements:**
- Platform: Ubuntu 22.04
- Two hosts: "src" (10.0.0.10/24) and "dst" (10.0.0.20/24)
- User: `xfer` with shell `/usr/sbin/nologin`
- SSH: Ed25519 key-based authentication only
- Firewall: UFW allowing only TCP/22 from peer
- Sync tool: rsync with archive, delete-after, and hard-link options
- Automation: systemd timer triggering at 02:17 daily
- Logging: `/var/log/xfer/nightly-sync.log` with logrotate integration

**Implementation Requirements:**

1. **Network Configuration:**
   - Hostname "src" with IP 10.0.0.10/24
   - Hostname "dst" with IP 10.0.0.20/24
   - Bidirectional L3 connectivity verified

2. **User Setup:**
   - User `xfer` exists on both hosts
   - Owns `/srv/secure-data/` directory
   - Shell set to `/usr/sbin/nologin`

3. **SSH Authentication:**
   - Ed25519 key pair generated on src for user `xfer`
   - Public key installed in dst's authorized_keys
   - Key-based login functional from src to dst
   - Root login disabled on dst (PermitRootLogin setting)

4. **Firewall Rules:**
   - UFW installed and enabled on both hosts
   - Only TCP/22 allowed from peer IP address
   - All other incoming traffic denied
   - Rules persist after reboot

5. **Rsync Configuration:**
   - rsync installed on both hosts
   - Command uses archive mode, delete-after, and hard-link options
   - Syncs `/srv/secure-data/` from src to dst

6. **Systemd Automation:**
   - Service unit: `/etc/systemd/system/nightly-sync.service`
   - Timer unit: `/etc/systemd/system/nightly-sync.timer`
   - Timer triggers at 02:17 daily
   - Service executes rsync with specified options
   - Stdout/stderr logged to `/var/log/xfer/nightly-sync.log`

7. **Retry Logic:**
   - Maximum 3 sync attempts on failure
   - 5-minute back-off between retries
   - All attempts logged

8. **Log Management:**
   - Log directory `/var/log/xfer/` exists
   - logrotate configuration for nightly-sync.log

9. **Persistence:**
   - Timer enabled to start on boot
   - Configuration survives system reboot
   - Sync executes successfully after dst reboot

**Verification Points:**
- Network connectivity between hosts
- User `xfer` cannot login interactively
- SSH key authentication works without password
- UFW status shows only port 22 allowed from peer
- Manual rsync completes successfully
- Timer is active and scheduled correctly
- Service logs to specified file
- Root SSH login rejected on dst
- System functions correctly after reboot
