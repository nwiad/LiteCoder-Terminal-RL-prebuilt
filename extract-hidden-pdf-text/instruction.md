## Hidden Text Extraction from a PDF Document

Recover text that has been visually hidden inside a PDF file. A whistle-blower has released a PDF report (`/app/suspect.pdf`). On screen everything looks perfectly innocent, but a short secret text passage has been concealed in a way that is not visible to a normal reader. Your job is to locate and extract that hidden message.

### Technical Requirements

- Language: Python 3 (you may also use standard command-line PDF utilities available on Linux)
- Input file: `/app/suspect.pdf` — a valid PDF that contains one or more hidden text passages not visible when the PDF is rendered normally
- Output file: `/app/output.json`

### Creating the Input File

Before extraction, you must first create the test PDF `/app/suspect.pdf`. Build a valid PDF file that:
1. Contains visible text: `"This is a normal public report with nothing unusual."`
2. Contains the following hidden text that is NOT visible when the PDF is rendered or printed normally: `"The meeting is at 19:30 behind the old mill."`

The hidden text must be genuinely embedded inside the PDF structure (e.g., as invisible text-rendering mode, white-on-white text, text positioned off-page, text behind an opaque object, or appended after %%EOF) — it must not appear when the document is viewed in a standard PDF reader.

### Extraction and Output

After creating the PDF, write a Python script `/app/extract.py` that:
1. Reads `/app/suspect.pdf`
2. Extracts all hidden or non-visible text passages from the PDF
3. Computes the SHA-256 hash of each extracted text passage (hash the exact UTF-8 encoded bytes of the string, with no trailing newline)
4. Writes the results to `/app/output.json`

### Output Format

`/app/output.json` must be a JSON object with the following structure:

```json
{
  "hidden_texts": [
    {
      "text": "The meeting is at 19:30 behind the old mill.",
      "sha256": "<sha256 hex digest of the exact text bytes>"
    }
  ]
}
```

- `hidden_texts`: a JSON array containing one object per hidden text passage found.
- Each object has:
  - `text`: the exact extracted hidden string (trimmed of leading/trailing whitespace).
  - `sha256`: lowercase hex SHA-256 digest of the UTF-8 encoding of the `text` value (no trailing newline).
- The array must contain at least one entry with the correct hidden message and its matching hash.
