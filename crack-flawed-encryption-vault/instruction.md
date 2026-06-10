## Decrypting the Encrypted Vault

A junior developer created a "secure" vault using a custom encryption scheme with critical cryptographic flaws. You are given the encryption source code and the encrypted vault file. Analyze the code, identify the weaknesses, and exploit them to decrypt the vault and retrieve the hidden flag.

### Environment

After setup, the working directory `/app` contains:
- `encryption_program.py` — The source code of the flawed encryption program
- `vault.enc` — The encrypted vault file containing the flag
- `README.md` — Basic challenge description

### Technical Requirements

- Language: Python 3
- The `pycryptodome` package is available in the environment

### Task

1. Analyze `encryption_program.py` to identify the cryptographic weaknesses in the implementation
2. Exploit those weaknesses to decrypt `vault.enc`
3. Extract the flag from the decrypted content

### Output

Write the recovered flag to `/app/output.txt`. The file must contain exactly one line with the flag in the format `CTF{...}` (no leading/trailing whitespace, no extra lines).
