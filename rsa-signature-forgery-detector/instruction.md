## RSA Signature Forgery Detection

Implement a Python tool that detects forged RSA digital signatures by analyzing padding structure and mathematical properties.

**Technical Requirements:**
- Python 3.x
- Input: `/app/signatures.json` - JSON file containing signature data to analyze
- Output: `/app/results.json` - JSON file with detection results

**Input Format (`/app/signatures.json`):**
```json
{
  "signatures": [
    {
      "id": "sig_001",
      "message": "base64_encoded_message",
      "signature": "base64_encoded_signature",
      "public_key": {
        "n": "modulus_as_integer",
        "e": "exponent_as_integer"
      }
    }
  ]
}
```

**Output Format (`/app/results.json`):**
```json
{
  "results": [
    {
      "id": "sig_001",
      "is_forged": true,
      "confidence": 0.95,
      "vulnerabilities_detected": ["invalid_padding", "mathematical_inconsistency"],
      "details": "Description of detected issues"
    }
  ]
}
```

**Detection Requirements:**
- Validate PKCS#1 v1.5 padding structure (0x00 0x01 padding 0x00 hash)
- Check mathematical consistency: verify that signature^e mod n produces valid padded hash
- Detect Bleichenbacher's attack patterns (missing or malformed padding bytes)
- Identify signatures with incorrect hash algorithm identifiers
- Calculate confidence score (0.0 to 1.0) based on number and severity of issues found

**Edge Cases:**
- Handle signatures with various key sizes (1024, 2048, 4096 bits)
- Detect partially valid signatures (correct math but wrong padding)
- Handle malformed base64 encoding gracefully
- Return appropriate error details for unparseable signatures
