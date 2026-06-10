## Automate User and Permission Management

Create a bash script that automates user creation, group management, and directory permission setup on an Ubuntu system.

### Requirements

- Script location: `/app/setup.sh`
- The script must be executable (`chmod +x`).
- The script must run successfully as root without interactive prompts.
- The script should include comments explaining each major section.

### Users and Groups

1. Create three user accounts: `dev1`, `dev2`, `dev3`. Each user must have a home directory created automatically and use `/bin/bash` as the default shell.
2. Create a user account `projectmanager` with a home directory and `/bin/bash` as the default shell.
3. Create two groups: `developers` and `projects`.
4. Add `dev1`, `dev2`, `dev3` to the `developers` group (as a supplementary group).
5. Add `projectmanager` to the `projects` group (as a supplementary group).

### Directory Structure and Permissions

1. Create the shared directory `/opt/projects`:
   - Owner: `root`
   - Group: `projects`
   - Permissions: `2775` (rwxrwsr-x, with SetGID bit set)

2. Create per-user subdirectories under `/opt/projects`:
   - `/opt/projects/dev1` — owner: `dev1`, group: `projects`, permissions: `2770`
   - `/opt/projects/dev2` — owner: `dev2`, group: `projects`, permissions: `2770`
   - `/opt/projects/dev3` — owner: `dev3`, group: `projects`, permissions: `2770`

   Each subdirectory must be accessible only by its respective owner and members of the `projects` group (no access for others).

### Umask Configuration

- For each developer user (`dev1`, `dev2`, `dev3`), append the line `umask 002` to their `~/.bashrc` file so that newly created files default to group-writable permissions.

### Idempotency

- The script should handle being run multiple times without producing errors. If a user, group, or directory already exists, the script should skip creation gracefully (no fatal errors).
