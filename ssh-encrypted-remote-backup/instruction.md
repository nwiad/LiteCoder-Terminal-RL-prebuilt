## Remote Backup Over SSH

Create an automated, secure, encrypted off-site backup system that compresses a local directory and prepares it for transfer to a remote server using standard Unix tools and SSH keys.

### Technical Requirements

- Shell: Bash
- Working directory: `/app`
- No additional packages may be installed beyond what is available in a standard Linux environment (tar, gzip, openssl, ssh-keygen, ssh-copy-id, scp/rsync, cron).

### Tasks

1. **SSH Key Pair**: Generate a 4096-bit RSA SSH key pair without a passphrase for the root user. The private key must be at `/root/.ssh/id_rsa` and the public key at `/root/.ssh/id_rsa.pub`. The private key file must have permissions `600`.

2. **Backup Script**: Create an executable shell script at `/root/remote_backup.sh` with the following behavior:

   - The script must start with `#!/bin/bash`.
   - It must compress the directory `/srv/apps` into a tar.gz archive.
   - It must encrypt the tar.gz archive using `openssl enc` with the `aes-256-cbc` cipher.
   - The encryption passphrase must be exactly 32 characters long, randomly generated at runtime (e.g., via `/dev/urandom`), and must NEVER be written to any file on disk. It must be passed to openssl exclusively through a pipeline or process substitution (e.g., `-pass stdin`, `-pass fd:N`, or `-pass file:/dev/stdin`), not via `-pass pass:...` with a shell variable written to a temp file.
   - The final encrypted output file must be named following the pattern: `backup-YYYYmmdd-HHMMSS.tar.gz.enc` (e.g., `backup-20250115-021500.tar.gz.enc`), using the timestamp at the time of script execution.
   - The script must upload the encrypted file to the remote server `backup.example.com` as user `bkp` via `scp` or `rsync` over SSH, placing it in the remote user's home directory (e.g., `bkp@backup.example.com:~/`).
   - The script must clean up any local temporary files (the intermediate tar.gz archive) after the upload completes, whether the upload succeeds or fails.
   - The script must be executable (`chmod +x`).

3. **Cron Job**: Schedule the backup script to run every night at 02:15. The cron entry must be present in root's crontab and must match the schedule `15 2 * * *` invoking `/root/remote_backup.sh`.

4. **Decryption Documentation**: Create a file at `/root/RESTORE.md` that documents the exact command(s) needed on the remote server to decrypt and unpack a backup file. The documentation must include:
   - A command using `openssl enc -d -aes-256-cbc` to decrypt.
   - A command using `tar` to extract the decrypted archive.
   - The documentation must mention that the original encryption passphrase is required for decryption.

### Directory Setup

Before running the script, the directory `/srv/apps` will exist and contain sample files.

### Output Artifacts

| Artifact | Path |
|---|---|
| SSH private key | `/root/.ssh/id_rsa` |
| SSH public key | `/root/.ssh/id_rsa.pub` |
| Backup script | `/root/remote_backup.sh` |
| Cron job | root's crontab (`crontab -l`) |
| Restore documentation | `/root/RESTORE.md` |
