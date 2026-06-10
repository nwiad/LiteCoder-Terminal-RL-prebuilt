## Secure PKI Configuration Generator with OpenSSL

Create a bash script (`/app/generate_pki.sh`) that automates a complete PKI (Public Key Infrastructure) setup using OpenSSL. The script must generate a Root CA, an Intermediate CA, server and client certificates, and a Certificate Revocation List (CRL). Running `bash /app/generate_pki.sh` must produce all artifacts described below.

### Technical Requirements

- Language: Bash
- Tool: OpenSSL (command-line)
- Entry point: `/app/generate_pki.sh`
- The script must exit with code `0` on success.
- All generated files must be in PEM format.

### Directory Structure

The script must create and populate the following directory layout under `/app/pki/`:

```
/app/pki/
├── root-ca/
│   ├── root-ca.key          # Root CA private key
│   ├── root-ca.crt          # Root CA self-signed certificate
│   └── root-ca.cnf          # Root CA OpenSSL config (optional, may be inline)
├── intermediate-ca/
│   ├── intermediate-ca.key  # Intermediate CA private key
│   ├── intermediate-ca.csr  # Intermediate CA CSR
│   ├── intermediate-ca.crt  # Intermediate CA certificate (signed by Root CA)
│   └── intermediate-ca.cnf  # Intermediate CA OpenSSL config (optional)
├── server/
│   ├── server.key            # Server private key
│   ├── server.csr            # Server CSR
│   └── server.crt            # Server certificate (signed by Intermediate CA)
├── client/
│   ├── client.key            # Client private key
│   ├── client.csr            # Client CSR
│   └── client.crt            # Client certificate (signed by Intermediate CA)
├── crl/
│   └── intermediate.crl      # Certificate Revocation List issued by Intermediate CA
└── ca-chain.crt              # Concatenated certificate chain (Intermediate CA cert + Root CA cert)
```

### Certificate Specifications

**Root CA Certificate (`root-ca.crt`):**
- RSA key size: 4096 bits
- Validity: 3650 days (10 years)
- Subject: must contain `CN=Root CA` (the CN field must be exactly `Root CA`)
- Extensions: `basicConstraints` must be set to `CA:TRUE`
- Must be self-signed (issuer equals subject)

**Intermediate CA Certificate (`intermediate-ca.crt`):**
- RSA key size: 4096 bits
- Validity: 1825 days (5 years)
- Subject: must contain `CN=Intermediate CA`
- Extensions: `basicConstraints` must be set to `CA:TRUE`
- Must be signed by the Root CA

**Server Certificate (`server.crt`):**
- RSA key size: 2048 bits (minimum)
- Validity: 365 days (1 year)
- Subject: must contain `CN=server.example.com`
- Extensions: must include `TLS Web Server Authentication` in extendedKeyUsage
- Must be signed by the Intermediate CA

**Client Certificate (`client.crt`):**
- RSA key size: 2048 bits (minimum)
- Validity: 365 days (1 year)
- Subject: must contain `CN=client.example.com`
- Extensions: must include `TLS Web Client Authentication` in extendedKeyUsage
- Must be signed by the Intermediate CA

### Certificate Chain

The file `/app/pki/ca-chain.crt` must contain the Intermediate CA certificate followed by the Root CA certificate (concatenated PEM). The following verifications must succeed:

- `openssl verify -CAfile /app/pki/ca-chain.crt /app/pki/server/server.crt` → returns OK
- `openssl verify -CAfile /app/pki/ca-chain.crt /app/pki/client/client.crt` → returns OK

### Certificate Revocation List (CRL)

- The Intermediate CA must issue a CRL at `/app/pki/crl/intermediate.crl`.
- The CRL must be parseable by `openssl crl -in /app/pki/crl/intermediate.crl -noout -text`.
- The CRL issuer must match the Intermediate CA subject.

### Private Key Permissions

All `.key` files must have file permissions no more permissive than `0600` (owner read/write only).
