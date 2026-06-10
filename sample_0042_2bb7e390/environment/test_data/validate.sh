#!/bin/bash
# Validates that the task was solved correctly
set -e

EXPECTED="a3f1b9c7d4e60218f5a7b3c9d1e4f60789abcdef0123456789abcdef01234567"
OUTPUT_FILE="/app/output.txt"

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "FAIL: $OUTPUT_FILE does not exist"
    exit 1
fi

ACTUAL=$(cat "$OUTPUT_FILE" | tr -d '[:space:]')

if [ "$ACTUAL" = "$EXPECTED" ]; then
    echo "PASS: Output matches expected 64-char hex string"
    exit 0
else
    echo "FAIL: Output does not match"
    echo "  Expected: $EXPECTED"
    echo "  Actual:   $ACTUAL"
    exit 1
fi
