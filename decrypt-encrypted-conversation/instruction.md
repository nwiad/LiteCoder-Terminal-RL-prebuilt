## Encrypted Messaging System Forensics

Recover and decrypt a hidden conversation between two users (Alice and Bob) from an intercepted encrypted container file.

**Technical Requirements:**
- Language: Python 3.x
- Required libraries: `cryptography` or `pycryptodome`
- Input files:
  - `/app/conversation.enc` - encrypted message container
  - `/app/alice_private.pem` - Alice's RSA private key (PEM format)
  - `/app/bob_private.pem` - Bob's RSA private key (PEM format)
- Output files:
  - `/app/decrypted_conversation.txt` - full conversation in chronological order
  - `/app/msg_hashes.txt` - SHA-256 hash of each decrypted message (one per line)
  - `/app/forensic_report.txt` - forensic summary report

**Container Format Specification:**

The `conversation.enc` file contains multiple entries with this binary structure:
```
[4-byte entry length][sender:recipient][4-byte key length][encrypted AES key][16-byte IV][ciphertext]
```

- All integers are big-endian unsigned
- `sender:recipient` format: UTF-8 string (e.g., "Alice:Bob")
- Encrypted AES key: RSA-encrypted 256-bit AES key using recipient's public key
- IV: 16 bytes for AES-256-CBC
- Ciphertext: AES-256-CBC encrypted message

**Implementation Requirements:**

1. Parse the binary container and extract all entries
2. For each entry, decrypt the AES key using the appropriate recipient's RSA private key (PKCS1 OAEP padding)
3. Decrypt the message ciphertext using AES-256-CBC with the recovered key and IV
4. Write all decrypted messages to `/app/decrypted_conversation.txt` (one message per line, in order of appearance)
5. Compute SHA-256 hash of each decrypted plaintext and write to `/app/msg_hashes.txt` (one hash per line, lowercase hexadecimal)
6. Generate `/app/forensic_report.txt` with format:
```
Message 1:
Sender: [sender]
Recipient: [recipient]
Hash: [sha256_hash]

Message 2:
...
```

**Edge Cases:**
- Handle variable-length sender/recipient strings
- Support messages encrypted for either Alice or Bob
- Properly handle binary data and UTF-8 text encoding
