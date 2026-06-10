## Hash Function Length Extension Attack

Implement a hash function length extension attack to forge a valid MAC for an extended message without knowing the secret key.

**Technical Requirements**
- Language: Python 3.x
- Input file: /app/input.json
- Output file: /app/output.json
- Required libraries: hashlib, struct (standard library)

**Scenario**

A web service uses a vulnerable MAC scheme: `MAC = SHA256(secret || message)`. You have a valid MAC for a known message and need to forge a valid MAC for an extended message without knowing the secret.

**Input Format** (/app/input.json)

```json
{
  "original_message": "user=alice&role=user",
  "original_mac": "a1b2c3d4...",
  "secret_length": 16,
  "extension": "&role=admin"
}
```

- `original_message`: Known message with valid MAC
- `original_mac`: Valid MAC (64-character hex string)
- `secret_length`: Length of unknown secret in bytes
- `extension`: Data to append to forged message

**Output Format** (/app/output.json)

```json
{
  "forged_message": "user=alice&role=user<padding>&role=admin",
  "forged_mac": "e5f6g7h8..."
}
```

- `forged_message`: Extended message including SHA-256 padding
- `forged_mac`: Valid MAC for the forged message (64-character hex string)

**Requirements**

1. Read input from /app/input.json
2. Compute SHA-256 padding for `secret || original_message`
3. Use the original MAC as internal state to continue hashing
4. Append the extension and compute the forged MAC
5. Write results to /app/output.json

**Data Format Specifications**

- All MAC values must be lowercase hexadecimal strings (64 characters)
- Padding bytes in forged_message should be represented as hex escape sequences (\x80, \x00, etc.) or kept as raw bytes depending on your implementation
- JSON output must be valid and properly formatted
