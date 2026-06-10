## Task: Configure SSH Key-based Authentication with Port Knocking

Secure SSH access by implementing key-based authentication and a port-knocking mechanism on an Ubuntu system.

### Technical Requirements

- Operating System: Ubuntu Linux
- Services: OpenSSH server, knockd (port-knocking daemon)
- Firewall: iptables
- SSH Key: RSA 4096-bit
- Configuration files must be created at:
  - `/app/sshd_config` - SSH daemon configuration
  - `/app/knockd.conf` - Port knocking configuration
  - `/app/iptables_rules.sh` - Firewall rules script
  - `/app/deployment_summary.json` - Deployment documentation

### Implementation Requirements

1. **SSH Configuration** (`/app/sshd_config`):
   - Disable password authentication (`PasswordAuthentication no`)
   - Enable public key authentication (`PubkeyAuthentication yes`)
   - Disable root login (`PermitRootLogin no`)
   - Set SSH port to 22

2. **Port Knocking Configuration** (`/app/knockd.conf`):
   - Define a knock sequence using exactly 3 ports
   - Sequence must use TCP protocol
   - Configure `openSSH` sequence to temporarily open port 22
   - Configure `closeSSH` sequence to close port 22
   - Set timeout of 10 seconds for the SSH port to remain open

3. **Firewall Rules** (`/app/iptables_rules.sh`):
   - Create a bash script with iptables rules
   - Default policy: DROP all incoming connections
   - Allow established connections
   - SSH port (22) must be closed by default
   - Include rules that work with knockd

4. **Deployment Documentation** (`/app/deployment_summary.json`):
   - JSON format with the following structure:
     ```json
     {
       "ssh_key_type": "RSA",
       "ssh_key_bits": 4096,
       "ssh_port": 22,
       "knock_sequence": [port1, port2, port3],
       "knock_protocol": "tcp",
       "ssh_timeout_seconds": 10,
       "authentication_method": "key-based",
       "password_auth_enabled": false
     }
     ```

### Output Requirements

All configuration files must be valid and syntactically correct:
- `sshd_config` must follow OpenSSH configuration syntax
- `knockd.conf` must follow knockd configuration format
- `iptables_rules.sh` must be an executable bash script with proper shebang
- `deployment_summary.json` must be valid JSON

### Edge Cases

- Ensure knock sequence ports are in valid range (1024-65535, avoiding well-known ports)
- All three knock ports must be different
- Configuration must prevent lockout scenarios (SSH accessible after proper knock sequence)
