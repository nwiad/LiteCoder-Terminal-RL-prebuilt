## Audit and Secure SSH Service on Ubuntu

You have inherited a server whose SSH daemon accepts a wide range of authentication mechanisms. Harden the configuration so that ONLY public-key authentication is allowed, and produce an audit report of the changes.

### Environment

- OS: Ubuntu (with OpenSSH server installed)
- Working directory: `/app`
- The active sshd configuration file is `/etc/ssh/sshd_config` (and any included files under `/etc/ssh/sshd_config.d/`)

### Requirements

Complete the following steps in order:

1. **Pre-hardening audit**: Collect all effective authentication-related settings from the running SSH daemon (use `sshd -T` to query the effective configuration). Write the output to `/app/pre_audit.txt`. This file must contain at least the following directive names (one per line, in `key value` format as output by `sshd -T`): `pubkeyauthentication`, `passwordauthentication`, `kbdinteractiveauthentication`, `hostbasedauthentication`, `gssapiauthentication`, `kerberosauthentication`.

2. **Syntax check (pre-change)**: Run `sshd -t` against the current configuration. Write the exit code (`0` for success) to `/app/syntax_check_before.txt` (just the number, no trailing whitespace beyond a newline).

3. **Backup**: Copy the current `/etc/ssh/sshd_config` to `/app/sshd_config.bak`. The backup must be a byte-identical copy of the original file.

4. **Harden the configuration**: Edit `/etc/ssh/sshd_config` (and/or drop-in files under `/etc/ssh/sshd_config.d/`) so that the effective configuration satisfies ALL of the following when queried via `sshd -T`:
   - `pubkeyauthentication yes`
   - `passwordauthentication no`
   - `kbdinteractiveauthentication no`
   - `hostbasedauthentication no`
   - `gssapiauthentication no`
   - `kerberosauthentication no`
   - `challengeresponseauthentication no` (if the directive exists on this OpenSSH version)
   - `permitrootlogin` must be set to `prohibit-password` or `no`

5. **Syntax check (post-change)**: Run `sshd -t` against the new configuration. Write the exit code to `/app/syntax_check_after.txt` (same format as step 2). The value must be `0`.

6. **Reload the daemon**: Reload (not restart) the sshd service only if the syntax check in step 5 passed. Write either `reloaded` or `skipped` to `/app/reload_status.txt` (single word, no extra whitespace beyond a newline).

7. **Post-hardening audit**: Collect the effective authentication settings again via `sshd -T` and write the output to `/app/post_audit.txt`. The same directive names listed in step 1 must appear, now reflecting the hardened values.

8. **Cron job for drift detection**: Install a cron job for root that runs daily and performs the following:
   - Compares `/etc/ssh/sshd_config` against `/app/sshd_config.bak` using `diff`
   - Mails the diff output (if any) to `root` with subject `sshd configuration drift`
   - The cron entry must be verifiable via `crontab -l -u root`
   Write the exact cron line to `/app/cronjob.txt` as well.

### Output Files Summary

| File | Description |
|---|---|
| `/app/pre_audit.txt` | Effective sshd auth settings before hardening |
| `/app/syntax_check_before.txt` | Exit code of `sshd -t` before changes |
| `/app/sshd_config.bak` | Byte-identical backup of original sshd_config |
| `/app/syntax_check_after.txt` | Exit code of `sshd -t` after changes (must be `0`) |
| `/app/reload_status.txt` | `reloaded` or `skipped` |
| `/app/post_audit.txt` | Effective sshd auth settings after hardening |
| `/app/cronjob.txt` | The cron line installed for drift detection |
