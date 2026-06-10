## Container Image Backup and Transfer

Set up a versioned backup and transfer system for container images, including a local registry, backup script with retention policy, scheduled execution, and documentation.

### Technical Requirements

- Docker must be installed and configured to start on boot (enabled via systemd).
- All scripts and output files reside under `/app`.

### 1. Local Docker Registry

- Run a local Docker registry as a container named `backup-registry` using the `registry:2` image.
- The registry must listen on host port `5000` (mapped to container port 5000).
- The registry container must have restart policy `always`.

### 2. Backup Script

Create an executable Bash script at `/app/backup.sh` that:

- Accepts two arguments: `<image_name>` (e.g., `myapp`) and `<version>` (e.g., `1.0.3`).
- Tags the local image `<image_name>:latest` as `localhost:5000/<image_name>:<version>`.
- Pushes the tagged image to the local backup registry at `localhost:5000`.
- After a successful push, appends a JSON line to `/app/backup_log.json` with the following format (one JSON object per line, JSONL format):

```
{"image":"<image_name>","version":"<version>","timestamp":"<ISO-8601 UTC timestamp>","status":"success"}
```

- If the push fails, appends a line with `"status":"failed"` instead.
- The script must exit with code 0 on success and non-zero on failure.

### 3. Retention Policy Script

Create an executable Bash script at `/app/retention.sh` that:

- Accepts one argument: `<image_name>`.
- Queries the local backup registry (`localhost:5000`) for all tags of the given image.
- Keeps only the last 5 versions (sorted by version string in the order they appear in the registry tag list; the last 5 entries are kept).
- Deletes older tags from the registry beyond the most recent 5.
- Writes a summary to `/app/retention_report.json` (overwritten each run) in the following JSON format:

```json
{
  "image": "<image_name>",
  "kept_versions": ["v3", "v4", "v5", "v6", "v7"],
  "deleted_versions": ["v1", "v2"],
  "total_kept": 5,
  "total_deleted": 2
}
```

- If the image has 5 or fewer tags, no deletions occur; `deleted_versions` is an empty array and `total_deleted` is 0.

### 4. Scheduled Execution

- Set up a cron job for the current user that runs `/app/backup.sh` every hour (at minute 0).
- The cron entry must be verifiable via `crontab -l`.

### 5. Backup and Restore Test

- Build or pull a small test image (e.g., `alpine:latest`) and tag it as `testapp:latest`.
- Use `/app/backup.sh` to back up `testapp` with version `1.0.0`.
- Verify the image exists in the local registry by querying `http://localhost:5000/v2/testapp/tags/list`.

### 6. Documentation

Create a plain text file at `/app/backup_procedures.txt` that contains at minimum the following sections (each section header must appear on its own line exactly as shown):

```
BACKUP PROCEDURE
RESTORE PROCEDURE
RETENTION POLICY
SCHEDULED BACKUP
```

Each section must contain at least one line of descriptive text below its header.
