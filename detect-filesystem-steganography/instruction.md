## Detecting Covert File-System Tunneling

Analyze a simulated 16 MiB USB stick disk image to detect and extract data hidden via steganographic file-system tunneling beneath an innocent-looking FAT32 partition.

### Setup

Write a Python script `/app/create_image.py` that generates the disk image `/app/usb_stick.img` (exactly 16 MiB = 16,777,216 bytes) with the following structure:

1. A valid FAT32 file system occupying the image, containing exactly two visible files:
   - `README.txt` with the content `This is a normal USB stick.\n`
   - `photo.jpg` — any small placeholder content (at least 512 bytes)
2. A hidden ext2 file system embedded in the slack/unallocated area of the image starting at an offset that is a multiple of 32 KiB (choose one of: 32 KiB, 64 KiB, 128 KiB, or 256 KiB from the end of the FAT32 used area or at a fixed offset within the unallocated region). The hidden ext2 image must contain exactly one file named `firmware.bin` whose content is the UTF-8 string `SECRET_FIRMWARE_PAYLOAD_2024`.

Run `create_image.py` to produce `/app/usb_stick.img`.

### Analysis

Write a Python script `/app/analyze.py` that takes the disk image path as its first command-line argument:

```
python3 /app/analyze.py /app/usb_stick.img
```

The script must perform the following analysis steps and produce two output files:

#### Output 1: `/app/forensic_report.json`

A JSON file with the following top-level keys:

| Key | Type | Description |
|---|---|---|
| `image_size` | integer | Total size of the disk image in bytes |
| `fat32_detected` | boolean | Whether a valid FAT32 boot sector was found |
| `visible_files` | array of strings | List of file names found in the FAT32 root directory |
| `total_clusters` | integer | Total number of clusters in the FAT32 partition |
| `used_clusters` | integer | Number of clusters allocated to visible files |
| `slack_bytes` | integer | Number of bytes in unallocated/slack space (must be > 0) |
| `slack_chi_squared` | number | Chi-squared statistic of the byte distribution in the slack area |
| `slack_is_random` | boolean | `true` if the chi-squared test suggests the slack area contains random/encrypted data (p-value < 0.05 against uniform distribution), `false` otherwise |
| `hidden_fs_found` | boolean | Whether a hidden file system (ext2/ext3/ext4) was detected in the slack area |
| `hidden_fs_type` | string or null | The type of hidden file system detected (e.g., `"ext2"`, `"ext4"`), or `null` if none found |
| `hidden_fs_offset` | integer or null | Byte offset where the hidden file system starts, or `null` if none found |
| `hidden_files` | array of strings | List of file names found inside the hidden file system (empty array if none) |
| `firmware_sha256` | string or null | SHA-256 hex digest of the extracted firmware blob, or `null` if not found |

#### Output 2: `/app/extracted_firmware.bin`

If a hidden firmware blob is found, write its raw content to this file. If nothing is found, do not create this file.

### Technical Requirements

- Language: Python 3
- No external dependencies beyond the Python standard library are required, but you may use `struct`, `hashlib`, `json`, `math`, `sys`, `os` and similar stdlib modules.
- You may shell out to system tools (e.g., `mkfs.fat`, `mkfs.ext2`, `dd`) in `create_image.py` for image creation if needed.
- `analyze.py` must perform its own binary parsing — do not rely on mounting the image or calling external forensic tools. All FAT32 and ext2 structure parsing must be done in Python by reading raw bytes from the image file.
- The `firmware_sha256` value in the report must be the SHA-256 hex digest of the exact content of `firmware.bin` as stored inside the hidden file system.
