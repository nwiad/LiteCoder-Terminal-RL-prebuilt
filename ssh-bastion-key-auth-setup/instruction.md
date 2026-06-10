## Configure SSH Key-Based Authentication with Bastion Host

Create a set of SSH configuration files and a setup script that implements a secure bastion host (jump server) architecture for accessing internal servers using key-based authentication only.

### Technical Requirements

- Language/Tools: Bash (shell script), OpenSSH configuration syntax
- Working directory: /app
- All output files must be written to /app

### Files to Produce

1. `/app/sshd_config_bastion` — The OpenSSH server configuration file for the bastion host with these requirements:
   - Disable password authentication (`PasswordAuthentication no`)
   - Disable root login (`PermitRootLogin no`)
   - Enable public key authentication (`PubkeyAuthentication yes`)
   - Disable X11 forwarding (`X11Forwarding no`)
   - Allow agent forwarding (`AllowAgentForwarding yes`)
   - Set `MaxAuthTries` to 3
   - Set `LoginGraceTime` to 30
   - Set `ClientAliveInterval` to 300
   - Set `ClientAliveCountMax` to 2
   - Use port 22
   - Enable logging: `SyslogFacility AUTH` and `LogLevel VERBOSE`

2. `/app/sshd_config_internal` — The OpenSSH server configuration file for internal servers with these requirements:
   - Disable password authentication (`PasswordAuthentication no`)
   - Disable root login (`PermitRootLogin no`)
   - Enable public key authentication (`PubkeyAuthentication yes`)
   - Disable agent forwarding (`AllowAgentForwarding no`)
   - Disable X11 forwarding (`X11Forwarding no`)
   - Set `MaxAuthTries` to 3
   - Use port 22
   - Add a restriction so only connections from the bastion host subnet `10.0.1.0/24` are accepted, using `AllowUsers *@10.0.1.*`

3. `/app/ssh_client_config` — An SSH client config file (`~/.ssh/config` format) defining:
   - A host entry named `bastion` with:
     - `HostName 10.0.1.10`
     - `User admin`
     - `IdentityFile ~/.ssh/bastion_key`
     - `ForwardAgent yes`
   - A host entry named `internal-*` with:
     - `ProxyJump bastion`
     - `User admin`
     - `IdentityFile ~/.ssh/internal_key`
   - A host entry named `internal-web` with:
     - `HostName 10.0.2.11`
   - A host entry named `internal-db` with:
     - `HostName 10.0.2.12`

4. `/app/firewall_rules.sh` — A bash script that outputs iptables rules to stdout. The script must:
   - Begin with `#!/bin/bash`
   - Be executable
   - Print iptables commands (one per line) that enforce:
     - Allow SSH (port 22) inbound to the bastion host from any source (`0.0.0.0/0`)
     - Allow SSH (port 22) from the bastion subnet `10.0.1.0/24` to the internal subnet `10.0.2.0/24`
     - Drop all other SSH (port 22) traffic to the internal subnet `10.0.2.0/24`
   - Each printed line must be a valid `iptables` command

5. `/app/fail2ban_sshd.conf` — A fail2ban jail configuration for SSH with:
   - Section header `[sshd]`
   - `enabled = true`
   - `port = ssh`
   - `filter = sshd`
   - `maxretry = 3`
   - `bantime = 3600`
   - `findtime = 600`
   - `logpath = /var/log/auth.log`

6. `/app/setup.sh` — A master setup script that:
   - Begins with `#!/bin/bash`
   - Be executable
   - Generates an ED25519 SSH key pair at `/app/bastion_key` and `/app/bastion_key.pub` (no passphrase, overwrite if exists)
   - Generates an ED25519 SSH key pair at `/app/internal_key` and `/app/internal_key.pub` (no passphrase, overwrite if exists)
   - Prints `Setup complete` as its last line of stdout upon successful execution

### Output Verification

After running `bash /app/setup.sh`, the following files must exist:
- `/app/bastion_key` (private key, permissions 600)
- `/app/bastion_key.pub` (public key)
- `/app/internal_key` (private key, permissions 600)
- `/app/internal_key.pub` (public key)

All six configuration/script files listed above must exist and contain the specified directives.
