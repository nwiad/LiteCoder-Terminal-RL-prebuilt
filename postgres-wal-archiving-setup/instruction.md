## PostgreSQL WAL Archiving Setup

Configure PostgreSQL WAL (Write-Ahead Log) archiving to a local backup directory (simulating a remote backup server) for continuous backup and point-in-time recovery capabilities.

### Requirements

1. **Install PostgreSQL**: Install PostgreSQL server (version 14 or later) and client utilities. The PostgreSQL service must be running and accepting connections.

2. **Backup User and SSH Key**: Create a dedicated system user named `backupuser`. Generate an SSH key pair (Ed25519 or RSA) for this user at `/home/backupuser/.ssh/id_ed25519` (or `/home/backupuser/.ssh/id_rsa`). The private key must have permissions `600`. Configure SSH so that `backupuser` can connect to `localhost` without a password prompt (authorized_keys setup).

3. **Archive Directory**: Create the directory `/var/lib/postgresql/wal_archive/`. It must be owned by the `postgres` user and have permissions `700`.

4. **PostgreSQL WAL Archiving Configuration**: Modify the active PostgreSQL configuration (`postgresql.conf`) to enable WAL archiving with these settings:
   - `wal_level` set to `replica` (or `logical`)
   - `archive_mode` set to `on`
   - `archive_command` must copy WAL files to `/var/lib/postgresql/wal_archive/` (the command must include `%p` and `%f` placeholders and return a proper exit code)
   - `max_wal_senders` set to at least `3`

   After configuration, restart PostgreSQL so the settings take effect. Verify the settings are active by querying `pg_settings`.

5. **Archive Command Script**: Create an executable script at `/usr/local/bin/archive_wal.sh` that:
   - Copies a WAL file (passed as arguments) to `/var/lib/postgresql/wal_archive/`
   - Includes basic error handling (exits with non-zero on failure)
   - Is executable (permissions include execute bit)
   - Is owned by `postgres`

6. **Verify WAL Archiving**: Force a WAL segment switch (e.g., using `pg_switch_wal()`) and confirm that at least one WAL file appears in `/var/lib/postgresql/wal_archive/`.

7. **Test Database for Recovery**: Create a PostgreSQL database named `ecommerce_test` with a table named `orders` containing at least the columns:
   - `id` (serial primary key)
   - `product_name` (text)
   - `quantity` (integer)
   - `created_at` (timestamp, default `now()`)

   Insert at least 3 rows into the `orders` table.

8. **Backup and Recovery Documentation**: Create a plain text file at `/app/backup_recovery_procedures.txt` that documents:
   - How to perform a base backup
   - How to restore from a WAL archive (point-in-time recovery steps)
   - The file must be non-empty and contain at least 10 lines.

9. **WAL Monitoring Cron Job**: Set up a cron job (in the `postgres` user's crontab) that runs at least once per hour to check WAL archiving status. The cron entry must reference a monitoring script or command. Create the monitoring script at `/usr/local/bin/monitor_wal.sh` — it must be executable and check whether the archive directory contains recent files. The script should write output to `/var/log/wal_monitor.log`.
