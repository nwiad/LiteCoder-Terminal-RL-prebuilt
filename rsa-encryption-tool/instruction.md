## RSA Encryption & Decryption Tool

Build a command-line RSA encryption/decryption utility in C that generates key pairs, encrypts files, and decrypts files using OpenSSL.

## Technical Requirements

- Language: C (C99 or later)
- Library: OpenSSL (libssl-dev)
- Key size: 2048-bit RSA
- Key format: PEM
- Working directory: /app

## Command-Line Interface

Your program must be named `rsa_tool` and support three modes:

1. **Key Generation:**
   ```
   ./rsa_tool -g
   ```
   Generates a 2048-bit RSA key pair and writes:
   - Public key to `/app/public.pem`
   - Private key to `/app/private.pem`

2. **Encryption:**
   ```
   ./rsa_tool -e <public_key_path> <input_file>
   ```
   Encrypts the input file using the public key and writes encrypted output to `<input_file>.enc`

   Example: `./rsa_tool -e /app/public.pem /app/input.txt` creates `/app/input.txt.enc`

3. **Decryption:**
   ```
   ./rsa_tool -d <private_key_path> <encrypted_file>
   ```
   Decrypts the encrypted file using the private key and writes decrypted output to `<encrypted_file>.dec`

   Example: `./rsa_tool -d /app/private.pem /app/input.txt.enc` creates `/app/input.txt.enc.dec`

## Input/Output Specifications

**Key Generation Output:**
- `/app/public.pem`: PEM-formatted RSA public key
- `/app/private.pem`: PEM-formatted RSA private key

**Encryption:**
- Input: Any file (text or binary)
- Output: Encrypted file with `.enc` extension appended to original filename
- The encrypted file should contain binary data

**Decryption:**
- Input: Encrypted file (`.enc` extension)
- Output: Decrypted file with `.dec` extension appended to encrypted filename
- The decrypted content must exactly match the original plaintext

## Implementation Requirements

- Use OpenSSL EVP API for cryptographic operations
- Keys must be stored in PEM format
- The tool must work offline without external dependencies beyond OpenSSL
- Support files of arbitrary size within RSA encryption limits
- Exit with status code 0 on success, non-zero on failure

## Compilation

Your program must compile with:
```
gcc -o rsa_tool rsa_tool.c -lssl -lcrypto
```

## Edge Cases

- Handle missing command-line arguments gracefully
- Return appropriate error codes for invalid operations
- Handle cases where key files don't exist or are malformed
- Handle files that exceed RSA encryption size limits appropriately
