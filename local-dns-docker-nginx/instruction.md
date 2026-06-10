## Local DNS Server Setup with Dockerized Web App

Configure a BIND9 local DNS server on the host and deploy a Dockerized Nginx web application that resolves via the custom domain `app.dev.local`.

### Technical Requirements

- **DNS Server:** BIND9, installed and running as a system service
- **Web Server:** Nginx, running inside a Docker container
- **Docker:** Use Docker with a custom bridge network

### DNS Configuration

1. Configure BIND9 as an authoritative DNS server for the zone `dev.local`.
2. Create a forward lookup zone file for `dev.local` with the following records:
   - An SOA record for `dev.local`
   - An NS record pointing to `ns.dev.local`
   - An A record for `ns.dev.local` resolving to `127.0.0.1`
   - An A record for `app.dev.local` resolving to `172.20.0.10`
3. BIND9 must listen on `127.0.0.1` (port 53).
4. The system's DNS resolver (`/etc/resolv.conf`) must be configured to use `127.0.0.1` as the nameserver so that local DNS queries go through BIND9.

### Docker Configuration

1. Create a custom Docker bridge network named `dev-network` with subnet `172.20.0.0/16`.
2. Run an Nginx container with the following specifications:
   - Container name: `dev-app`
   - Attached to the `dev-network` network
   - Static IP address: `172.20.0.10`
   - Port mapping: host port `80` mapped to container port `80`
3. The Nginx container must serve a custom `index.html` at its web root containing exactly the following content:
   ```
   <h1>Welcome to app.dev.local</h1>
   ```

### Verification Criteria

- `dig @127.0.0.1 app.dev.local` must return an A record with address `172.20.0.10`.
- `curl http://app.dev.local` must return a response containing `<h1>Welcome to app.dev.local</h1>`.
- The Docker container `dev-app` must be running with IP `172.20.0.10` on the `dev-network` network.
- The BIND9 service (`named`) must be active and running.
