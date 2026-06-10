## Secure Message Decryption via RSA Key Recovery

Recover a 2048-bit RSA private key from a vulnerable public key and decrypt an encrypted message. The RSA modulus was generated using a flawed random number generator that produces close primes, making it susceptible to Fermat's factorization attack.

### Technical Requirements

- **Language**: Python 3.x
- **Input file**: `/app/public_key.json` - Contains RSA public key parameters and encrypted message
- **Output file**: `/app/decrypted_message.txt` - Contains the decrypted plaintext message

### Input Specification

The input file `/app/public_key.json` contains:
```json
{
  "n": "string (decimal integer)",
  "e": "integer",
  "ciphertext": "string (decimal integer)"
}
```

- `n`: RSA modulus (2048-bit, product of two close primes)
- `e`: Public exponent
- `ciphertext`: Encrypted message as integer

### Output Specification

Write the decrypted plaintext message to `/app/decrypted_message.txt` as UTF-8 text without additional formatting or metadata.

### Implementation Requirements

1. Parse the RSA public key parameters from `/app/public_key.json`
2. Factor the modulus `n` to recover prime factors `p` and `q`
3. Compute the private exponent `d` using the recovered primes
4. Decrypt the ciphertext using the private key
5. Convert the decrypted integer to the original message string
6. Write the plaintext to `/app/decrypted_message.txt`

### Constraints

- The modulus `n` is vulnerable to Fermat's factorization due to close primes
- Standard RSA decryption: `m = c^d mod n`
- Handle large integer arithmetic correctly for 2048-bit keys
