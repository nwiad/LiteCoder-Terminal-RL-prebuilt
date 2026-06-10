## File Integrity Monitoring Deployment

Deploy a self-contained file-integrity-monitoring (FIM) solution on this container that watches `/var/www/html`, stores baselines and change logs under `/var/log/fim/`, and e-mails a daily digest to the local user **security**.

### Requirements

1. **Build Dependencies & Local Mail**
   - Install a C compiler toolchain and a lightweight MTA (e.g., `postfix` or equivalent) configured for local-only delivery.
   - Create the local user `security` (if it does not already exist) so mail can be delivered to `/var/mail/security`.

2. **FIM Engine (C binary)**
   - Write, compile, and install a single-file C program as `/usr/local/bin/fim`.
   - The source file must be saved at `/root/fim.c`.
   - The binary must support at least the following sub-commands:
     - `fim init <directory>` — scan `<directory>` recursively, compute a SHA-256 hash for every regular file, and write the baseline database to `/root/.fim/baseline.db`.
     - `fim check <directory>` — rescan `<directory>`, compare against the baseline, and append any detected changes (added / modified / deleted files) to `/var/log/fim/changes.log`.
     - `fim watch <directory>` — run as a long-lived daemon (background process) that periodically checks `<directory>` and appends changes to `/var/log/fim/changes.log`. It must write its PID to `/var/run/fim.pid`.
   - The baseline database `/root/.fim/baseline.db` must be a text file with one entry per line in the format:
     ```
     <sha256hex>  <filepath>
     ```
     where `<sha256hex>` is the lowercase hex-encoded SHA-256 hash and `<filepath>` is the absolute path of the file.

3. **Directory Structure**
   - `/var/www/html` — the monitored web-root (create if missing).
   - `/var/log/fim/` — log directory.
   - `/root/.fim/` — baseline database directory.

4. **Baseline Initialisation**
   - Run `fim init /var/www/html` to generate the initial baseline.
   - After init, `/root/.fim/baseline.db` must exist and list every regular file under `/var/www/html`.

5. **FIM Daemon**
   - Start the daemon with `fim watch /var/www/html`.
   - The process must be running in the background; `/var/run/fim.pid` must contain its PID, and that PID must correspond to a live process.

6. **Change Log Format**
   - `/var/log/fim/changes.log` must record detected events. Each line must follow the format:
     ```
     <ISO-8601-datetime> <EVENT> <filepath>
     ```
     where `<EVENT>` is one of `ADDED`, `MODIFIED`, or `DELETED`, and `<ISO-8601-datetime>` is like `2025-01-15T08:30:00`.
   - When a file is created in `/var/www/html`, an `ADDED` line must eventually appear; when modified, a `MODIFIED` line; when removed, a `DELETED` line.

7. **Logrotate**
   - Install a logrotate configuration file at `/etc/logrotate.d/fim`.
   - It must rotate `/var/log/fim/*.log` daily, keep 7 rotations, use `compress` and `missingok`.

8. **Cron Job & Daily Digest Mail**
   - Add a cron entry (in root's crontab) that runs daily at 06:00 (i.e., `0 6 * * *`).
   - The cron job must mail the contents of `/var/log/fim/changes.log` (or a summary of it) to the local user `security` with the subject line containing `FIM Daily Digest`.
   - After manually triggering the cron job at least once, `/var/mail/security` must exist and contain a message whose body includes change-log entries and whose headers include `Subject:` with the text `FIM Daily Digest`.

9. **Verification**
   - Create a test file `/var/www/html/test.html` with any HTML content, then modify it, then remove it.
   - After these operations, `/var/log/fim/changes.log` must contain at least one `ADDED`, one `MODIFIED`, and one `DELETED` entry referencing `/var/www/html/test.html`.
