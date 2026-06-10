## Break the Crypto Vault - Vigenère Edition

You have intercepted an encrypted message protected by a Vigenère cipher. Your mission is to crack the cipher, recover the encryption key, decrypt the message, and extract the hidden flag.

### Input Files

- `/app/input/encrypted.txt` — The Vigenère-encrypted ciphertext.
- `/app/input/hint.txt` — A hint file with clues about the encryption.

### Task Requirements

Using Python 3, write a solution that:

1. Reads the encrypted ciphertext from `/app/input/encrypted.txt`.
2. Analyzes the ciphertext to determine the Vigenère key (using techniques such as Kasiski examination, index of coincidence, frequency analysis, or chi-square testing).
3. Decrypts the ciphertext using the recovered key.
4. Extracts the flag in the format `FLAG{...}` from the decrypted plaintext.
5. Produces the output files specified below.

### Encryption Details

- Standard Vigenère cipher (A-Z / a-z shift).
- Only alphabetic characters are encrypted; non-alphabetic characters (spaces, punctuation, digits, braces, underscores) are left unchanged.
- The key is applied cyclically to alphabetic characters only (the key index advances only when an alphabetic character is encountered).
- Letter case is preserved: uppercase plaintext letters produce uppercase ciphertext letters, and vice versa.

### Output Files

1. `/app/output/decrypted.txt` — The full decrypted plaintext. Must be a single text file containing the entire decrypted message.

2. `/app/output/solution.json` — A JSON file with the following structure:
```json
{
  "key": "<the recovered Vigenère key in lowercase>",
  "flag": "<the extracted flag, e.g. FLAG{...}>"
}
```

- `key`: The Vigenère key as a lowercase alphabetic string.
- `flag`: The complete flag string including the `FLAG{` prefix and `}` suffix, extracted exactly as it appears in the decrypted text.

### Constraints

- Use Python 3 only.
- Do not use any external packages that require installation (standard library only).
- The output directory `/app/output/` must be created if it does not exist.
