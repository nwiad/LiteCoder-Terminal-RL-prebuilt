#!/usr/bin/env bash
# AES-256-CBC encryption/decryption via OpenSSL (raw key+IV, no salt).
set -euo pipefail

usage() {
    echo "Usage: $0 -m encrypt|decrypt -i INPUT -o OUTPUT -k KEY_HEX -v IV_HEX"
    echo ""
    echo "Options:"
    echo "  -m MODE      encrypt or decrypt"
    echo "  -i INPUT     Input file path"
    echo "  -o OUTPUT    Output file path"
    echo "  -k KEY_HEX   AES-256 key as 64 hex characters"
    echo "  -v IV_HEX    IV as 32 hex characters"
    echo "  -h           Show this help"
    exit 0
}

MODE=""
INPUT=""
OUTPUT=""
KEY_HEX=""
IV_HEX=""

while getopts "m:i:o:k:v:h" opt; do
    case "$opt" in
        m) MODE="$OPTARG" ;;
        i) INPUT="$OPTARG" ;;
        o) OUTPUT="$OPTARG" ;;
        k) KEY_HEX="$OPTARG" ;;
        v) IV_HEX="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

if [[ -z "$MODE" || -z "$INPUT" || -z "$OUTPUT" || -z "$KEY_HEX" || -z "$IV_HEX" ]]; then
    echo "Error: all options -m, -i, -o, -k, -v are required." >&2
    usage
fi

case "$MODE" in
    encrypt)
        openssl enc -aes-256-cbc -in "$INPUT" -out "$OUTPUT" -K "$KEY_HEX" -iv "$IV_HEX" -nosalt
        echo "Encrypted $INPUT -> $OUTPUT"
        ;;
    decrypt)
        openssl enc -aes-256-cbc -d -in "$INPUT" -out "$OUTPUT" -K "$KEY_HEX" -iv "$IV_HEX" -nosalt
        echo "Decrypted $INPUT -> $OUTPUT"
        ;;
    *)
        echo "Error: mode must be 'encrypt' or 'decrypt'" >&2
        exit 1
        ;;
esac
