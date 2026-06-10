## Recover Encrypted Backup File

A departing employee hid a critical 64-character hexadecimal string (a master product-key) inside a password-protected archive, then renamed it to look like an ordinary system file. Use forensic techniques to locate the archive, deduce the passphrase, and recover the hex key.

### Technical Requirements

- **Environment:** Ubuntu container with sudo access
- **Input files:**
  - `/app/.bash_history` — a shell history file containing commands the employee ran; includes clues about the archive name, location, and/or passphrase.
  - `/app/sysbackup/` — a directory containing several files with system-like names. One of these files is actually a password-protected archive disguised with a different name/extension.
- **Output file:** `/app/output.txt` — must contain exactly the recovered 64-character lowercase hexadecimal string, with no leading/trailing whitespace or newlines.

### Task Steps

1. Inspect `/app/.bash_history` for suspicious commands that reveal the archive's real name, location, or password hints.
2. Enumerate `/app/sysbackup/`, examine file attributes and magic bytes to identify the disguised archive.
3. Use clues from the history file (dates, usernames, project names, patterns, etc.) to build candidate passphrases.
4. Crack the archive password using the derived candidates.
5. Extract the archive contents to retrieve the file containing the 64-character hex string.
6. Write the exact 64-character hex string to `/app/output.txt`.

### Output Format

- `/app/output.txt` must contain a single line: exactly 64 lowercase hexadecimal characters (`[0-9a-f]{64}`).
- No extra whitespace, newlines, prefixes, or surrounding text.
