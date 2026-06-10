## CTF Challenge: Shadow File Hash Analysis and Password Recovery

You are given a simulated `/etc/shadow` file extracted during an authorized penetration test of a privileged Docker container environment. Your task is to analyze the shadow file, identify SHA-512 (`$6$`) password hashes, and recover the cleartext passwords using a password-cracking tool.

### Technical Requirements

- Language/Tools: Python 3.x and/or standard Linux CLI tools (e.g., `hashcat`, `john`)
- Input file: `/app/shadow_file.txt` — a simulated shadow file in standard `/etc/shadow` format
- Output file: `/app/output.json`

### Input Specification

The input file `/app/shadow_file.txt` contains lines in standard shadow format:

```
username:$hash_id$salt$hash:last_changed:min:max:warn:inactive:expire:reserved
```

The file will contain a mix of:
- Accounts with SHA-512 (`$6$`) hashed passwords
- Locked accounts (password field is `!` or `*` or `!!`)
- Accounts with no password (empty password field)

### Output Specification

Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "cracked_passwords": [
    {
      "username": "<username>",
      "hash_type": "SHA-512",
      "cleartext_password": "<recovered password>"
    }
  ],
  "locked_accounts": ["<username1>", "<username2>"],
  "no_password_accounts": ["<username1>"]
}
```

- `cracked_passwords`: An array of objects for each account whose SHA-512 hash was successfully cracked. Each object must contain `username`, `hash_type` (always `"SHA-512"` for `$6$` hashes), and `cleartext_password`.
- `locked_accounts`: A sorted array of usernames whose password field is `!`, `*`, or `!!`.
- `no_password_accounts`: A sorted array of usernames with an empty password field.
- All arrays should be sorted alphabetically by username.

### Requirements

1. Parse `/app/shadow_file.txt` and categorize every account into one of the three categories above.
2. For each account with a `$6$` hash, attempt to crack the password. The passwords used are common dictionary words or simple passwords (suitable for cracking with a standard wordlist such as `rockyou.txt` or a small custom wordlist).
3. Write the results to `/app/output.json` in the exact format specified above.
4. The output JSON must be valid, properly formatted, and written with UTF-8 encoding.
