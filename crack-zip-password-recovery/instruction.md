## Password-Protected ZIP Message Recovery

Write a Python program that creates a weakly-protected ZIP file and then recovers the password and extracts the hidden message using cryptographic analysis techniques.

### Technical Requirements

- Language: Python 3.x
- No external libraries beyond the Python standard library and `pyzipper` (for AES-encrypted ZIP support if needed). You may also use `zipfile` from stdlib.
- Entry point: `/app/solution.py`
- Input config: `/app/input.json`
- Output file: `/app/output.json`

### Task Details

Your program must perform two phases:

**Phase 1 — Setup (ZIP Creation):**

Read `/app/input.json` which contains:

```json
{
  "message": "The eagle has landed at dawn",
  "password_hint": "4-digit numeric PIN",
  "password": "1984"
}
```

Using this config, create a password-protected ZIP file at `/app/secret.zip` containing a single text file named `message.txt` with the value of `"message"`. The ZIP must be encrypted using the standard ZIP encryption (ZipCrypto) with the password from the config.

**Phase 2 — Recovery (Password Crack & Extraction):**

Without directly using the `"password"` field from the input config during this phase, your program must:

1. Read the `"password_hint"` field from `/app/input.json` to determine the password space (the hint always follows the format: `"N-digit numeric PIN"` where N is an integer between 1 and 6).
2. Parse the hint to determine N, then brute-force all numeric strings of exactly N digits (from `"0" * N` to `"9" * N`) to find the correct password.
3. Extract `message.txt` from the ZIP using the recovered password.
4. Write the results to `/app/output.json`.

### Output Format

`/app/output.json` must be a JSON object with exactly these fields:

```json
{
  "recovered_password": "1984",
  "message": "The eagle has landed at dawn",
  "attempts": 1985,
  "hint_parsed_digits": 4
}
```

- `recovered_password` (string): the password that successfully decrypted the ZIP.
- `message` (string): the exact content of `message.txt` extracted from the ZIP, with no leading/trailing whitespace.
- `attempts` (integer): the total number of passwords tried before finding the correct one (including the successful attempt). Passwords must be tried in ascending numeric order starting from `"0" * N` (e.g., for 4 digits: "0000", "0001", "0002", ...).
- `hint_parsed_digits` (integer): the value of N parsed from the hint string.

### Constraints

- The brute-force must iterate in ascending order: `"0000"`, `"0001"`, ..., `"9999"` for a 4-digit PIN.
- The password is always a zero-padded numeric string of exactly N digits (e.g., `"0042"` for N=4).
- The program must handle hints for digit lengths 1 through 6.
- If the ZIP file cannot be created or the password cannot be recovered, write an `output.json` with `"error": "<description>"` instead.
