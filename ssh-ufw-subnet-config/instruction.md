## SSH Key Authentication & Firewall Configuration

Configure secure SSH key-based authentication and UFW firewall rules to restrict SSH access to a specific subnet on an Ubuntu server.

**Technical Requirements:**
- Target system: Ubuntu server with SSH and UFW installed
- Configuration files: `/etc/ssh/sshd_config`, UFW rules
- Input: `/app/input.json` - Server network configuration
- Output: `/app/output.json` - Configuration changes summary

**Input Format (`/app/input.json`):**
```json
{
  "server_subnet": "192.168.1.0/24",
  "ssh_port": 22,
  "allowed_subnet": "192.168.1.0/24"
}
```

**Task Requirements:**

1. **SSH Configuration** (`/etc/ssh/sshd_config`):
   - Set `PasswordAuthentication no`
   - Set `PermitRootLogin no`
   - Set `PubkeyAuthentication yes`

2. **UFW Firewall Rules**:
   - Allow SSH (port from input) only from the specified subnet
   - Enable UFW firewall
   - Deny all other incoming SSH connections

3. **SSH Key Setup**:
   - Generate ED25519 SSH key pair (client-side)
   - Deploy public key to server's authorized_keys

**Output Format (`/app/output.json`):**
```json
{
  "ssh_config_changes": {
    "PasswordAuthentication": "no",
    "PermitRootLogin": "no",
    "PubkeyAuthentication": "yes"
  },
  "firewall_rules": [
    {
      "action": "allow",
      "port": 22,
      "from": "192.168.1.0/24",
      "protocol": "tcp"
    }
  ],
  "firewall_status": "active",
  "ssh_key_deployed": true,
  "ssh_key_type": "ed25519"
}
```

**Verification Criteria:**
- SSH configuration file contains all required security settings
- UFW rules restrict SSH access to specified subnet only
- SSH key pair generated and public key deployed
- Output JSON accurately reflects all configuration changes
