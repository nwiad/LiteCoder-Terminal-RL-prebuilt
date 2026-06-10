## Unveil Encrypted Secrets with John the Ripper and Hashcat

Recover the plaintext passwords for a set of salted MD5 (md5crypt) hashes using both John the Ripper and Hashcat in an Ubuntu environment, and produce a structured results report.

### Technical Requirements

- **Language/Tools:** Bash scripting; John the Ripper and Hashcat must be installed and used.
- **Input file:** `/app/hashes.txt` — you must create this file containing exactly 10 unique md5crypt hashes (format: `$1$<salt>$<hash>`). Each hash on its own line.
- **Wordlist file:** `/app/wordlist.txt` — you must create or obtain a focused wordlist (max 50 KB) used by both tools for the cracking attempts.
- **Output file:** `/app/output.json`

### Input Specification

The hashes in `/app/hashes.txt` must:
- Use the md5crypt format: `$1$<salt>$<hash>` (one per line, no blank lines)
- Contain exactly 10 entries
- Each hash must correspond to a crackable plaintext password that exists in your wordlist

### Output Specification

Write `/app/output.json` as a JSON file with the following structure:

```json
{
  "cracked_passwords": [
    {
      "hash": "$1$salt$hashvalue",
      "plaintext": "recovered_password",
      "cracked_by": "john"
    },
    {
      "hash": "$1$salt2$hashvalue2",
      "plaintext": "recovered_password2",
      "cracked_by": "hashcat"
    }
  ],
  "summary": {
    "total_hashes": 10,
    "john_cracked": <number>,
    "hashcat_cracked": <number>,
    "total_unique_cracked": <number>
  }
}
```

Field details:
- `cracked_passwords`: array of objects, one entry per cracked hash (may include duplicates if both tools cracked the same hash — include one entry per tool that cracked it).
- `hash`: the full hash string exactly as it appears in `/app/hashes.txt`.
- `plaintext`: the recovered plaintext password.
- `cracked_by`: either `"john"` or `"hashcat"`.
- `summary.total_hashes`: must be `10`.
- `summary.john_cracked`: number of hashes cracked by John the Ripper.
- `summary.hashcat_cracked`: number of hashes cracked by Hashcat.
- `summary.total_unique_cracked`: number of distinct hashes cracked by at least one tool (must be between 1 and 10 inclusive).

### Constraints

- All 10 hashes must be crackable with the provided wordlist (i.e., `total_unique_cracked` must equal 10).
- Both John the Ripper and Hashcat must each crack at least 1 hash (both `john_cracked` and `hashcat_cracked` must be ≥ 1).
- The wordlist `/app/wordlist.txt` must not exceed 50 KB in size.
- Every `plaintext` value in `cracked_passwords` must, when hashed with the corresponding salt, produce the matching hash in `/app/hashes.txt`.
