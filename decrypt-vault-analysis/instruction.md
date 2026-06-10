## Task: Secure Encryption Chain Analysis

Analyze a custom encryption scheme and decrypt a protected vault file by identifying implementation weaknesses.

**Technical Requirements:**
- Language: Python 3.x
- Input files:
  - `/app/encrypt_vault.py` - encryption implementation to analyze
  - `/app/vault.enc` - encrypted vault file
- Output file: `/app/decrypted_vault.txt` - decrypted contents

**Objective:**

Reverse-engineer the encryption scheme in `encrypt_vault.py`, identify vulnerabilities in the key derivation or encryption implementation, and create a decryption solution that outputs the vault contents to `/app/decrypted_vault.txt`.

**Input Specifications:**

1. `encrypt_vault.py`: Python script containing the encryption implementation with key derivation, encryption layers, and obfuscation techniques
2. `vault.enc`: Binary or text file containing the encrypted vault data

**Output Specifications:**

- File: `/app/decrypted_vault.txt`
- Format: Plain text containing the decrypted vault contents
- The output must be the exact decrypted content without additional formatting or metadata

**Requirements:**

1. Analyze the encryption scheme to understand all encryption layers and transformations
2. Identify the key derivation mechanism and extract necessary parameters
3. Implement decryption logic that reverses the encryption process
4. Write the final decrypted content to `/app/decrypted_vault.txt`

**Success Criteria:**

The decrypted output file must contain valid, readable content that represents the original vault data before encryption.
