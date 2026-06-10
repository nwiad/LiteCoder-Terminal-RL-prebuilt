## Task: Reconstructing a Broken SSH Key Pair

A junior administrator corrupted an SSH private key file during server maintenance. You must reconstruct the functional private key from available fragments and use it to decrypt an encrypted message.

### Technical Requirements

- **Language/Tools**: OpenSSH utilities (ssh-keygen, openssl), bash/shell scripting
- **Input Files**:
  - `/app/key_fragments/` - Directory containing corrupted key fragments
  - `/app/encrypted_message.txt` - Message encrypted with the public key
- **Output File**:
  - `/app/decrypted_message.txt` - The decrypted message content

### Task Specifications

**Key Reconstruction:**
- Examine all files in `/app/key_fragments/` to identify key type (RSA, ED25519, ECDSA, etc.)
- Reconstruct a valid OpenSSH private key file at `/app/id_rsa` (or appropriate filename for key type)
- The reconstructed key must pass validation with `ssh-keygen -y` (able to derive public key)
- Set correct permissions (0600) on the private key file

**Message Decryption:**
- Decrypt `/app/encrypted_message.txt` using the reconstructed private key
- Write the plaintext result to `/app/decrypted_message.txt`
- The decrypted message must be readable ASCII text

**Validation Criteria:**
- The private key file must be in valid OpenSSH or PEM format
- `ssh-keygen -y -f /app/id_rsa` must successfully generate the corresponding public key
- The decrypted message must match the original plaintext (verification will be done by comparing with reference)
- All output files must exist at the specified paths

### Edge Cases

- Handle different SSH key formats (OpenSSH, PEM)
- Handle missing or incomplete key fragments
- Verify key integrity before attempting decryption
