## Task: Configure a Mail Server with Postfix and Dovecot

Set up a functional mail server using Postfix (SMTP) and Dovecot (IMAP) on Ubuntu with TLS encryption and user authentication.

**Technical Requirements:**
- Ubuntu Linux environment
- Postfix for SMTP service
- Dovecot for IMAP service
- TLS/SSL encryption enabled
- User authentication configured

**Configuration Specifications:**

1. **Postfix SMTP Configuration** (`/etc/postfix/main.cf`):
   - Set `myhostname` to a valid hostname
   - Configure `mydestination` to include localhost
   - Enable SASL authentication (`smtpd_sasl_auth_enable = yes`)
   - Configure TLS: `smtpd_tls_cert_file` and `smtpd_tls_key_file` must be set
   - Set `smtpd_tls_security_level = may`

2. **Dovecot IMAP Configuration** (`/etc/dovecot/dovecot.conf` or `/etc/dovecot/conf.d/`):
   - Enable `imap` protocol
   - Configure SSL: `ssl = yes` with valid cert and key paths
   - Set `mail_location` (e.g., maildir:~/Maildir)
   - Configure authentication mechanism (plain/login)

3. **User Accounts:**
   - Create at least 2 test user accounts with mailboxes
   - Users must be able to authenticate via SASL

4. **Service Status:**
   - Postfix service must be running and enabled
   - Dovecot service must be running and enabled

**Verification Output:**

Create a JSON file at `/app/mail_server_status.json` with the following structure:

```json
{
  "postfix": {
    "installed": true,
    "running": true,
    "tls_enabled": true,
    "sasl_enabled": true,
    "listening_port": 25
  },
  "dovecot": {
    "installed": true,
    "running": true,
    "ssl_enabled": true,
    "imap_enabled": true,
    "listening_port": 143
  },
  "test_users": ["user1", "user2"],
  "configuration_files": {
    "postfix_main_cf": "/etc/postfix/main.cf",
    "dovecot_conf": "/etc/dovecot/dovecot.conf"
  }
}
```

All boolean fields must reflect actual configuration state. Port numbers should match active listening ports.
