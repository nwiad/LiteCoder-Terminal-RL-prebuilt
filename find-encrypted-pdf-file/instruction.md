## Find the Encrypted PDF

Somewhere on this system, a password-protected PDF file has been hidden. Your task is to search the filesystem, locate the encrypted PDF, and report its full absolute path. You do not need to crack or read the file — just find it.

### Requirements

- Search the filesystem for all `.pdf` files.
- Identify which PDF file(s) are password-protected (encrypted).
- Confirm the file is a valid PDF and is encrypted by inspecting its properties (e.g., using tools like `qpdf`, `pdfinfo`, or `file`).
- Write the full absolute path of the encrypted PDF to `/app/output.txt`.

### Output

- File: `/app/output.txt`
- The file must contain exactly one line: the full absolute path of the encrypted PDF (e.g., `/some/path/to/file.pdf`).
- No trailing whitespace or extra lines beyond the path itself.
