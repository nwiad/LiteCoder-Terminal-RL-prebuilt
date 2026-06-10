#!/bin/bash
set -e

# Define the secret flag/plaintext
FLAG="FLAG{sym_k3y_r3c0v3r3d_2024}"

# Define the password that will be embedded in the image
PASSWORD="cr4ckTh1s_s3cr3t!"

# --- Step 1: Create a valid JPEG image using ImageMagick ---
convert -size 200x200 xc:blue -fill white -gravity center -pointsize 20 -annotate 0 "Secret" /app/secret_image.jpg

# --- Step 2: Embed the password into the image using steghide ---
echo -n "$PASSWORD" > /tmp/password.txt
steghide embed -cf /app/secret_image.jpg -ef /tmp/password.txt -p "" -f
rm /tmp/password.txt

# --- Step 3: Create the hidden directory tree and encrypt the flag ---
mkdir -p /app/hidden/deep/nested/folder
echo -n "$FLAG" | openssl enc -aes-256-cbc -pbkdf2 -pass "pass:${PASSWORD}" -out /app/hidden/deep/nested/folder/symmetric_key.enc

# --- Step 4: Add some decoy files to make the search non-trivial ---
echo "not a key" > /app/hidden/readme.txt
mkdir -p /app/hidden/logs
echo "log entry 1" > /app/hidden/logs/access.log
echo "nothing here" > /app/hidden/deep/notes.txt
mkdir -p /app/hidden/deep/nested/other
echo "decoy data" > /app/hidden/deep/nested/other/data.bin

# --- Cleanup: remove output files if they exist (agent must create them) ---
rm -f /app/output.txt /app/flag.txt

echo "Setup complete. Test data created successfully."
