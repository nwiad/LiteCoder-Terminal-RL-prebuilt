## Git-based Website Deployment System

Set up a Git-based website deployment system using a bare repository and a post-receive hook that automatically deploys site content to a web-accessible directory when code is pushed.

### Technical Requirements

- Environment: Linux container with bash
- Tools: Git, SSH (openssh-server)

### Setup Specifications

1. **System user for deployments:**
   - Create a system user named `deployer`.
   - The `deployer` user must have a valid home directory at `/home/deployer`.
   - The `deployer` user's default shell must be a valid login shell (e.g., `/bin/bash`).

2. **SSH key authentication:**
   - Generate an SSH key pair for the `deployer` user (type: ed25519, no passphrase).
   - The private key must be at `/home/deployer/.ssh/id_ed25519`.
   - The public key must be at `/home/deployer/.ssh/id_ed25519.pub`.
   - The public key must be added to `/home/deployer/.ssh/authorized_keys`.
   - The `.ssh` directory permissions must be `700`, and `authorized_keys` permissions must be `600`.

3. **Bare Git repository:**
   - Create a bare Git repository at `/srv/git/website.git`.
   - The repository must be owned by the `deployer` user.

4. **Post-receive hook:**
   - Create an executable post-receive hook at `/srv/git/website.git/hooks/post-receive`.
   - The hook must deploy the contents of the `main` branch to the web directory `/var/www/html` whenever a push to `main` is received.
   - The hook file must be owned by the `deployer` user and be executable.

5. **Web deployment directory:**
   - The deployment target directory is `/var/www/html`.
   - This directory must exist and be writable by the `deployer` user.

6. **Local repository and deployment test:**
   - Initialize a local Git repository at `/home/deployer/website-local`.
   - The local repo must have a remote named `production` pointing to the bare repository (`/srv/git/website.git`).
   - The local repo must contain at least an `index.html` file on the `main` branch with the content:
     ```
     <html><body><h1>Deployed via Git</h1></body></html>
     ```
   - Push the `main` branch from the local repo to the `production` remote.

### Verification Criteria

After the full setup and push:

- The file `/var/www/html/index.html` must exist and contain the string `Deployed via Git`.
- The bare repository at `/srv/git/website.git` must have at least one commit on the `main` branch.
- The post-receive hook at `/srv/git/website.git/hooks/post-receive` must be executable and reference the `main` branch and `/var/www/html`.
- SSH key-based authentication files must be in place for the `deployer` user with correct permissions.
