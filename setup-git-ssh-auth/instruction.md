## Git and SSH Configuration for Secure Development

Set up a secure, fully-functional Git environment with SSH key authentication on a developer workstation. All configuration must follow security best practices.

### Requirements

1. **Install Git**: Ensure Git is installed and available on the system PATH. Verify by running `git --version`.

2. **Configure Global Git User Settings**:
   - `user.name` set to `John Developer`
   - `user.email` set to `john.developer@example.com`
   - These must be set as global Git config values (i.e., in `~/.gitconfig`).

3. **Generate SSH Key Pair**:
   - Algorithm: Ed25519
   - Key file path: `~/.ssh/id_ed25519` (private) and `~/.ssh/id_ed25519.pub` (public)
   - Comment on the key: `john.developer@example.com`
   - No passphrase (empty passphrase)

4. **Configure SSH Client** by creating/updating `~/.ssh/config` with the following host entry:
   - A `Host github.com` block that specifies:
     - `HostName github.com`
     - `User git`
     - `IdentityFile ~/.ssh/id_ed25519`
     - `IdentitiesOnly yes`

5. **Set File Permissions**:
   - `~/.ssh` directory: `700`
   - `~/.ssh/id_ed25519` (private key): `600`
   - `~/.ssh/id_ed25519.pub` (public key): `644`
   - `~/.ssh/config`: `600`

6. **Initialize a Local Test Repository**:
   - Create a bare Git repository at `/app/test-repo.git` using `git init --bare`.
   - Clone it to `/app/test-workspace` via local path.
   - Inside `/app/test-workspace`, create a file `README.md` with the content `# Test Repository`.
   - Stage, commit (with message `Initial commit`), and push the commit back to the bare repo.

7. **Configure Git to Use SSH by Default**:
   - Set the global Git config `url."git@github.com:".insteadOf` to `https://github.com/`.

8. **Set Up Git Aliases** as global Git config:
   - `alias.co` → `checkout`
   - `alias.br` → `branch`
   - `alias.ci` → `commit`
   - `alias.st` → `status`
   - `alias.lg` → `log --oneline --graph --decorate`

9. **Documentation**: Write a configuration summary to `/app/setup-report.txt` containing:
   - A line with the Git version output (from `git --version`)
   - A line with the configured `user.name`
   - A line with the configured `user.email`
   - A line with the SSH public key fingerprint (output of `ssh-keygen -lf ~/.ssh/id_ed25519.pub`)
   - A line listing each configured Git alias and its value

The report must contain all five categories of information above, one per line or section, in plain text.
