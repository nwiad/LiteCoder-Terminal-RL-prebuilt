## Task: AES-CBC IV Recovery and PDF Decryption

You have recovered two files from a compromised server: an encrypted PDF and a cryptographic leak file. Your goal is to decrypt the PDF and extract a hidden flag.

## Technical Requirements

- Language: Python 3.x
- Input files:
  - `/app/encrypted.pdf` - AES-128-CBC encrypted PDF file
  - `/app/leak.txt` - Partial cryptographic data (12 bytes of IV at start, 96 bytes of ciphertext at end)
- Output file: `/app/flag.txt` - Contains the extracted flag in plain text

## Task Description

The encrypted PDF uses AES-128-CBC encryption. The leak file contains:
- First 12 bytes: Beginning of the initialization vector (IV)
- Last 96 bytes: End of the ciphertext
- Middle section: Missing (4 IV bytes gap)

You must:
1. Reconstruct the complete 16-byte IV by determining the missing 4 bytes
2. Decrypt the PDF using the reconstructed IV and the ciphertext from the leak
3. Validate that the decrypted output is a valid PDF (starts with `%PDF-`)
4. Extract the flag from the decrypted PDF

## Input Specifications

`/app/leak.txt` format:
- Binary file containing exactly 108 bytes total
- Bytes 0-11: First 12 bytes of the IV
- Bytes 12-107: Last 96 bytes of the ciphertext

`/app/encrypted.pdf`:
- AES-128-CBC encrypted binary file
- No key provided (must be derived or brute-forced)

## Output Specifications

`/app/flag.txt`:
- Plain text file containing only the flag string
- Flag format: `FLAG{...}` where `...` is alphanumeric characters
- No additional whitespace or newlines

## Constraints

- The missing 4 IV bytes must be brute-forced (2^32 possibilities)
- Valid PDF files must start with the byte sequence `%PDF-1.` (e.g., `%PDF-1.4`, `%PDF-1.7`)
- Use CBC mode properties: modifying the IV affects only the first plaintext block
- The decryption key must be derived from the available information or through cryptanalytic techniques
