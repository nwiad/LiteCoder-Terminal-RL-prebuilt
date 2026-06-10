## RSA Encryption and Decryption Challenge

Implement a complete RSA encryption and decryption pipeline in Python 3, including manual key generation, message encryption/decryption, and OpenSSL-based verification.

### Technical Requirements

- Language: Python 3
- External tools: OpenSSL (command-line)
- Main script: `/app/rsa_challenge.py`
- Running `python3 /app/rsa_challenge.py` must produce all output files described below.

### Input

The plaintext message to encrypt is: `Secure Communication`

### Output Files

1. `/app/rsa_keys.json` — RSA key components in the following JSON structure:
   ```json
   {
     "p": "<hex string of prime p>",
     "q": "<hex string of prime q>",
     "n": "<hex string of modulus n>",
     "phi_n": "<hex string of Euler's totient>",
     "e": <integer public exponent>,
     "d": "<hex string of private exponent>"
   }
   ```
   - `p` and `q` must each be 1024-bit primes (hex length 256 characters).
   - `n` must equal `p * q` and be 2048 bits.
   - `e` must satisfy `1 < e < phi(n)` and `gcd(e, phi(n)) == 1`. The common choice `65537` is acceptable.
   - `d` must satisfy `(d * e) mod phi(n) == 1`.

2. `/app/rsa_result.json` — Encryption and decryption results:
   ```json
   {
     "plaintext": "Secure Communication",
     "ciphertext": "<hex string of encrypted message>",
     "decrypted_text": "Secure Communication",
     "verification": "PASS"
   }
   ```
   - `plaintext` must be the original message string.
   - `ciphertext` is the hex-encoded result of RSA encryption using the public key `(n, e)`.
   - `decrypted_text` is the result of RSA decryption using the private key `(n, d)`.
   - `verification` must be `"PASS"` if `decrypted_text` equals `plaintext`, otherwise `"FAIL"`.

3. `/app/private_key.pem` — A 2048-bit RSA private key in PEM format, generated using OpenSSL.

4. `/app/public_key.pem` — The corresponding RSA public key in PEM format, extracted from the private key using OpenSSL.

5. `/app/openssl_encrypted.bin` — The message `Secure Communication` encrypted using the OpenSSL public key (`public_key.pem`) with PKCS#1 v1.5 padding (i.e., `openssl rsautl -encrypt` or `openssl pkeyutl -encrypt`).

6. `/app/openssl_decrypted.txt` — The decrypted content of `openssl_encrypted.bin` using the OpenSSL private key. This file must contain exactly `Secure Communication`.

7. `/app/summary_report.txt` — A plain-text report containing:
   - The RSA key bit sizes used (p, q, n).
   - Whether manual encryption/decryption succeeded (`PASS` or `FAIL`).
   - Whether OpenSSL encryption/decryption succeeded (`PASS` or `FAIL`).

### Requirements

- The manual RSA implementation must not use any high-level RSA library functions for key generation, encryption, or decryption (e.g., do not use `cryptography.hazmat` or `Crypto.PublicKey.RSA` for the manual part). Standard library modules such as `random`, `math`, and `os` are allowed. Using `sympy` or similar for prime generation/testing is acceptable.
- The OpenSSL portion must invoke `openssl` via subprocess or `os.system`.
- All hex strings in JSON files must be lowercase without `0x` prefix.
- The script must be self-contained and produce all output files in a single run.
