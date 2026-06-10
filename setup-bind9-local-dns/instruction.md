## Local DNS Server Setup and Multi-Domain Resolution

Configure a local BIND9 DNS server that resolves multiple custom development domains to local IP addresses, supports reverse lookups, forwards external queries, and logs DNS activity.

### Technical Requirements

- **Platform:** Ubuntu/Debian-based system
- **DNS Software:** BIND9
- **Working Directory:** /app

### Domain Configuration

Set up forward zones for the following three domains, all authoritative on this server:

| Domain | A Record(s) | Additional Records |
|---|---|---|
| `dev.local` | `dev.local` → `127.0.0.1` | `www.dev.local` → `127.0.0.1`, `db.dev.local` → `127.0.0.2` |
| `app.local` | `app.local` → `127.0.0.1` | `www.app.local` → `127.0.0.1`, `staging.app.local` → `127.0.0.3` |
| `api.local` | `api.local` → `127.0.0.1` | `v1.api.local` → `127.0.0.1`, `v2.api.local` → `127.0.0.4` |

All zones must use:
- SOA record with `ns1.<domain>` as the primary nameserver and `admin.<domain>` as the contact email
- An NS record pointing to `ns1.<domain>`
- An A record for `ns1.<domain>` → `127.0.0.1`
- TTL of `604800` for the zone default

### Reverse DNS

Configure a reverse lookup zone for `127.in-addr.arpa` so that:
- `127.0.0.1` resolves (PTR) to `dev.local.`
- `127.0.0.2` resolves (PTR) to `db.dev.local.`
- `127.0.0.3` resolves (PTR) to `staging.app.local.`
- `127.0.0.4` resolves (PTR) to `v2.api.local.`

### Forwarding

Configure BIND9 to forward queries for non-local domains to the following public DNS servers:
- `8.8.8.8`
- `8.8.4.4`

Use `forward only;` semantics inside a `forwarders` block in the BIND9 options.

### Logging

Enable BIND9 query logging:
- Log channel name: `query_log`
- Log to file: `/var/log/named/query.log`
- Severity: `info`
- Log category: `queries`

Ensure the directory `/var/log/named/` exists with appropriate permissions for the `bind` user.

### System Resolver

Update `/etc/resolv.conf` so that `127.0.0.1` is listed as the first nameserver.

### Verification Script

Create a script at `/app/verify_dns.sh` (executable, bash) that performs the following checks using `dig @127.0.0.1` and writes results to `/app/dns_test_results.txt`:

The output file must contain exactly the following lines (one per check, in this order):

```
dev.local=127.0.0.1
www.dev.local=127.0.0.1
db.dev.local=127.0.0.2
app.local=127.0.0.1
www.app.local=127.0.0.1
staging.app.local=127.0.0.3
api.local=127.0.0.1
v1.api.local=127.0.0.1
v2.api.local=127.0.0.4
reverse_127.0.0.1=dev.local.
reverse_127.0.0.2=db.dev.local.
reverse_127.0.0.3=staging.app.local.
reverse_127.0.0.4=v2.api.local.
```

Each line is `<query>=<result>` where `<result>` is the resolved address (for A records) or hostname (for PTR records) as returned by `dig +short`.

### Service State

After all configuration is complete:
- BIND9 service (`named`) must be running
- `named-checkconf` must exit with code 0
- `named-checkzone` must pass for all four zones (three forward + one reverse)
