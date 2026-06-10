## Set up a Secure SFTP Server with Chrooted Users

Configure a secure SFTP-only server on the system using OpenSSH, with chrooted user accounts that can upload files but cannot access a shell or browse outside their designated directories.

### Requirements

1. **OpenSSH Server**
   - Ensure the `openssh-server` package is installed and the `sshd` service is running and enabled.

2. **SFTP User Group**
   - Create a system group named `sftpusers`.

3. **SSH Daemon Configuration (`/etc/ssh/sshd_config`)**
   - Override the default SFTP subsystem to use `internal-sftp`.
   - Add a `Match Group sftpusers` block at the end of the config with the following directives:
     - `ChrootDirectory /sftp/%u`
     - `ForceCommand internal-sftp`
     - `AllowTcpForwarding no`
     - `X11Forwarding no`
   - Restart or reload the `sshd` service after configuration changes so they take effect.

4. **Chroot Directory Structure**
   - For each SFTP user, create a chroot directory at `/sftp/<username>`.
   - The chroot directory (`/sftp/<username>`) must be owned by `root:root` with permissions `755`.
   - Inside each chroot, create an `uploads` directory at `/sftp/<username>/uploads` owned by the respective user and their primary group, with permissions `755`.

5. **Test User Accounts**
   - Create two user accounts: `sftpuser1` and `sftpuser2`.
   - Both users must belong to the `sftpusers` group.
   - Both users must have their shell set to `/usr/sbin/nologin` (or `/sbin/nologin`).
   - Set the password for `sftpuser1` to `Upload@2025` and `sftpuser2` to `Secure@2025`.
   - Set each user's home directory to their respective chroot path `/sftp/<username>`.

6. **New User Provisioning Script**
   - Create a script at `/app/create_sftp_user.sh` that automates adding a new SFTP user.
   - The script must accept exactly two positional arguments: `<username>` and `<password>`.
   - When executed (e.g., `bash /app/create_sftp_user.sh newuser MyP@ss123`), it must:
     - Create the user with shell `/usr/sbin/nologin`, add them to `sftpusers`, set the given password.
     - Create the chroot directory `/sftp/<username>` owned by `root:root` (permissions `755`).
     - Create `/sftp/<username>/uploads` owned by the new user (permissions `755`).
   - The script must exit with code `0` on success and non-zero on failure.

7. **SFTP Logging**
   - Configure the `internal-sftp` subsystem or the `Match Group` block to log SFTP activity at log level `INFO` or higher (e.g., using `LogLevel INFO` or `LogLevel VERBOSE` within the Match block, or via the `-l INFO` flag on the Subsystem directive).
   - SFTP log entries should be directed to syslog (default auth facility) and be visible in `/var/log/auth.log` (or the system's equivalent auth log).

8. **Documentation**
   - Write a plain-text documentation file at `/app/sftp_setup.txt` that contains at minimum:
     - A description of the SFTP group name used.
     - The chroot directory structure layout.
     - Instructions for adding a new SFTP user (referencing the script).
     - A note on where to find SFTP logs.
