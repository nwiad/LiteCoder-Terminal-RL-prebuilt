## Cracking a Weak Cipher Using Classic Cryptanalysis

You are auditing a legacy application and have uncovered an old log file containing an encrypted secret. The file is short, and you suspect the developer used a simple, home-made cipher — either a mono-alphabetic substitution or a simple transposition. Your job is to identify the cipher type, break it, and recover the original plaintext message.

### Technical Requirements

- Language: Python 3.x
- Input file: `/app/input.txt` — contains the ciphertext (a single line of ASCII text, approximately 60–80 characters)
- Output file: `/app/output.json`

### Task

1. Read the ciphertext from `/app/input.txt`.
2. Determine the type of cipher used (substitution or transposition).
3. Apply a classic cryptanalysis technique to recover the original English plaintext.
4. Write results to `/app/output.json`.

### Output Format

`/app/output.json` must be a valid JSON object with the following fields:

```json
{
  "cipher_type": "<string>",
  "plaintext": "<string>",
  "shift": <integer or null>
}
```

Field specifications:
- `cipher_type`: One of `"substitution"` or `"transposition"` (lowercase).
- `plaintext`: The fully decrypted original English message. Must preserve the original casing, spacing, and punctuation of the plaintext.
- `shift`: If the cipher is a substitution cipher (specifically a Caesar/ROT-style shift), provide the integer shift value used for encryption (1–25). Set to `null` if the cipher is not a shift-based substitution.

### Constraints

- The ciphertext contains only printable ASCII characters.
- Only alphabetic characters (a–z, A–Z) are affected by the cipher; digits, punctuation, and spaces are left unchanged.
- The recovered plaintext must be meaningful, grammatically coherent English.
- The output JSON must be parseable by Python's `json.load()` with no trailing commas or comments.
