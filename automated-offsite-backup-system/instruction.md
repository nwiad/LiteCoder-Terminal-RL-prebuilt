## Automated Offsite Backup System

Create a complete automated offsite backup solution consisting of shell scripts and configuration files that handle encrypted incremental backups via rsync, integrity verification, logging, and cron scheduling.

### Technical Requirements

- Language: Bash (compatible with Bash 4+)
- All scripts must be executable (`chmod +x`)
- All output files go under `/app/`

### Files to Produce

1. `/app/backup.sh` — Main backup script
2. `/app/verify_backup.sh` — Pre/post-backup integrity verification script
3. `/app/restore.sh` — Backup restoration script
4. `/app/backup.conf` — Configuration file (sourced by the scripts)
5. `/app/crontab.txt` — Crontab entry file
6. `/app/logrotate.conf` — Logrotate configuration for backup logs

### Configuration File (`backup.conf`)

Must define the following variables (one per line, `KEY=VALUE` format, no spaces around `=`):

- `SOURCE_DIR` — local directory to back up (set to `/app/data`)
- `REMOTE_USER` — remote SSH user (set to `backupuser`)
- `REMOTE_HOST` — remote server hostname (set to `backup.remote.example.com`)
- `REMOTE_DIR` — remote destination directory (set to `/backups/daily`)
- `SSH_KEY` — path to SSH private key (set to `/app/.ssh/backup_key`)
- `LOG_DIR` — directory for log files (set to `/app/logs`)
- `LOG_FILE` — path to the main log file (set to `/app/logs/backup.log`)
- `RETENTION_DAYS` — number of days to retain old backups (set to `30`)
- `CHECKSUM_FILE` — path to store checksums (set to `/app/checksums.sha256`)

### Main Backup Script (`backup.sh`)

- Must source `/app/backup.conf` at the top
- Must create `LOG_DIR` if it does not exist
- Must define and use a logging function that writes timestamped entries (format: `[YYYY-MM-DD HH:MM:SS] MESSAGE`) to both `LOG_FILE` and stdout
- Must call `/app/verify_backup.sh pre` before starting the rsync transfer
- Must invoke `rsync` with at least these flags: `-avz --delete -e` with SSH using the configured key and strict host key checking disabled (`-o StrictHostKeyChecking=no`)
- Must capture the rsync exit code and log whether the backup succeeded or failed
- Must call `/app/verify_backup.sh post` after the rsync transfer
- Must exit with code 0 on success and non-zero on failure
- On rsync failure, must log a line containing the word `FAILED`
- On rsync success, must log a line containing the word `SUCCESS`

### Verification Script (`verify_backup.sh`)

- Must accept a single argument: `pre` or `post`
- Must source `/app/backup.conf`
- In `pre` mode:
  - Check that `SOURCE_DIR` exists and is a directory; exit with code 1 and print an error message containing `SOURCE_DIR` and `not found` (case-insensitive) if it does not
  - Check that `SSH_KEY` file exists; exit with code 1 and print an error containing `SSH key` and `not found` (case-insensitive) if it does not
  - Generate SHA-256 checksums of all files under `SOURCE_DIR` and write them to `CHECKSUM_FILE`
- In `post` mode:
  - Verify the checksums in `CHECKSUM_FILE` against the source files (using `sha256sum -c` or equivalent)
  - Exit with code 0 if verification passes, non-zero otherwise
- If called with an invalid argument (not `pre` or `post`), print a usage message containing the word `Usage` and exit with code 1

### Restoration Script (`restore.sh`)

- Must source `/app/backup.conf`
- Must accept exactly one argument: the local directory to restore into
- If no argument is provided, print a usage message containing the word `Usage` and exit with code 1
- Must create the restore target directory if it does not exist
- Must invoke `rsync` to pull data from `REMOTE_USER@REMOTE_HOST:REMOTE_DIR/` into the specified local directory, using the same SSH key configuration as `backup.sh`
- Must log restore operations with timestamped entries to `LOG_FILE`
- Must exit with code 0 on success and non-zero on failure

### Crontab File (`crontab.txt`)

- Must contain exactly one uncommented cron entry
- The cron job must schedule `/app/backup.sh` to run daily at 2:00 AM
- The cron entry must redirect both stdout and stderr to `/app/logs/cron_backup.log`

### Logrotate Configuration (`logrotate.conf`)

- Must target `/app/logs/backup.log`
- Must specify `daily` rotation
- Must retain at least 7 rotated logs (`rotate 7` or higher)
- Must include `compress` directive
- Must include `missingok` directive
- Must include `notifempty` directive
