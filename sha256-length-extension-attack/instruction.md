## Break the HMAC-SHA256 Without the Key

Perform a length-extension attack on a vulnerable HMAC-SHA256 implementation to forge a valid signature for a modified message without knowing the secret key.

**Technical Requirements:**
- Language: Python 3.x
- Input file: /app/input.json
- Output file: /app/output.json

**Scenario:**

A web service uses a vulnerable authentication scheme: `HMAC = SHA256(secret || message)` where `secret` is a 16-byte key. You have intercepted a valid message-signature pair and need to forge a signature for a modified message using a length-extension attack.

**Input Format (/app/input.json):**
```json
{
  "original_message": "user=bob&role=user",
  "original_signature": "b3d70addbfbf48bca1b07c8d5f4db41b1e3e76d66b0c272e9e8b8f3f4a9f4e4e",
  "secret_length": 16,
  "append_data": "&role=admin"
}
```

- `original_message`: The intercepted message (string)
- `original_signature`: The valid HMAC signature in hexadecimal (string)
- `secret_length`: Length of the secret key in bytes (integer)
- `append_data`: The payload to append (string)

**Output Format (/app/output.json):**
```json
{
  "forged_message": "user=bob&role=user[padding_bytes]&role=admin",
  "forged_signature": "a1b2c3d4e5f6..."
}
```

- `forged_message`: The complete forged message including SHA-256 padding (string, may contain non-printable bytes represented as escape sequences or hex)
- `forged_signature`: The forged HMAC signature in hexadecimal lowercase (string)

**Requirements:**

1. Read the input from /app/input.json
2. Compute SHA-256 padding for the original message (accounting for the secret prefix)
3. Perform a length-extension attack to generate a valid signature for the extended message
4. Write the forged message and signature to /app/output.json

**Note:** The vulnerability exists because the service uses `SHA256(secret || message)` instead of proper HMAC construction. This allows extending the hash state without knowing the secret.
