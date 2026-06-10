## Break the "Unbreakable" Cipher

Crack a multi-layered homemade cipher hidden inside a web page's source code and recover the secret flag.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.html` — an HTML page containing an encrypted message hidden in an HTML comment
- Output: `/app/output.json`

### Task Details

1. Parse the HTML file at `/app/input.html` and extract the ciphertext and any cipher-related metadata from the HTML comments.
2. The encryption was applied in this order during encryption: **Caesar shift → Vigenère cipher → Custom substitution**. To decrypt, reverse the operations in the opposite order.
3. The HTML comment contains:
   - The custom substitution mapping (original alphabet and its mapped alphabet)
   - The ciphertext string
4. You must determine the Caesar shift value and the Vigenère key by analyzing the cipher. The Caesar shift is a single integer (1–25). The Vigenère key is a lowercase English word.
5. Non-alphabetic characters (digits, underscores, curly braces, etc.) are not affected by any cipher layer — they pass through unchanged.
6. All alphabetic characters in the ciphertext are lowercase.

### Output Format

Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "ciphertext": "<the extracted ciphertext string>",
  "caesar_shift": <integer>,
  "vigenere_key": "<string>",
  "plaintext": "<the fully decrypted flag>"
}
```

- `ciphertext`: the raw ciphertext extracted from the HTML comment
- `caesar_shift`: the Caesar shift value used during encryption
- `vigenere_key`: the Vigenère key used during encryption (lowercase)
- `plaintext`: the final decrypted plaintext flag, in the format `flag{...}`
