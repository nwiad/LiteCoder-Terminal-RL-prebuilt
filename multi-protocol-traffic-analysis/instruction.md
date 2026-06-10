## Multi-Protocol Traffic Analysis & Message Reconstruction

Write a Python program that analyzes a simulated multi-protocol network traffic log file, extracts hidden message fragments embedded across HTTP, DNS, and SSH protocol entries, and reconstructs the original secret message.

### Technical Requirements

- Language: Python 3.x (standard library only)
- Input file: `/app/input.json`
- Output file: `/app/output.json`

### Input Format

The input file `/app/input.json` contains a JSON object with a single key `"traffic_log"`, which is an array of traffic entry objects. Each entry represents a captured network event from one of three protocols: `HTTP`, `DNS`, or `SSH`.

Every traffic entry has the following common fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier for the traffic entry |
| `timestamp` | string | ISO 8601 timestamp (e.g., `"2025-01-15T10:30:00Z"`) |
| `protocol` | string | One of `"HTTP"`, `"DNS"`, or `"SSH"` |
| `source_ip` | string | Source IP address |
| `dest_ip` | string | Destination IP address |

Each protocol type has additional protocol-specific fields containing a hidden fragment:

**HTTP entries** have an additional `headers` object. The hidden fragment is in `headers.X-Request-Token`. The value is a Base64-encoded string. Decode it to get the fragment payload.

**DNS entries** have an additional `query` string. The query is a domain name like `<encoded_part>.example.com`. Extract the first subdomain label (the part before the first `.`), then hex-decode it (treat it as a hex string) to get the fragment payload.

**SSH entries** have an additional `session_data` string. The value is a Base64-encoded string. Decode it to get the fragment payload.

Each decoded fragment payload is a JSON string with the following structure:

```json
{
  "seq": <integer>,
  "data": "<string>",
  "checksum": "<string>"
}
```

- `seq`: The sequence number (0-indexed) indicating the fragment's position in the final message.
- `data`: The text fragment of the hidden message.
- `checksum`: A CRC32 checksum (lowercase hex, 8 characters, zero-padded) of the `data` string (UTF-8 encoded bytes).

### Processing Rules

1. Parse all traffic entries from the input.
2. For each entry, extract and decode the hidden fragment according to its protocol type as described above.
3. Validate each fragment's integrity: compute the CRC32 checksum of `data` (UTF-8 bytes) and compare it with the provided `checksum`. Fragments with mismatched checksums must be discarded.
4. If multiple valid fragments share the same `seq` number, keep only the one with the earliest `timestamp`.
5. Order all valid fragments by `seq` in ascending order.
6. Concatenate the `data` fields in order to form the reconstructed message.

### Output Format

Write a JSON object to `/app/output.json` with the following structure:

```json
{
  "total_entries": <integer>,
  "valid_fragments": <integer>,
  "discarded_fragments": <integer>,
  "protocols_seen": [<string>, ...],
  "reconstructed_message": "<string>",
  "fragments": [
    {
      "seq": <integer>,
      "protocol": "<string>",
      "source_ip": "<string>",
      "data": "<string>",
      "checksum": "<string>"
    }
  ]
}
```

| Field | Description |
|---|---|
| `total_entries` | Total number of traffic entries in the input |
| `valid_fragments` | Number of fragments that passed checksum validation and were used (after deduplication) |
| `discarded_fragments` | Number of fragments that failed checksum validation |
| `protocols_seen` | Sorted list (alphabetically) of unique protocol names present in the input |
| `reconstructed_message` | The final concatenated message string |
| `fragments` | Array of used fragment details, ordered by `seq` |

### Edge Cases

- If the input file contains zero traffic entries, output `total_entries: 0`, `valid_fragments: 0`, `discarded_fragments: 0`, `protocols_seen: []`, `reconstructed_message: ""`, and `fragments: []`.
- Duplicate `seq` values: keep the fragment with the earliest timestamp; if timestamps are identical, keep the first one encountered in the input array.
- All fragment checksums could potentially be invalid, resulting in an empty reconstructed message.
