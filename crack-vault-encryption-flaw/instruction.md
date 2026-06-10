## The Forgotten Vault

A forgotten vault was discovered on an old server containing an encrypted secret. The vault uses a custom encryption scheme with a critical flaw. Analyze the encryption implementation, identify the flaw, and exploit it to decrypt the secret flag.

### Setup

Before starting, run the setup script to generate the vault files:

```bash
cd /app && python3 setup_vault.py
```

This creates:
- `/app/vault/encrypt.py` — the encryption implementation (source code)
- `/app/vault/secret.enc` — the encrypted secret (hex-encoded ciphertext)
- `/app/vault/known_header.txt` — a known plaintext header that was prepended to the secret before encryption

### Technical Requirements

- Language: Python 3
- No external packages required (standard library only)
- Write your decryption script to `/app/decrypt.py`
- Write the recovered flag to `/app/output.txt`

### Task

1. Read and analyze `/app/vault/encrypt.py` to understand the encryption scheme and identify its cryptographic flaw.
2. Use the known plaintext in `/app/vault/known_header.txt` along with the ciphertext in `/app/vault/secret.enc` to exploit the flaw.
3. Write a decryption script (`/app/decrypt.py`) that recovers the original plaintext.
4. Extract the flag from the decrypted plaintext and write it to `/app/output.txt`.

### Output Specification

- `/app/output.txt` must contain exactly the flag string, in the format `FLAG{...}`, with no leading/trailing whitespace or newlines.
