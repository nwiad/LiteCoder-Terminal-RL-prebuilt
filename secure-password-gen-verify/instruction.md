## Secure Password Generator and Verifier

Create a Python command-line tool (`/app/password_tool.py`) that generates cryptographically strong passwords using `/dev/urandom`, hashes them with bcrypt, and verifies password attempts against stored hashes.

### Technical Requirements

- Language: Python 3
- Dependencies: `bcrypt` (install via pip)
- Entropy source: `/dev/urandom` (use `os.urandom` or `secrets` module)
- Hashing: bcrypt with a default cost factor of 12
- Storage file: `/app/passwords.json`

### CLI Interface

The tool must use `argparse` with the following subcommands:

**1. `generate`** — Generate a password and store its bcrypt hash.

```
python3 /app/password_tool.py generate --length <int> --name <string> [--no-special] [--no-digits] [--no-uppercase]
```

- `--length`: Password length (required, integer, minimum 8, maximum 128)
- `--name`: A unique label/identifier for the stored password (required)
- `--no-special`: If set, exclude special characters from the password
- `--no-digits`: If set, exclude digits from the password
- `--no-uppercase`: If set, exclude uppercase letters from the password
- Passwords must always contain at least lowercase letters.
- If `--length` is less than 8 or greater than 128, print to stdout: `Error: Length must be between 8 and 128` and exit with code 1.
- If `--name` already exists in the storage file, print to stdout: `Error: Name '<name>' already exists` and exit with code 1.

On success, print exactly to stdout:
```
Password generated for '<name>': <plaintext_password>
```

The character sets used for generation:
- Lowercase: `abcdefghijklmnopqrstuvwxyz`
- Uppercase: `ABCDEFGHIJKLMNOPQRSTUVWXYZ`
- Digits: `0123456789`
- Special: `!@#$%^&*()-_=+[]{}|;:,.<>?`

**2. `verify`** — Verify a password attempt against a stored hash.

```
python3 /app/password_tool.py verify --name <string> --password <string>
```

- `--name`: The label of the stored password (required)
- `--password`: The password attempt to verify (required)
- If `--name` is not found in the storage file, print to stdout: `Error: Name '<name>' not found` and exit with code 1.

On success, print exactly one of:
```
Verification result: MATCH
```
or
```
Verification result: NO MATCH
```

**3. `list`** — List all stored password names.

```
python3 /app/password_tool.py list
```

Print each stored name on its own line, sorted alphabetically. If no passwords are stored, print: `No passwords stored`

### Storage Format (`/app/passwords.json`)

The file must be a JSON object mapping names to their bcrypt hash strings:

```json
{
  "admin": "$2b$12$...",
  "db_service": "$2b$12$..."
}
```

- If the file does not exist when the tool runs, treat it as an empty store and create it when needed.
- The file must be updated atomically after each `generate` operation.

### Exit Codes

- `0` for successful operations
- `1` for any error (invalid arguments, duplicate name, name not found, etc.)
