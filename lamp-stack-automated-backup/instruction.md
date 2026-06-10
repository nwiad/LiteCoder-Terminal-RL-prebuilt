## Automated Backup System for a LAMP Stack

Set up an automated backup system that performs scheduled backups of web application files and a MySQL database, with compression, rotation, logging, and cron scheduling.

### Environment Setup

1. Install and configure a working LAMP stack (Apache, MySQL/MariaDB, PHP).
2. Create a sample web application under `/var/www/html/` containing at least:
   - An `index.php` file with PHP content.
   - A `config.php` file.
3. Create a MySQL database named `ecommerce_db` with at least two tables:
   - `customers` (columns: `id` INT PRIMARY KEY AUTO_INCREMENT, `name` VARCHAR(100), `email` VARCHAR(100))
   - `orders` (columns: `id` INT PRIMARY KEY AUTO_INCREMENT, `customer_id` INT, `amount` DECIMAL(10,2), `order_date` DATE)
   - Insert at least 3 rows into each table.

### Backup Directory Structure

Create the following directory layout with permissions `750`:

```
/backup/
├── files/
├── database/
└── logs/
```

### Backup Script

Create an executable Bash backup script at `/app/backup.sh`. The script must:

1. **File Backup**: Archive and compress `/var/www/html/` into a `.tar.gz` file saved under `/backup/files/` with the naming format:
   ```
   files_backup_YYYYMMDD_HHMMSS.tar.gz
   ```

2. **Database Backup**: Dump the `ecommerce_db` database using `mysqldump` and compress it into a `.gz` file saved under `/backup/database/` with the naming format:
   ```
   db_backup_YYYYMMDD_HHMMSS.sql.gz
   ```

3. **Backup Rotation**: Delete backup files (in both `/backup/files/` and `/backup/database/`) that are older than 7 days.

4. **Logging**: Append a log entry for each backup run to `/backup/logs/backup.log`. Each log entry must include:
   - A timestamp in the format `YYYY-MM-DD HH:MM:SS`
   - The status: either `SUCCESS` or `FAILURE`
   - A message describing what was backed up or what failed

   Example log lines:
   ```
   2025-01-15 02:00:01 SUCCESS Files backup completed: files_backup_20250115_020001.tar.gz
   2025-01-15 02:00:05 SUCCESS Database backup completed: db_backup_20250115_020005.sql.gz
   ```
   If any step fails, log a `FAILURE` entry with a description of the error.

5. **Exit Code**: The script must exit with code `0` if all backups succeed, and a non-zero exit code if any step fails.

### Cron Scheduling

Add a cron job for the `root` user that runs `/app/backup.sh` daily at 2:00 AM. The cron entry must be verifiable via `crontab -l`.

### Verification

After setup, run `/app/backup.sh` once manually. After a successful run:
- At least one `.tar.gz` file must exist in `/backup/files/`.
- At least one `.sql.gz` file must exist in `/backup/database/`.
- `/backup/logs/backup.log` must contain at least two `SUCCESS` lines (one for files, one for database).
- The compressed database backup, when decompressed, must contain valid SQL including the `customers` and `orders` tables.
- The compressed file backup, when extracted, must contain the `index.php` and `config.php` files.
