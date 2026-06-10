## Hidden Symmetric Key Recovery

Locate a hidden encrypted symmetric key file in the system, extract a password from a steganographic image, decrypt the key file, and write the result.

### Technical Requirements

- **Language/Tools:** Any command-line tools (e.g., steghide, openssl, find, etc.)
- **Working directory:** /app

### Input Files

1. **Steganographic image:** `/app/secret_image.jpg`
   - A JPEG image containing steganographically embedded data.
   - The embedded data is the password needed to decrypt the encrypted key file.
   - The data was embedded using `steghide` with an empty passphrase (i.e., passphrase is `""`).

2. **Encrypted key file:** Located somewhere under the `/app/hidden/` directory tree.
   - The file has the extension `.enc`.
   - It was encrypted using `openssl enc -aes-256-cbc -pbkdf2` with the password extracted from the image.
   - There is exactly one `.enc` file in the directory tree.

### Task Steps

1. Extract the hidden password from `/app/secret_image.jpg` using steganography tools.
2. Search the `/app/hidden/` directory tree for the `.enc` file.
3. Decrypt the `.enc` file using the extracted password with AES-256-CBC (PBKDF2 key derivation).
4. Write the decrypted plaintext content to `/app/output.txt`.
5. Write the same decrypted plaintext content (the flag) to `/app/flag.txt`.

### Output Files

- **`/app/output.txt`**: Contains the exact decrypted plaintext from the `.enc` file, with no extra whitespace or newlines beyond what the original plaintext contains.
- **`/app/flag.txt`**: Contains the same content as `/app/output.txt`.

### Constraints

- The steganographic extraction passphrase is an empty string `""`.
- The decryption cipher is `aes-256-cbc` with `-pbkdf2`.
- Both output files must contain only the raw decrypted plaintext (no headers, no labels, no extra formatting).
