## Secure File Sharing for Development Team

Configure a secure file-sharing environment on a headless Ubuntu server with authenticated access, automated backups, and audit logging. All configuration must be done via shell commands and config file edits.

### Technical Requirements

- Operating System: Ubuntu (current environment)
- All paths referenced below are absolute paths on the server.

### 1. OpenSSH Server

- Install `openssh-server` if not already installed.
- Ensure the SSH service is enabled.
- Apply the following hardening settings in `/etc/ssh/sshd_config`:
  - `PermitRootLogin no`
  - `PasswordAuthentication no` (key-based auth only)
  - `Port 2222`
  - `MaxAuthTries 3`
  - `X11Forwarding no`
  - `AllowGroups devteam`

### 2. Users and Groups

- Create a group named `devteam`.
- Create the following users and add them to the `devteam` group:
  - `dev_alice`
  - `dev_bob`
  - `dev_charlie`
- Each user must have a home directory created under `/home/`.
- Each user's shell must be set to `/bin/bash`.
- Generate an SSH key pair (Ed25519) for each user, stored in their respective `~/.ssh/` directory. Add each user's public key to their own `~/.ssh/authorized_keys` file with permissions `600`.
- The `~/.ssh/` directory for each user must have permissions `700`.

### 3. Shared Directory

- Create a shared directory at `/srv/devshare`.
- Set ownership to `root:devteam`.
- Set permissions to `2770` (setgid bit set so new files inherit the group).
- Create the following subdirectories inside `/srv/devshare`:
  - `code/`
  - `docs/`
  - `releases/`
- All subdirectories must also be owned by `root:devteam` with permissions `2770`.

### 4. Automated Backups

- Create a backup destination directory at `/srv/backups/devshare`.
- Write a backup script at `/usr/local/bin/devshare_backup.sh` that:
  - Uses `rsync` to sync `/srv/devshare/` to `/srv/backups/devshare/`.
  - Logs backup start time, end time, and status (success/failure) to `/var/log/devshare_backup.log`.
  - The script must be executable (`755`).
- Create a cron job (in `/etc/cron.d/devshare_backup`) that runs the backup script daily at 02:00 as root.

### 5. Backup Verification and Cleanup

- Write a script at `/usr/local/bin/devshare_backup_cleanup.sh` that:
  - Verifies the backup directory `/srv/backups/devshare` exists and is non-empty.
  - Removes backup log entries older than 30 days from `/var/log/devshare_backup.log` (lines with timestamps older than 30 days).
  - Logs its own execution to `/var/log/devshare_cleanup.log`.
  - The script must be executable (`755`).
- Create a cron job (in `/etc/cron.d/devshare_cleanup`) that runs this script every Sunday at 03:00 as root.

### 6. Audit Logging

- Install `auditd` if not already installed.
- Add audit rules to monitor the shared directory. Create or append to `/etc/audit/rules.d/devshare.rules` with:
  - A watch rule on `/srv/devshare` for write, attribute change, read, and execute access (`-p rwxa`) with key `devshare_access`.
- Ensure the auditd service is enabled.

### 7. Fail2ban

- Install `fail2ban` if not already installed.
- Create a jail configuration at `/etc/fail2ban/jail.d/sshd_custom.conf` with:
  - `[sshd]` section
  - `enabled = true`
  - `port = 2222`
  - `maxretry = 3`
  - `bantime = 3600`
  - `findtime = 600`
- Ensure the fail2ban service is enabled.

### 8. Summary Report

Generate a JSON summary report at `/app/output.json` with the following structure:

```json
{
  "ssh": {
    "port": 2222,
    "permit_root_login": false,
    "password_authentication": false,
    "max_auth_tries": 3,
    "allowed_groups": ["devteam"]
  },
  "users": ["dev_alice", "dev_bob", "dev_charlie"],
  "group": "devteam",
  "shared_directory": {
    "path": "/srv/devshare",
    "permissions": "2770",
    "subdirectories": ["code", "docs", "releases"]
  },
  "backup": {
    "source": "/srv/devshare/",
    "destination": "/srv/backups/devshare/",
    "script": "/usr/local/bin/devshare_backup.sh",
    "schedule": "daily at 02:00",
    "log": "/var/log/devshare_backup.log"
  },
  "cleanup": {
    "script": "/usr/local/bin/devshare_backup_cleanup.sh",
    "schedule": "weekly on Sunday at 03:00",
    "log": "/var/log/devshare_cleanup.log"
  },
  "audit": {
    "rules_file": "/etc/audit/rules.d/devshare.rules",
    "watch_path": "/srv/devshare",
    "key": "devshare_access"
  },
  "fail2ban": {
    "jail_config": "/etc/fail2ban/jail.d/sshd_custom.conf",
    "port": 2222,
    "maxretry": 3,
    "bantime": 3600
  }
}
```

All services that are installed must be enabled (but do not need to be actively running if the environment does not support it). All files, directories, scripts, cron jobs, and configurations described above must exist on disk with the specified paths and settings.
