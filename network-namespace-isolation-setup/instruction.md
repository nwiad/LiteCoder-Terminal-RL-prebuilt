## Network Isolation and Monitoring Setup

Create an isolated network environment with traffic monitoring capabilities using Linux network namespaces, veth pairs, and iptables. All scripts and output files should be placed under `/app/`.

### Requirements

1. **Setup Script (`/app/setup.sh`)**

   Write a Bash script that performs all of the following when executed:

   - Create two network namespaces: `app-ns` and `monitor-ns`.
   - Create a veth pair named `veth-app` and `veth-monitor`.
   - Move `veth-app` into `app-ns` and `veth-monitor` into `monitor-ns`.
   - Assign IP `10.0.1.1/24` to `veth-app` inside `app-ns`.
   - Assign IP `10.0.1.2/24` to `veth-monitor` inside `monitor-ns`.
   - Bring up the loopback and veth interfaces in both namespaces.
   - Configure iptables rules inside `app-ns`:
     - Default policy for the `FORWARD` chain: `DROP`.
     - Allow ICMP traffic (ping) between the two namespaces (on the `INPUT` and `OUTPUT` chains).
     - Add a `LOG` rule on the `INPUT` chain that logs incoming packets with the prefix `"APP-NS-IN: "`.
   - Configure NAT in `monitor-ns`: add a `MASQUERADE` rule on the `POSTROUTING` chain of the `nat` table for source subnet `10.0.1.0/24`.
   - The script must be idempotent — running it multiple times should not produce errors or duplicate resources.

2. **Traffic Capture (`/app/capture.sh`)**

   Write a Bash script that:
   - Runs `tcpdump` inside `monitor-ns` on interface `veth-monitor`.
   - Captures exactly 5 ICMP packets (use `-c 5`).
   - Writes the capture to `/app/capture.pcap`.
   - Before starting the capture, generates ICMP traffic by running `ping -c 5 10.0.1.2` from inside `app-ns` (in the background so tcpdump can capture it).

3. **Network Report (`/app/report.sh`)**

   Write a Bash script that inspects the current state of the environment and produces `/app/network_report.json` with the following JSON structure:

   ```json
   {
     "namespaces": ["app-ns", "monitor-ns"],
     "veth_pair": {
       "app_side": {
         "name": "veth-app",
         "namespace": "app-ns",
         "ip": "10.0.1.1/24"
       },
       "monitor_side": {
         "name": "veth-monitor",
         "namespace": "monitor-ns",
         "ip": "10.0.1.2/24"
       }
     },
     "iptables_rules": {
       "app_ns": {
         "forward_policy": "DROP",
         "icmp_allowed": true,
         "log_prefix": "APP-NS-IN: "
       },
       "monitor_ns": {
         "nat_masquerade": true
       }
     }
   }
   ```

   The values must be dynamically read from the live system state (e.g., `ip netns`, `ip addr`, `iptables` commands), not hardcoded.

4. **Cleanup Script (`/app/cleanup.sh`)**

   Write a Bash script that fully reverses the setup:
   - Deletes both network namespaces (`app-ns` and `monitor-ns`). Deleting the namespaces implicitly removes the veth pair and iptables rules within them.
   - Removes `/app/capture.pcap` if it exists.
   - The script must be idempotent — running it when the environment is already clean should not produce errors.

### Constraints

- All scripts must use `#!/bin/bash` and must be executable.
- All scripts must exit with code `0` on success.
- Do not install any packages beyond what is available in a standard Linux environment with `iproute2`, `iptables`, and `tcpdump` pre-installed.
