## Analyze and Crack the Encrypted Message

A colleague encrypted a secret message and hid the relevant files across the filesystem. Your job is to locate the hidden encrypted file and key file, determine the encryption method, decrypt the message, and write the result to an output file.

### Technical Requirements
- Environment: Linux (Bash + any scripting language available on the system)
- Working directory: /app
- Output file: /app/output.txt

### Task Details

1. Hidden files are scattered under the `/app` directory tree (they may be in subdirectories at any depth). The filenames start with a dot (`.`), following the Unix hidden file convention.

2. Among the hidden files, exactly one is the **key file** and exactly one is the **encrypted file**. Identify them by inspecting their contents:
   - The key file contains a line starting with `KEY:` followed by the key value.
   - The encrypted file contains a line starting with `ENC:` followed by the hex-encoded encrypted data.

3. The encryption method is **XOR cipher**: each byte of the original plaintext message was XORed with the corresponding byte of the key (the key is applied cyclically if the message is longer than the key).

4. Decrypt the message by:
   - Extracting the hex-encoded ciphertext from the encrypted file (the part after `ENC:`).
   - Extracting the key string from the key file (the part after `KEY:`).
   - XOR-decrypting the ciphertext using the key (cycling the key as needed).

5. Write **only** the decrypted plaintext message (with no trailing newline or extra whitespace) to `/app/output.txt`.

### Output Format
- `/app/output.txt` must contain the exact decrypted plaintext string and nothing else.
