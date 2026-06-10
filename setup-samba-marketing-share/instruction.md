## Task: Configure a Secure File Sharing Service with Samba

Set up a secure Samba file-sharing service with authenticated access, proper permissions, and audit logging for a marketing team to share files with internal staff and external partners.

**Technical Requirements:**
- Ubuntu/Debian Linux system
- Samba 4.x or later
- Configuration file: `/etc/samba/smb.conf`
- Shared directory: `/srv/samba/marketing`
- User database: Samba's tdbsam backend

**User and Group Setup:**
- Create system group: `marketing`
- Create three users with Samba passwords:
  - `alice` (internal staff, read/write access, member of marketing group)
  - `bob` (internal staff, read/write access, member of marketing group)
  - `partner1` (external partner, read-only access, NOT in marketing group)

**Samba Share Configuration:**
- Share name: `[marketing]`
- Path: `/srv/samba/marketing`
- Valid users: `@marketing, partner1`
- Write access: `@marketing` only
- Read-only users: `partner1`
- Guest access: disabled
- Encryption: required (SMB3 encryption enabled)

**Security Requirements:**
- Minimum SMB protocol version: SMB2
- Server role: standalone server
- Security mode: user-level authentication
- Audit logging enabled with full VFS module (log read/write operations to syslog)
- Firewall: Allow Samba ports (139, 445) only from localhost for testing

**Directory Permissions:**
- `/srv/samba/marketing` owned by `root:marketing`
- Directory permissions: `2770` (setgid bit set)
- All files created inherit group ownership

**Verification Requirements:**
After configuration, the system must:
1. Have Samba service running and enabled at boot
2. Allow alice and bob to read/write files in the share
3. Allow partner1 to read but NOT write files in the share
4. Reject unauthenticated access attempts
5. Log file access operations to `/var/log/samba/audit.log` or syslog
6. Maintain proper file ownership (group: marketing) for new files

**Output:**
Create a verification report at `/app/verification_report.txt` containing:
- Samba service status (active/inactive)
- List of configured shares
- List of Samba users
- Firewall rules for ports 139 and 445
- Directory permissions for `/srv/samba/marketing`
- Confirmation that audit logging is enabled
