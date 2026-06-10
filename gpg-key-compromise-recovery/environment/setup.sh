#!/usr/bin/env bash
set -euo pipefail

# ── GPG Key Compromise & Recovery – Environment Setup ──
# This script creates the full GPG environment for the task.

export GNUPGHOME=/app/gpghome
mkdir -p "$GNUPGHOME" /app/releases /app/secrets /app/contributors /app/output
chmod 700 "$GNUPGHOME"

# ── Helper: generate a key non-interactively ──
gen_key() {
  local name="$1" email="$2" home="$3"
  mkdir -p "$home"
  chmod 700 "$home"
  gpg --homedir "$home" --batch --pinentry-mode loopback --passphrase '' \
      --quick-gen-key "$name <$email>" rsa3072 default never 2>/dev/null
  local fpr
  fpr=$(gpg --homedir "$home" --with-colons --list-keys "$email" 2>/dev/null \
        | awk -F: '/^fpr/{print $10; exit}')
  # Add signing, encryption, authentication subkeys
  gpg --homedir "$home" --batch --pinentry-mode loopback --passphrase '' \
      --quick-add-key "$fpr" rsa3072 sign never 2>/dev/null
  gpg --homedir "$home" --batch --pinentry-mode loopback --passphrase '' \
      --quick-add-key "$fpr" rsa3072 encr never 2>/dev/null
  gpg --homedir "$home" --batch --pinentry-mode loopback --passphrase '' \
      --quick-add-key "$fpr" rsa3072 auth never 2>/dev/null
  echo "$fpr"
}

# ── 1. Generate the compromised maintainer key ──
echo "[setup] Generating compromised maintainer key..."
OLD_FPR=$(gen_key "Maintainer" "maintainer@example.com" "$GNUPGHOME")
echo "$OLD_FPR" > /app/old_key_fingerprint.txt
echo "[setup] Old maintainer fingerprint: $OLD_FPR"

# ── 2. Generate contributor keys in their own keyrings ──
declare -A CONTRIB_FPRS
for user in alice bob carol; do
  echo "[setup] Generating key for ${user}@example.com..."
  CHOME="/app/contributors/${user}"
  fpr=$(gen_key "${user^}" "${user}@example.com" "$CHOME")
  CONTRIB_FPRS[$user]="$fpr"
  echo "[setup]   ${user} fingerprint: $fpr"

  # Export contributor public key and import into main keyring
  gpg --homedir "$CHOME" --batch --armor --export "${user}@example.com" \
    | gpg --homedir "$GNUPGHOME" --batch --import 2>/dev/null

  # Export old maintainer public key into contributor keyring
  gpg --homedir "$GNUPGHOME" --batch --armor --export "maintainer@example.com" \
    | gpg --homedir "$CHOME" --batch --import 2>/dev/null
done

# ── 3. Set trust in main keyring ──
for email in maintainer@example.com alice@example.com bob@example.com carol@example.com; do
  fpr=$(gpg --homedir "$GNUPGHOME" --with-colons --list-keys "$email" 2>/dev/null \
        | awk -F: '/^fpr/{print $10; exit}')
  echo "${fpr}:6:" | gpg --homedir "$GNUPGHOME" --batch --import-ownertrust 2>/dev/null
done

# Set trust in contributor keyrings for their own key and old maintainer key
for user in alice bob carol; do
  CHOME="/app/contributors/${user}"
  for email in "${user}@example.com" "maintainer@example.com"; do
    fpr=$(gpg --homedir "$CHOME" --with-colons --list-keys "$email" 2>/dev/null \
          | awk -F: '/^fpr/{print $10; exit}')
    echo "${fpr}:6:" | gpg --homedir "$CHOME" --batch --import-ownertrust 2>/dev/null
  done
done

# ── 4. Create release tarballs and sign them ──
echo "[setup] Creating release tarballs..."
TMPREL=$(mktemp -d)
for ver in 1.0 2.0 3.0; do
  echo "Release v${ver} contents" > "${TMPREL}/README-v${ver}.txt"
  tar czf "/app/releases/release-v${ver}.tar.gz" -C "$TMPREL" "README-v${ver}.txt"
  gpg --homedir "$GNUPGHOME" --batch --pinentry-mode loopback --passphrase '' \
      --detach-sign --armor -u "maintainer@example.com" \
      -o "/app/releases/release-v${ver}.tar.gz.sig" \
      "/app/releases/release-v${ver}.tar.gz" 2>/dev/null
  echo "[setup]   Signed release-v${ver}.tar.gz"
done
rm -rf "$TMPREL"

# ── 5. Create and encrypt secrets file ──
echo "[setup] Creating encrypted secrets..."
cat > /app/secrets/secrets.txt <<'SECRETS'
DB_PASSWORD=supersecret123
API_KEY=ak-9f8e7d6c5b4a3210
DEPLOY_TOKEN=dt-abcdef1234567890
SECRETS

gpg --homedir "$GNUPGHOME" --batch --pinentry-mode loopback --passphrase '' \
    --trust-model always --yes \
    -e -r "maintainer@example.com" \
    -r "alice@example.com" \
    -r "bob@example.com" \
    -r "carol@example.com" \
    -o /app/secrets/secrets.txt.gpg \
    /app/secrets/secrets.txt 2>/dev/null

echo "[setup] ── Environment ready ──"
echo "[setup] Old key fingerprint: $(cat /app/old_key_fingerprint.txt)"
echo "[setup] Releases in /app/releases/"
echo "[setup] Secrets in /app/secrets/"
echo "[setup] Contributor keyrings in /app/contributors/{alice,bob,carol}/"
echo "[setup] Output directory: /app/output/"
echo "[setup] Run your key rotation against GNUPGHOME=/app/gpghome"
