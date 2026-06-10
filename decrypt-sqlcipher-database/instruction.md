## Decrypt the Encrypted SQLite Database

Recover the plaintext contents of an encrypted SQLite database by analyzing a memory dump, source code fragment, and wordlist to find the encryption passphrase.

**Technical Requirements:**
- Python 3.x
- SQLCipher library (pysqlcipher3 or sqlcipher)
- Standard libraries: hashlib, struct, binascii

**Input Files:**
- `/app/clients.db` - Encrypted SQLite database
- `/app/mem.dump` - Memory dump file containing encryption artifacts
- `/app/db_encrypt.py` - Python source fragment showing SQLCipher configuration
- `/app/wordlist.txt` - List of candidate passphrases (one per line)

**Output File:**
- `/app/result.json` - JSON file containing the recovered passphrase and client records

**Task Requirements:**

1. **Memory Analysis:** Extract the SQLCipher salt and derived key material from the memory dump using string/hex analysis techniques.

2. **KDF Parameter Recovery:** Parse the source fragment to identify the exact PBKDF2 parameters (iterations, hash function, key length).

3. **Passphrase Recovery:** Implement a brute-force script that:
   - Reads candidates from the wordlist
   - Applies PBKDF2-HMAC-SHA256 with recovered parameters
   - Matches the derived key against memory dump artifacts
   - Identifies the correct passphrase

4. **Database Decryption:** Use the recovered passphrase to decrypt the SQLite database and extract all client records.

5. **Output Format:** Write results to `/app/result.json` with this structure:
```json
{
  "passphrase": "recovered_passphrase_string",
  "client_records": [
    {"field1": "value1", "field2": "value2"},
    ...
  ]
}
```

The client_records array should contain all rows from the main client data table in the database, preserving all columns and their original data types (as JSON-compatible values).
