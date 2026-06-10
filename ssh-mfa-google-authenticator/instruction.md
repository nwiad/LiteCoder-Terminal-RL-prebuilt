## Configure SSH Multi-Factor Authentication

Set up multi-factor authentication (MFA) for SSH access on an Ubuntu server using Google Authenticator, requiring both public key and TOTP verification for all users except a designated emergency account.

### Technical Requirements

- Operating System: Ubuntu (current environment)
- PAM module: `libpam-google-authenticator`
- All configuration changes must be made to the actual system files described below.

### Requirements

1. **Install Google Authenticator PAM Module**
   - Install the `libpam-google-authenticator` package.

2. **Configure PAM for SSH**
   - Edit `/etc/pam.d/sshd` to include the Google Authenticator PAM module.
   - The PAM configuration must contain a line that loads `pam_google_authenticator.so` with the `nullok` option (to allow users who haven't yet set up TOTP to still log in).
   - The `pam_google_authenticator.so` line must NOT be commented out.

3. **Configure SSHD**
   - Edit `/etc/ssh/sshd_config` (or create a drop-in file at `/etc/ssh/sshd_config.d/mfa.conf`) so that the following directives are active (not commented out):
     - `ChallengeResponseAuthentication yes`
     - `UsePAM yes`
     - `PubkeyAuthentication yes`
     - `AuthenticationMethods publickey,keyboard-interactive`
   - Add a `Match User` block for the emergency user `emergency_admin` that sets:
     - `AuthenticationMethods publickey`
     This allows `emergency_admin` to authenticate with only a public key, bypassing MFA.

4. **Create Emergency User**
   - Create a system user named `emergency_admin`.
   - Create the directory `/home/emergency_admin/.ssh/` with permissions `700`, owned by `emergency_admin`.
   - Create the file `/home/emergency_admin/.ssh/authorized_keys` with permissions `600`, owned by `emergency_admin`.

5. **Create Test User and Generate TOTP Secret**
   - Create a system user named `mfa_testuser`.
   - Run `google-authenticator` (non-interactively) for `mfa_testuser` to generate a TOTP secret. The generated config must be stored at `/home/mfa_testuser/.google_authenticator`.
   - The TOTP secret file must:
     - Be owned by `mfa_testuser`.
     - Have permissions `400` or `600`.
     - Contain a secret key as the first line (a base32-encoded string).

6. **Configuration Summary Output**
   - Write a JSON file to `/app/output.json` with the following structure:

```json
{
  "pam_module_installed": true,
  "pam_sshd_config": "/etc/pam.d/sshd",
  "sshd_config_file": "<path to the sshd config file you edited, e.g. /etc/ssh/sshd_config or /etc/ssh/sshd_config.d/mfa.conf>",
  "challenge_response_auth": "yes",
  "use_pam": "yes",
  "pubkey_auth": "yes",
  "authentication_methods": "publickey,keyboard-interactive",
  "emergency_user": "emergency_admin",
  "emergency_user_auth_method": "publickey",
  "test_user": "mfa_testuser",
  "totp_secret_file": "/home/mfa_testuser/.google_authenticator"
}
```

All JSON keys must be present. Boolean values must be JSON booleans. String values must be JSON strings.
