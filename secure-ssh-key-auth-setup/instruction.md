## Configure Secure SSH Access with Key-based Authentication

Harden SSH access on the server by disabling password authentication and enabling key-based authentication exclusively. Generate a new SSH key pair, apply the configuration, and document the procedure.

### Requirements

1. **SSH Key Pair Generation**
   - Generate an RSA key pair with 4096-bit key length for the current user.
   - Private key path: `~/.ssh/id_rsa` (no passphrase).
   - Public key path: `~/.ssh/id_rsa.pub`.
   - Add the generated public key to `~/.ssh/authorized_keys`.

2. **SSH Server Configuration**
   - Modify `/etc/ssh/sshd_config` to apply the following directives (each must appear as an uncommented, active line):
     - `PasswordAuthentication no`
     - `PubkeyAuthentication yes`
     - `ChallengeResponseAuthentication no`
     - `PermitRootLogin prohibit-password`
     - `UsePAM no`
   - If a directive already exists (commented or uncommented), update it in place. If it does not exist, append it.

3. **File and Directory Permissions**
   - `~/.ssh` directory: `700`
   - `~/.ssh/authorized_keys`: `600`
   - `~/.ssh/id_rsa` (private key): `600`
   - `~/.ssh/id_rsa.pub` (public key): `644`

4. **SSH Service**
   - Validate the SSH configuration is syntactically correct (e.g., using `sshd -t` or equivalent).
   - Restart (or reload) the SSH service to apply the new configuration.

5. **Documentation**
   - Write a summary document to `/app/ssh_access_procedure.txt`.
   - The document must contain all of the following sections (each as a line starting with the section name followed by a colon):
     - `Key Type:` — the algorithm and bit length used (e.g., `RSA 4096`)
     - `Private Key Path:` — absolute path to the private key
     - `Public Key Path:` — absolute path to the public key
     - `Disabled Settings:` — comma-separated list of disabled authentication methods (e.g., `PasswordAuthentication, ChallengeResponseAuthentication, UsePAM`)
     - `Enabled Settings:` — comma-separated list of enabled authentication settings (e.g., `PubkeyAuthentication`)
     - `PermitRootLogin:` — the value set for PermitRootLogin (e.g., `prohibit-password`)
