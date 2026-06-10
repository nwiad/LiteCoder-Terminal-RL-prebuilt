## Harden SSH Access with Two-Factor Authentication and Key-Based Auth

Secure an Ubuntu server by enforcing SSH login via public-key authentication combined with TOTP (Time-based One-Time Password) as a second factor for all sudo group users, and completely disable password authentication. Document all changes in a runbook.

### Technical Requirements

- **OS:** Ubuntu 22.04
- **Packages:** `libpam-google-authenticator` must be installed
- **Output files:**
  - `/app/runbook.md` — a step-by-step runbook documenting every change made
  - `/app/config_summary.json` — a JSON summary of the final configuration state (schema below)

### User and Group Setup

1. Create a user `admin2` that belongs to the `sudo` group.
2. Generate an ED25519 SSH key pair for `admin2`:
   - Private key: `/home/admin2/.ssh/id_ed25519`
   - Public key: `/home/admin2/.ssh/id_ed25519.pub`
3. Deploy the public key to `/home/admin2/.ssh/authorized_keys` with permissions `600`, and `.ssh` directory with permissions `700`. Owner must be `admin2`.
4. Initialize Google Authenticator for `admin2` (non-interactive, time-based, with rate limiting). The config file must exist at `/home/admin2/.google_authenticator`.

### SSH Daemon Configuration (`/etc/ssh/sshd_config` or drop-in under `/etc/ssh/sshd_config.d/`)

The following directives must be set exactly:

| Directive | Required Value |
|---|---|
| `PasswordAuthentication` | `no` |
| `ChallengeResponseAuthentication` | `no` |
| `PubkeyAuthentication` | `yes` |
| `AuthenticationMethods` | `publickey,keyboard-interactive` |
| `KbdInteractiveAuthentication` | `yes` |
| `PermitRootLogin` | `no` |
| `AllowGroups` | must include `sudo` |
| `UsePAM` | `yes` |

Additionally, restrict ciphers to only AES-256 and ChaCha20 variants (the `Ciphers` directive must be explicitly set and must not include any CBC-mode ciphers).

The SSH configuration must pass syntax validation (`sshd -t` returns exit code 0).

### PAM Configuration (`/etc/pam.d/sshd`)

- The file must contain a line that loads `pam_google_authenticator.so`.
- This module must be configured as `auth required` (not `auth sufficient`).
- The `@include common-auth` line for password-based auth should be commented out or removed.

### Root Account

- Root direct SSH login must be disabled (`PermitRootLogin no`).
- The root account password login should be locked (via `passwd -l root` or equivalent).

### Output: `/app/config_summary.json`

Produce a JSON file with the following structure:

```json
{
  "admin2_user_exists": true,
  "admin2_in_sudo_group": true,
  "ssh_key_type": "ed25519",
  "authorized_keys_path": "/home/admin2/.ssh/authorized_keys",
  "authorized_keys_permissions": "600",
  "ssh_dir_permissions": "700",
  "google_authenticator_initialized": true,
  "sshd_config": {
    "PasswordAuthentication": "no",
    "ChallengeResponseAuthentication": "no",
    "PubkeyAuthentication": "yes",
    "AuthenticationMethods": "publickey,keyboard-interactive",
    "KbdInteractiveAuthentication": "yes",
    "PermitRootLogin": "no",
    "AllowGroups": "sudo",
    "UsePAM": "yes",
    "Ciphers": "<actual cipher string set>"
  },
  "pam_google_authenticator_enabled": true,
  "pam_common_auth_disabled": true,
  "root_password_locked": true,
  "sshd_config_syntax_valid": true
}
```

All boolean fields must reflect the actual system state after configuration. The `Ciphers` field must contain the exact cipher string configured.

### Runbook (`/app/runbook.md`)

The runbook must document each configuration step performed, in order, including:
- Package installation commands
- User creation and key deployment steps
- SSH daemon configuration changes
- PAM configuration changes
- Root account hardening
- Validation and service restart commands

Each step must include the exact command(s) executed.
