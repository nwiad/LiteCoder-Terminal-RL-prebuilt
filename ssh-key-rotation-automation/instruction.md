## SSH Key Rotation Automation

Automate SSH key rotation across multiple user accounts on a Linux server by creating a rotation script, backup mechanism, logging, and cron scheduling.

### Technical Requirements

- Language: Bash (the main rotation script must be a Bash script)
- OS: Ubuntu/Debian-based Linux
- Tools: OpenSSH (`ssh-keygen`, `ssh-copy-id` or manual key placement)

### Input

A JSON configuration file at `/app/input.json` defines the user accounts and rotation settings:

```json
{
  "users": ["alice", "bob", "charlie"],
  "key_type": "ed25519",
  "key_bits": 256,
  "backup_dir": "/app/backups",
  "log_file": "/app/rotation.log",
  "cron_schedule": "0 3 1 * *"
}
```

- `users`: list of local user account names whose SSH keys must be rotated.
- `key_type`: SSH key algorithm to use (e.g., `ed25519`, `rsa`).
- `key_bits`: key size (only relevant for `rsa`; ignored for `ed25519`).
- `backup_dir`: directory where old keys are backed up before rotation.
- `log_file`: path to the log file recording all rotation activity.
- `cron_schedule`: cron expression for scheduling automatic rotation.

### Setup Requirements

1. Create the user accounts listed in `input.json` if they do not already exist (each with a home directory and `.ssh` directory with permissions `700`).
2. Generate an initial SSH key pair for each user (stored in `~<user>/.ssh/id_<key_type>` and `~<user>/.ssh/id_<key_type>.pub`), and add the public key to `~<user>/.ssh/authorized_keys` with permissions `600`.

### Rotation Script

Create an executable Bash script at `/app/rotate_keys.sh` that, when run, performs the following for every user in `/app/input.json`:

1. **Backup**: Copy the user's current private and public key files into the backup directory specified in `input.json`, inside a per-user subdirectory. Backup filenames must include a timestamp in the format `YYYYMMDD_HHMMSS` (e.g., `/app/backups/alice/id_ed25519.20250301_030000`).
2. **Generate new key pair**: Generate a new SSH key pair of the configured type, replacing the old key files in the user's `~/.ssh/` directory. The new key must have no passphrase.
3. **Update authorized_keys**: Replace the old public key entry in `~<user>/.ssh/authorized_keys` with the new public key.
4. **Set permissions**: Ensure private key is `600`, public key is `644`, and `authorized_keys` is `600`. The `.ssh` directory must be `700`. All files must be owned by the respective user.
5. **Log each action**: Append entries to the log file specified in `input.json`. Each log line must follow this format:
   ```
   [YYYY-MM-DD HH:MM:SS] <USER> - <ACTION>
   ```
   Where `<ACTION>` is one of: `BACKUP_CREATED`, `NEW_KEY_GENERATED`, `AUTHORIZED_KEYS_UPDATED`, `ROTATION_COMPLETE`, or `ERROR: <message>`.

### Cron Setup

Create a file at `/app/cron_entry.txt` containing the cron line that would schedule `/app/rotate_keys.sh` according to the `cron_schedule` value from `input.json`. Format:

```
<cron_schedule> /app/rotate_keys.sh
```

### Status Report

After each full rotation run, the script must write a JSON status report to `/app/rotation_status.json` with the following structure:

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SS",
  "users_processed": ["alice", "bob", "charlie"],
  "success": ["alice", "bob", "charlie"],
  "failed": [],
  "total": 3,
  "success_count": 3,
  "failed_count": 0
}
```

- `users_processed`: all users the script attempted to rotate.
- `success`: users whose rotation completed without error.
- `failed`: users whose rotation encountered an error.
- `total`, `success_count`, `failed_count`: corresponding counts.

### Edge Cases

- If a user listed in `input.json` does not exist and cannot be created, log an `ERROR` entry and include that user in the `failed` list in the status report. Do not abort the remaining users.
- If the backup directory does not exist, create it (including per-user subdirectories).
- If a user has no existing key pair (first run after account creation), skip the backup step and log accordingly, then generate a new key pair.

### Expected Output Files

| File | Description |
|---|---|
| `/app/rotate_keys.sh` | Main rotation script (executable) |
| `/app/rotation.log` | Append-only log of all rotation actions |
| `/app/rotation_status.json` | JSON status report of the latest run |
| `/app/cron_entry.txt` | Cron schedule line |
| `/app/backups/<user>/` | Per-user backup directories with timestamped old keys |
