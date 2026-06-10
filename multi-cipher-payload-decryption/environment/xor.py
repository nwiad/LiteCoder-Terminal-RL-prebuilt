#!/usr/bin/env python3
"""XOR encrypt/decrypt a file with a repeating hex key."""
import argparse
import binascii
import sys

def main():
    parser = argparse.ArgumentParser(
        description="XOR encrypt or decrypt a file using a repeating key."
    )
    parser.add_argument("-i", "--input", required=True, help="Input file path")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument(
        "-k", "--key", required=True,
        help="Hex-encoded key string (e.g. 4a6f686e...)"
    )
    args = parser.parse_args()

    try:
        key_bytes = binascii.unhexlify(args.key)
    except (ValueError, binascii.Error) as e:
        print(f"Error: invalid hex key — {e}", file=sys.stderr)
        sys.exit(1)

    if len(key_bytes) == 0:
        print("Error: key must not be empty", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "rb") as f:
        data = f.read()

    result = bytearray(len(data))
    key_len = len(key_bytes)
    for i in range(len(data)):
        result[i] = data[i] ^ key_bytes[i % key_len]

    with open(args.output, "wb") as f:
        f.write(bytes(result))

    print(f"Done. Wrote {len(result)} bytes to {args.output}")

if __name__ == "__main__":
    main()
