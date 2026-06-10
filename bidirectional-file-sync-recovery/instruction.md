## Automated File Sync with Failure Recovery

Build a resilient, two-way file synchronisation pipeline between two local directories (`/srv/project_a` and `/srv/project_b`) with automatic failure-recovery, logging, and log rotation.

### Technical Requirements

- Language/Tools: Bash, rsync, inotify-tools, systemd, logrotate
- OS: Linux with systemd

### Deliverables

1. **Sync directories**: Create `/srv/project_a` and `/srv/project_b` with permissions `755`.

2. **Sync script** at `/usr/local/bin/bidirectional_sync.sh`:
   - Must be executable (`chmod +x`).
   - Uses `inotifywait` (from `inotify-tools`) to monitor both directories for file create, modify, delete, and move events.
   - On detecting a change in `/srv/project_a`, syncs to `/srv/project_b` using `rsync`; and vice-versa.
   - Every sync operation must be logged to `/var/log/file_sync.log` with the format:
     ```
     [YYYY-MM-DD HH:MM:SS] <DIRECTION> <EVENT_DESCRIPTION>
     ```
     where `<DIRECTION>` is either `A->B` or `B->A`.
   - Errors must also be logged to `/var/log/file_sync.log` with the prefix `[YYYY-MM-DD HH:MM:SS] ERROR:`.
   - The script must run in a continuous loop (not exit after one event).

3. **systemd service unit** at `/etc/systemd/system/file-sync.service`:
   - `Type=simple`
   - `ExecStart=/usr/local/bin/bidirectional_sync.sh`
   - `Restart=on-failure`
   - `RestartSec=30`
   - The service must be enabled (`systemctl enable file-sync.service`).
   - The service must be started and in `active (running)` state.

4. **logrotate configuration** at `/etc/logrotate.d/file-sync`:
   - Targets `/var/log/file_sync.log`.
   - Rotation frequency: `weekly`.
   - Retains at most `1` rotated log (i.e., `rotate 1`), effectively discarding logs older than seven days.
   - Must include `missingok` and `notifempty` directives.
   - Must include a `compress` directive.

5. **Summary document** at `/root/SYNC_SUMMARY.md`:
   - Must contain a section describing the directory layout (mentioning `/srv/project_a`, `/srv/project_b`, the sync script path, the service unit path, the logrotate config path, and the log file path).
   - Must contain a runbook paragraph explaining how to start, stop, and check the status of the sync service.

### Verification

- Creating a file in `/srv/project_a` must result in that file appearing in `/srv/project_b`, and vice-versa.
- The log file `/var/log/file_sync.log` must contain timestamped entries after sync operations occur.
- If the sync script crashes or is killed, systemd must restart it within 30 seconds.
