## SSH Key Pair and Encrypted Backup System

Set up secure SSH access and implement a GPG-based encrypted backup system for sensitive configuration files.

### Technical Requirements

- Environment: Linux with `openssh` and `gpg` (GnuPG 2.x) available
- All artifacts must be created under `/app/`

### Step 1: Generate SSH Key Pair

- Generate an RSA SSH key pair with a key size of **4096 bits**.
- Use passphrase: `SecurePass2024!`
- Save the private key to `/app/ssh_keys/id_rsa`
- Save the public key to `/app/ssh_keys/id_rsa.pub`
- Set private key file permissions to `600`.
- Set public key file permissions to `644`.

### Step 2: Configure SSH Daemon

- Create an SSH daemon configuration file at `/app/ssh_config/sshd_config`.
- The configuration must include at minimum the following directives (exact directive names, values are case-sensitive):
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `PubkeyAuthentication yes`
  - `Protocol 2`
  - `MaxAuthTries 3`
  - `AllowUsers admin`
- Set file permissions to `600`.

### Step 3: Create Sensitive Test Data

- Create directory `/app/sensitive_data/`.
- Create the following files inside it:
  - `database.conf` — must contain at least the keys `db_host`, `db_port`, `db_user`, and `db_password` (one per line, in `key=value` format).
  - `api_keys.conf` — must contain at least the keys `api_key` and `api_secret` (one per line, in `key=value` format).
  - `server.conf` — must contain at least the keys `server_ip`, `server_port`, and `server_user` (one per line, in `key=value` format).

### Step 4: Generate GPG Key Pair

- Generate a GPG key pair using batch/unattended mode with the following parameters:
  - Key type: RSA
  - Key length: **4096**
  - Name: `BackupAdmin`
  - Email: `backup@example.com`
  - Passphrase: `GPGBackup2024!`
- After generation, export the public key to `/app/gpg_keys/backup_public.gpg`.
- Export the private/secret key to `/app/gpg_keys/backup_secret.gpg`.

### Step 5: Create Encrypted Backup

- Create a tar archive of the entire `/app/sensitive_data/` directory.
- Encrypt the tar archive using GPG with the `BackupAdmin` key (recipient: `backup@example.com`).
- Save the final encrypted backup file to `/app/backups/sensitive_backup.tar.gpg`.
- The encrypted file must be a valid GPG-encrypted file (verifiable via `gpg --list-packets` or `file` command).

### Step 6: Verify Decryption

- Decrypt `/app/backups/sensitive_backup.tar.gpg` using the GPG private key and passphrase `GPGBackup2024!`.
- Extract the decrypted tar archive to `/app/backups/restored/`.
- After extraction, the directory `/app/backups/restored/` must contain the original files (`database.conf`, `api_keys.conf`, `server.conf`) with content identical to the originals in `/app/sensitive_data/`.

### Step 7: Documentation

- Create a documentation file at `/app/docs/security_report.txt`.
- The file must contain all of the following sections (each as a line or heading containing the section name):
  - `SSH Key Generation` — describe key type and size used
  - `SSH Daemon Configuration` — list security directives applied
  - `GPG Encryption` — describe encryption method and key details
  - `Backup Process` — describe how the backup was created and verified
  - `Security Measures` — summarize overall security practices applied
- The file must be at least 20 lines long.
