#!/bin/bash
# Setup script: generates a suspicious ELF binary with hidden encrypted credentials
set -e

cd /app

# --- Configuration ---
XOR_KEY="s3cr3tK3y!"
SECTION_NAME=".note.dbg_info"

# Credentials to hide (plaintext, newline-separated as key=value pairs)
PLAINTEXT="username=admin&password=P@ssw0rd_2024!
username=backup_svc&password=Bkup#Secure99
username=root&password=R00t$hell_Access"

# --- XOR encrypt the plaintext ---
python3 -c "
import sys

key = '${XOR_KEY}'
plaintext = '''${PLAINTEXT}'''

encrypted = bytearray()
for i, ch in enumerate(plaintext.encode('utf-8')):
    encrypted.append(ch ^ ord(key[i % len(key)]))

with open('/app/_hidden_blob.bin', 'wb') as f:
    f.write(encrypted)
"

# --- Create a minimal C program that looks like a normal utility ---
cat > /app/_stub.c << 'CEOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Decoy: looks like a system monitoring tool */
static const char *banner = "sysmond v2.4.1 - system monitor daemon";

void check_status(void) {
    printf("[*] Checking system status...\n");
    sleep(1);
    printf("[*] All services nominal.\n");
}

int main(int argc, char *argv[]) {
    if (argc > 1 && strcmp(argv[1], "--version") == 0) {
        printf("%s\n", banner);
        return 0;
    }
    check_status();
    return 0;
}
CEOF

# --- Compile the stub binary ---
gcc -o /app/suspicious_binary /app/_stub.c -O2 -s

# --- Append the encrypted blob into a custom ELF section ---
objcopy --add-section "${SECTION_NAME}=/app/_hidden_blob.bin" \
        --set-section-flags "${SECTION_NAME}=noload,readonly" \
        /app/suspicious_binary /app/suspicious_binary

# --- Also embed the XOR key in a less obvious way: inside a fake .comment section ---
# We prepend some garbage compiler-like text around the key
python3 -c "
key = '${XOR_KEY}'
marker = b'GCC: (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0\x00xor_key=' + key.encode() + b'\x00'
with open('/app/_key_blob.bin', 'wb') as f:
    f.write(marker)
"

# Replace the existing .comment section with our crafted one
objcopy --remove-section=.comment /app/suspicious_binary /app/suspicious_binary 2>/dev/null || true
objcopy --add-section ".comment=/app/_key_blob.bin" \
        --set-section-flags ".comment=noload,readonly" \
        /app/suspicious_binary /app/suspicious_binary

# --- Cleanup temp files ---
rm -f /app/_stub.c /app/_hidden_blob.bin /app/_key_blob.bin

echo "[setup] suspicious_binary generated at /app/suspicious_binary"
