## DNS-over-TLS (DoT) Recursive Resolver with Unbound

Configure Unbound as a local DNS-over-TLS (DoT) caching resolver that encrypts all upstream DNS queries to public resolvers (Cloudflare and Quad9) while serving LAN clients on port 53.

### Technical Requirements

- **Platform:** Linux (Debian/Ubuntu-based), run all work inside the current environment.
- **Software:** Unbound DNS resolver with TLS support libraries.

### Tasks

1. **Install Unbound** and any required TLS libraries (e.g., `libunbound`, OpenSSL/GnuTLS dependencies). Ensure the `unbound` package is installed and functional.

2. **Back up the stock configuration** by copying the original `/etc/unbound/unbound.conf` to `/etc/unbound/unbound.conf.bak` before making any changes.

3. **Write the Unbound configuration** at `/etc/unbound/unbound.conf`. The configuration must include:

   - A `server:` section with at minimum:
     - `interface: 0.0.0.0` (listen on all IPv4 interfaces)
     - `port: 53`
     - `do-udp: yes`
     - `do-tcp: yes`
     - `tls-cert-bundle` pointing to the system CA certificate bundle (e.g., `/etc/ssl/certs/ca-certificates.crt`)
     - `access-control` allowing the `127.0.0.0/8` network and at least one private LAN range (e.g., `10.0.0.0/8`, `172.16.0.0/12`, or `192.168.0.0/16`) with the `allow` action
     - `hide-identity: yes`
     - `hide-version: yes`

   - A `forward-zone:` section with:
     - `name: "."` (forward all queries)
     - `forward-tls-upstream: yes`
     - At least two upstream forwarders configured for TLS:
       - **Cloudflare:** `forward-addr: 1.1.1.1@853#cloudflare-dns.com`
       - **Quad9:** `forward-addr: 9.9.9.9@853#dns.quad9.net`

4. **Configure firewall rules** using `iptables` (or `nftables`):
   - Allow inbound TCP and UDP traffic on port 53 from local/LAN sources.
   - Allow outbound TCP traffic on port 853 (TLS to upstream resolvers).
   - Save the rules so they persist across reboots. Write the saved rules to `/app/iptables-rules.txt` (output of `iptables-save` or equivalent).

5. **Start and enable the Unbound service** via systemd:
   - `unbound.service` must be in `active (running)` state.
   - `unbound.service` must be `enabled` (auto-start on boot).

6. **Verify DNS resolution** works by running:
   - `dig @127.0.0.1 example.com A` — must return a valid A record (NOERROR status).
   - Write the full dig output to `/app/dig-test-output.txt`.

7. **Verify TLS forwarding** by confirming that outbound DNS traffic uses port 853. Capture or log evidence and write it to `/app/tls-verification.txt`. This file must contain references to port `853` demonstrating that upstream queries are encrypted.

8. **Write a client configuration snippet** to `/app/client-dns-config.txt` that documents how a Linux desktop client should configure its DNS to point to this Unbound resolver. The file must contain a `nameserver` directive referencing `127.0.0.1` (for local use) or the server's LAN IP.

### Output Files Summary

| File | Description |
|---|---|
| `/etc/unbound/unbound.conf.bak` | Backup of original Unbound config |
| `/etc/unbound/unbound.conf` | Final Unbound DoT configuration |
| `/app/iptables-rules.txt` | Saved firewall rules |
| `/app/dig-test-output.txt` | Output of `dig @127.0.0.1 example.com A` |
| `/app/tls-verification.txt` | Evidence of TLS (port 853) usage |
| `/app/client-dns-config.txt` | Client-side DNS configuration snippet |
