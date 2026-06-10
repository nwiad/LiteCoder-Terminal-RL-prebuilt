#!/usr/bin/env bash
# 3DES-CBC encryption/decryption via OpenSSL (salted, pbkdf2).
set -euo pipefail

usage() {
    echo "Usage: $0 -m encrypt|decrypt -i INPUT -o OUTPUT -p PASSWORD"
    echo ""
    echo "Options:"
    echo "  -m MODE      encrypt or decrypt"
    echo "  -i INPUT     Input file path"
    echo "  -o OUTPUT    Output file path"
    echo "  -p PASSWORD  Password string (plaintext)"
    echo "  -h           Show this help"
    exit 0
}

MODE=""
INPUT=""
OUTPUT=""
PASSWORD=""

while getopts "m:i:o:p:h" opt; do
    case "$opt" in
        m) MODE="$OPTARG" ;;
        i) INPUT="$OPTARG" ;;
        o) OUTPUT="$OPTARG" ;;
        p) PASSWORD="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

if [[ -z "$MODE" || -z "$INPUT" || -z "$OUTPUT" || -z "$PASSWORD" ]]; then
    echo "Error: all options -m, -i, -o, -p are required." >&2
    usage
fi

case "$MODE" in
    encrypt)
        openssl enc -des-ede3-cbc -pbkdf2 -in "$INPUT" -out "$OUTPUT" -pass "pass:$PASSWORD"
        echo "Encrypted $INPUT -> $OUTPUT"
        ;;
    decrypt)
        openssl enc -des-ede3-cbc -d -pbkdf2 -in "$INPUT" -out "$OUTPUT" -pass "pass:$PASSWORD"
        echo "Decrypted $INPUT -> $OUTPUT"
        ;;
    *)
        echo "Error: mode must be 'encrypt' or 'decrypt'" >&2
        exit 1
        ;;
esac
