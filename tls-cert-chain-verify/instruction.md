## Task: TLS Certificate Chain Verification

Perform comprehensive TLS certificate chain verification for a given domain and generate a structured security report.

**Technical Requirements:**
- Language: Python 3.x or Bash
- Input: `/app/input.json` containing the target domain
- Output: `/app/output.json` containing the verification report

**Input Format (`/app/input.json`):**
```json
{
  "domain": "example.com",
  "port": 443
}
```

**Output Format (`/app/output.json`):**
```json
{
  "domain": "example.com",
  "port": 443,
  "timestamp": "2024-01-15T10:30:00Z",
  "chain_valid": true,
  "certificates": [
    {
      "level": "server",
      "subject": "CN=example.com",
      "issuer": "CN=Intermediate CA",
      "serial_number": "1A2B3C4D5E6F",
      "not_before": "2023-01-01T00:00:00Z",
      "not_after": "2024-12-31T23:59:59Z",
      "is_expired": false,
      "signature_algorithm": "sha256WithRSAEncryption",
      "key_usage": ["digitalSignature", "keyEncipherment"],
      "extended_key_usage": ["serverAuth"],
      "subject_alternative_names": ["example.com", "www.example.com"],
      "sha256_fingerprint": "AB:CD:EF:..."
    }
  ],
  "hostname_valid": true,
  "issues": []
}
```

**Certificate Chain Structure:**
- Each certificate must include: level (server/intermediate/root), subject, issuer, serial_number, validity dates, expiration status, signature algorithm, fingerprint
- Include key_usage and extended_key_usage arrays if present
- Include subject_alternative_names array for server certificates

**Verification Requirements:**
- Validate the complete certificate chain from server to root
- Check certificate expiration status (compare not_after with current timestamp)
- Verify hostname matches against subject_alternative_names
- Set chain_valid to false if any signature verification fails
- Set hostname_valid to false if domain doesn't match any SAN entry

**Issues Array:**
- Report expired certificates: `{"type": "expired_certificate", "level": "server", "message": "Certificate expired on 2023-12-31"}`
- Report hostname mismatches: `{"type": "hostname_mismatch", "message": "Domain does not match certificate SANs"}`
- Report chain validation failures: `{"type": "chain_invalid", "message": "Certificate signature verification failed"}`
- Report missing extensions: `{"type": "missing_extension", "message": "Extended Key Usage extension not found"}`

**Edge Cases:**
- Handle connection failures gracefully (network errors, refused connections)
- Handle self-signed certificates
- Handle incomplete certificate chains
- Validate timestamp format as ISO 8601
