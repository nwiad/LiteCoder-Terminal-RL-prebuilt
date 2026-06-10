## Encrypted Disk Image Forensics

Decrypt a password-protected evidence image, recover all files (including hidden/deleted ones), and produce a structured forensic report of files matching a specific project-numbering pattern.

### Technical Requirements

- Language/Tools: Python 3 (scripting), plus standard Linux CLI utilities (openssl, tar, sha256sum, etc.)
- Working directory: `/app`

### Input Files

- `/app/usb_evidence.img` — An OpenSSL AES-256-CBC (PBKDF2) encrypted archive containing a tar.gz of the suspect's files.
- `/app/wordlist.txt` — A newline-delimited word list; exactly one entry is the correct decryption password.

### Task Steps

1. Identify the encryption scheme of `usb_evidence.img`.
2. Use the supplied `wordlist.txt` to brute-force the decryption password. Try each word as the passphrase for OpenSSL AES-256-CBC with PBKDF2 until decryption succeeds.
3. Decrypt and extract the archive contents.
4. Enumerate all recovered files, including any inside subdirectories (treat these as "hidden" files).
5. Search every filename and file content for the regex pattern `PRJ-\d{4}`. Collect all matching project codes.
6. For each file that matches, record: its path within the archive, its size in bytes, and its SHA-256 hash.
7. Write the results to `/app/output.json`.

### Output Specification

Write a single JSON file to `/app/output.json` with the following structure:

```json
{
  "password": "<the correct password from wordlist.txt>",
  "flagged_files": [
    {
      "path": "<path of the file as it appeared inside the archive>",
      "size": <file size in bytes as integer>,
      "sha256": "<lowercase hex SHA-256 hash of the file>",
      "project_codes": ["PRJ-XXXX", ...]
    }
  ],
  "all_project_codes": ["PRJ-XXXX", ...]
}
```

Field details:
- `password`: The single word from `wordlist.txt` that successfully decrypts the image.
- `flagged_files`: An array of objects, one per file whose name or content matches `PRJ-\d{4}`. Each object contains:
  - `path`: The file's relative path inside the extracted archive (e.g., `content/somefile.txt`).
  - `size`: File size in bytes (integer).
  - `sha256`: Lowercase hexadecimal SHA-256 digest of the file.
  - `project_codes`: A sorted list of all distinct `PRJ-\d{4}` codes found in that file's name and content combined.
- `all_project_codes`: A sorted, deduplicated list of every `PRJ-\d{4}` code found across all flagged files.

### Constraints

- Every file inside the archive that contains or whose filename contains the pattern `PRJ-\d{4}` must appear in `flagged_files`.
- `all_project_codes` must be sorted in ascending lexicographic order.
- Each file's `project_codes` list must also be sorted in ascending lexicographic order.
- SHA-256 hashes must be lowercase hexadecimal strings (64 characters).
- The output JSON must be valid and parseable.
