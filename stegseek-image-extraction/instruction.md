## Detecting and Extracting Steganographic Images using Stegseek

You are a security analyst investigating images suspected of containing steganographically hidden data. Use Stegseek to analyze the images in `/app/images/` and extract any concealed messages.

### Technical Requirements

- Language: Bash/Shell scripting (Python 3.x allowed for JSON output generation)
- Tool: `stegseek` (install if not present, along with any dependencies)
- Working directory: `/app`

### Input

- Image directory: `/app/images/` — contains JPEG image files to analyze.
- Wordlist: `/app/wordlist.txt` — you must create this file before running detection. It must contain at least 30 entries, including common passwords (e.g., `password`, `123456`, `letmein`, `admin`) and company-themed terms (e.g., `corporate`, `internal`, `confidential`, `project`, `secret`, `employee`, `report`).

### Setup

Before analysis, create the test images by performing the following steps:

1. Install `steghide` and `stegseek` (and any required dependencies).
2. Create three JPEG image files in `/app/images/`:
   - `image1.jpg` — a valid JPEG with a hidden message `"Project Atlas is compromised"` embedded using `steghide` with passphrase `corporate`.
   - `image2.jpg` — a valid JPEG with a hidden message `"Meet at dock 7 midnight"` embedded using `steghide` with passphrase `secret`.
   - `image3.jpg` — a valid JPEG with no hidden data (clean image, no steganographic content).

### Task

1. Create the wordlist at `/app/wordlist.txt`.
2. Run `stegseek` against each image in `/app/images/` using the wordlist.
3. For each image where hidden data is found, extract the message content.
4. Write all findings to `/app/output.json`.

### Output

Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "analyzed_count": 3,
  "positive_count": 2,
  "findings": [
    {
      "filename": "image1.jpg",
      "stego_detected": true,
      "passphrase": "corporate",
      "extracted_message": "Project Atlas is compromised"
    },
    {
      "filename": "image2.jpg",
      "stego_detected": true,
      "passphrase": "secret",
      "extracted_message": "Meet at dock 7 midnight"
    },
    {
      "filename": "image3.jpg",
      "stego_detected": false,
      "passphrase": null,
      "extracted_message": null
    }
  ]
}
```

Requirements for `output.json`:
- `analyzed_count`: integer, total number of images analyzed.
- `positive_count`: integer, number of images where steganographic content was detected.
- `findings`: array of objects, one per image file in `/app/images/`, sorted alphabetically by `filename`.
- Each finding must include `filename` (string), `stego_detected` (boolean), `passphrase` (string or null), and `extracted_message` (string or null, trimmed of leading/trailing whitespace).
- For clean images, `passphrase` and `extracted_message` must be `null`.

### Cleanup

Remove any temporary extraction output files after their content has been captured into `output.json`. The `/app/images/` directory and `/app/wordlist.txt` should remain intact.
