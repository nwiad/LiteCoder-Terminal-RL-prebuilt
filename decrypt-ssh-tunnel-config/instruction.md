## Decrypt the Encrypted SSH Tunnel Configuration

Recover a plaintext SSH tunnel configuration by locating scattered passphrase fragments across the filesystem, reconstructing the full passphrase, and decrypting an AES-256-CBC encrypted file.

### Technical Requirements

- Language/Tools: Bash, OpenSSL (available in the environment)
- Working directory: /app

### Setup

The following files and locations contain the pieces you need:

1. **Encrypted file:** `/app/repo/ssh_tunnel.conf.enc` — an AES-256-CBC encrypted file produced by OpenSSL.
2. **Encryption metadata:** `/app/repo/encryption_info.txt` — contains the encryption method and any relevant parameters (salt, iteration count, digest algorithm).
3. **Passphrase fragment 1:** Found somewhere in `/home/admin/.bash_history`.
4. **Passphrase fragment 2:** Stored in an environment variable. Check `/app/repo/.env` for the variable definition.
5. **Passphrase fragment 3:** Hidden inside `/var/log/syslog.log`.

Each fragment is tagged with a label so it can be identified (e.g., `PASSPHRASE_PART1=...`). The three parts must be concatenated in order (part1 + part2 + part3) to form the complete passphrase.

### Task Steps

1. Read `/app/repo/encryption_info.txt` to learn the encryption parameters.
2. Locate and extract the three passphrase fragments from their respective locations.
3. Concatenate the fragments in order (part1 + part2 + part3) to form the full passphrase.
4. Use the passphrase and the parameters from `encryption_info.txt` to decrypt `/app/repo/ssh_tunnel.conf.enc` with OpenSSL.
5. Write the decrypted plaintext to `/app/output/ssh_tunnel.conf`.
6. Extract the key configuration values from the decrypted file and write a JSON summary to `/app/output/result.json`.

### Output Specifications

**File 1: `/app/output/ssh_tunnel.conf`**
The raw decrypted SSH tunnel configuration in plaintext. It will be an OpenSSH-style config containing fields such as `Host`, `HostName`, `Port`, `User`, `LocalForward`, `IdentityFile`, etc.

**File 2: `/app/output/result.json`**
A JSON object summarizing the recovered configuration with exactly these keys:

```json
{
  "passphrase": "<the full reconstructed passphrase>",
  "host_alias": "<value of Host>",
  "hostname": "<value of HostName>",
  "port": "<value of Port as a string>",
  "user": "<value of User>",
  "local_forward": "<full value of LocalForward, e.g. '8080 localhost:3306'>",
  "identity_file": "<value of IdentityFile>"
}
```

All values must be strings. If a field appears multiple times, use the first occurrence.

### Constraints

- You must create the `/app/output/` directory if it does not exist.
- The decryption must use OpenSSL's command-line tool.
- Do not modify any of the input/source files.
- The passphrase fragments must be extracted programmatically from their respective locations, not guessed.
