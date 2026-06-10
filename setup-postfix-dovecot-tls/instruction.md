## Mail Server Setup with Postfix, Dovecot, and TLS

Deploy a secure mail server using Postfix (SMTP) and Dovecot (IMAP) for the domain `example.tst`, enforcing TLS on all client-facing ports and restricting access to the local network `192.168.0.0/24`.

### Technical Requirements

- OS: Debian/Ubuntu-based Linux environment
- Packages: `postfix`, `dovecot-imapd`, `dovecot-core`, `ufw`
- Domain: `example.tst`
- Hostname: `mail.example.tst`

### 1. Postfix Configuration

Configure Postfix as the MTA with the following:

- **Hostname and domain:**
  - `myhostname = mail.example.tst`
  - `mydomain = example.tst`
  - `mydestination` must include `example.tst` and `mail.example.tst`
  - `mynetworks` must include `192.168.0.0/24`
  - HELO/banner must contain `mail.example.tst`
- **Listening ports:**
  - Port 25 (SMTP) — enabled in `/etc/postfix/master.cf`
  - Port 465 (SMTPS / `smtps`) — enabled with `smtpd_tls_wrappermode=yes`
  - Port 587 (submission) — enabled with `smtpd_tls_security_level=encrypt`
- **TLS settings in `/etc/postfix/main.cf`:**
  - `smtpd_tls_cert_file` and `smtpd_tls_key_file` must be set to valid file paths
  - `smtpd_tls_mandatory_protocols` must disallow TLSv1 and TLSv1.1 (i.e., enforce TLS 1.2+)
  - `smtpd_tls_security_level` set to `may` (opportunistic on port 25)
- **Relay restrictions:** `smtpd_recipient_restrictions` must include `reject_unauth_destination`
- **Rate limiting:** `smtpd_client_message_rate_limit` must be set to a positive integer value

### 2. Dovecot Configuration

Configure Dovecot for IMAPS with system-account authentication:

- **Protocols:** The Dovecot configuration must include `imap` in its protocols
- **IMAPS listener:** A `inet_listener imaps` block must be configured on port `993` with `ssl = yes`
- **Plaintext IMAP disabled:** Port 143 listener must be disabled (port set to `0` or listener removed entirely)
- **Authentication:** PAM-based auth must be enabled (an `auth-system.conf.ext` include or `passdb { driver = pam }` block must exist)
- **TLS settings:**
  - `ssl = required` must be set in the Dovecot SSL configuration
  - `ssl_cert` and `ssl_key` must point to valid file paths
  - `ssl_min_protocol` must be set to `TLSv1.2` (or equivalent)
  - `ssl_cipher_list` must be explicitly set to a non-empty value

### 3. TLS Certificates

- Generate a self-signed certificate (or use snakeoil certs) for `mail.example.tst`
- The certificate file referenced by both Postfix and Dovecot must exist on disk
- The key file referenced by both Postfix and Dovecot must exist on disk

### 4. Firewall (UFW)

Configure UFW rules so that ports 25, 465, 587, and 993 are allowed from `192.168.0.0/24`. After configuration, the output of `ufw status` must show rules allowing each of these four ports from `192.168.0.0/24`.

### 5. Test User

- Create a system user named `mailtest` (non-root, with a valid shell or `/usr/sbin/nologin`)
- The user must exist in `/etc/passwd`

### 6. Queue Monitoring Cron Job

- Add a cron job (in any system or user crontab) that runs hourly
- The job must write output to `/var/log/postfix_queue.log`
- The job must invoke `mailq`

### 7. Documentation File

Write a file at `/app/mail_server_doc.txt` containing:

- A line with the UID of the `mailtest` user in the format: `MAILTEST_UID=<uid>`
- A line with the GID of the `mailtest` user in the format: `MAILTEST_GID=<gid>`
- A line with the exact Dovecot TLS cipher string in the format: `DOVECOT_CIPHER_LIST=<cipher_string>`

Each key=value pair must be on its own line. Example:
```
MAILTEST_UID=1001
MAILTEST_GID=1001
DOVECOT_CIPHER_LIST=ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
```

### Service State

After all configuration is complete, both `postfix` and `dovecot` services must be in a running/active state (verifiable via `systemctl is-active postfix` and `systemctl is-active dovecot` or equivalent process checks).
