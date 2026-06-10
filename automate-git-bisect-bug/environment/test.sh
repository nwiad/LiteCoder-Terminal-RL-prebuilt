#!/bin/bash
# Test script for git bisect automation
# Returns 0 if test passes, non-zero if test fails

python3 /app/app.py > /tmp/output.txt 2>&1

# Check if the divide function returns correct result
if grep -q "20 / 5 = 4.0" /tmp/output.txt; then
    exit 0
else
    exit 1
fi
