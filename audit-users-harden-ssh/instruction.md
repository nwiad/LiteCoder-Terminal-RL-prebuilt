## User Audit and Expiration

Audit local user accounts from a provided dataset, classify them, set expiration policies, and harden SSH configuration. Produce a structured audit report and a secured SSH config file.

### Technical Requirements

- Language: Python 3
- Input: `/app/input.json`
- Outputs:
  - `/app/audit_report.json` — structured audit report
  - `/app/sshd_config` — hardened SSH configuration file

### Input Specification

`/app/input.json` contains a JSON object with two keys:

- `users`: an array of user account objects, each with:
  - `username` (string): the account name
  - `uid` (integer): user ID
  - `gid` (integer): group ID
  - `home` (string): home directory path
  - `shell` (string): login shell path
  - `comment` (string): GECOS/comment field (may be empty)

- `sshd_config_original`: a string containing the original sshd_config file content (multiline)

Example `input.json`:
```json
{
  "users": [
    {"username": "root", "uid": 0, "gid": 0, "home": "/root", "shell": "/bin/bash", "comment": "root"},
    {"username": "daemon", "uid": 1, "gid": 1, "home": "/usr/sbin", "shell": "/usr/sbin/nologin", "comment": "daemon"},
    {"username": "jdoe", "uid": 1001, "gid": 1001, "home": "/home/jdoe", "shell": "/bin/bash", "comment": "John Doe"},
    {"username": "nginx", "uid": 999, "gid": 999, "home": "/var/lib/nginx", "shell": "/usr/sbin/nologin", "comment": "nginx service"}
  ],
  "sshd_config_original": "Port 22\nPermitRootLogin yes\nProtocol 1,2\nPasswordAuthentication yes\n"
}
```

### Account Classification Rules

Each user must be classified as either `"human"` or `"service"` based on these rules:
1. A user is `"service"` if ANY of the following is true:
   - `uid` is 0 (root)
   - `uid` is less than 1000 (system/service range)
   - `shell` ends with `nologin` or `false`
2. All other users are classified as `"human"`.

### Output: `audit_report.json`

A JSON object with the following structure:

- `audit_date`: today's date in `YYYY-MM-DD` format
- `total_users`: integer count of all users
- `human_users`: integer count of human users
- `service_users`: integer count of service users
- `accounts`: an array of objects, one per user (in the same order as input), each with:
  - `username`: string
  - `uid`: integer
  - `classification`: `"human"` or `"service"`
  - `action`: string describing the action taken:
    - For human users: `"expiration_set"` — expiration set to 90 days from `audit_date` (format `YYYY-MM-DD`)
    - For service users: `"login_disabled"`
  - `expiration_date`: for human users, the date string (`YYYY-MM-DD`) that is exactly 90 days after `audit_date`. For service users, this field must be `null`.
  - `shell_status`: for service users, the string `"nologin"`. For human users, the original shell path.

### Output: `sshd_config`

Write a hardened version of the original sshd_config to `/app/sshd_config`. The following directives must be present with exact values (case-sensitive keys):

- `PermitRootLogin no`
- `Protocol 2`
- `PasswordAuthentication no`

Rules for generating the config:
- If a directive already exists in the original config, replace its value.
- If a directive does not exist, append it at the end.
- All other original lines must be preserved in their original order.
- No duplicate directive keys in the final output.
- Each directive must be on its own line in `Key Value` format (single space separator).
- The file must end with a newline character.
