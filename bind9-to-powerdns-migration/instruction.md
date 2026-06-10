## DNS Migration: BIND9 to PowerDNS

Migrate DNS zone data from BIND9 zone file format to PowerDNS-compatible configuration. Given a BIND9 zone file at `/app/bind9_zones.txt`, parse all DNS records and produce the outputs described below.

### Technical Requirements

- Language: Python 3
- Input: `/app/bind9_zones.txt` (BIND9 zone file)
- Output:
  - `/app/powerdns_records.json` — All parsed DNS records in PowerDNS JSON format
  - `/app/migration_report.txt` — Migration summary report

### Input Format

The input file `/app/bind9_zones.txt` contains one or more BIND9 zone blocks. Each zone block starts with a `$ORIGIN` directive specifying the zone name, followed by a `$TTL` directive for the default TTL, and then individual DNS resource records. Records follow standard BIND zone file syntax:

```
$ORIGIN corp.example.com.
$TTL 3600
@       IN  SOA   ns1.corp.example.com. admin.corp.example.com. (
                    2024010101  ; Serial
                    3600        ; Refresh
                    900         ; Retry
                    604800      ; Expire
                    86400 )     ; Minimum TTL
@       IN  NS    ns1.corp.example.com.
@       IN  NS    ns2.corp.example.com.
ns1     IN  A     192.168.1.1
ns2     IN  A     192.168.1.2
mail    IN  A     192.168.1.10
@       IN  MX    10 mail.corp.example.com.
www     IN  CNAME corp.example.com.
app     IN  A     192.168.1.20
db      IN  A     192.168.1.30
```

Multiple zones may appear in the same file, each starting with its own `$ORIGIN` directive. A record name of `@` refers to the zone origin itself. Record names without a trailing dot are relative to the current `$ORIGIN`.

### Output 1: `/app/powerdns_records.json`

A JSON file containing an array of zone objects. Each zone object has:

- `zone`: the zone name (string, with trailing dot, e.g. `"corp.example.com."`)
- `default_ttl`: the default TTL from the `$TTL` directive (integer)
- `records`: an array of record objects, each with:
  - `name`: fully qualified domain name with trailing dot (e.g. `"ns1.corp.example.com."`)
  - `type`: record type string (e.g. `"A"`, `"MX"`, `"CNAME"`, `"NS"`, `"SOA"`)
  - `ttl`: integer TTL value (use the zone's default TTL if not explicitly specified on the record)
  - `content`: the record data as a string
    - For SOA records: `"ns1.corp.example.com. admin.corp.example.com. 2024010101 3600 900 604800 86400"`
    - For MX records: `"10 mail.corp.example.com."`
    - For CNAME/NS records: the target FQDN with trailing dot
    - For A records: the IP address
    - For AAAA records: the IPv6 address

Records must appear in the same order as they appear in the input file. The `@` symbol must be expanded to the zone's origin name (with trailing dot). Relative record names (without trailing dot) must be expanded to FQDNs by appending the zone origin. Content values that are domain names must also be fully qualified with a trailing dot.

### Output 2: `/app/migration_report.txt`

A plain text report with the following exact format (one line per item, no extra blank lines between items):

```
Migration Report
Zones migrated: <N>
Total records: <M>
Zone: <zone_name>
  SOA: <count>
  NS: <count>
  A: <count>
  AAAA: <count>
  CNAME: <count>
  MX: <count>
```

Where `<N>` is the number of zones, `<M>` is the total number of records across all zones. For each zone, list the per-type record counts. Only include record types that have count > 0 for that zone. The per-zone record type lines must be indented with exactly two spaces. If there are multiple zones, repeat the `Zone: ...` block for each zone in the order they appear in the input.

### Edge Cases

- If a record specifies an explicit TTL (a number before `IN`), use that TTL instead of the zone default.
- Handle both `@` and bare hostnames correctly by expanding to FQDNs.
- Domain names in content fields that are already fully qualified (end with `.`) must be kept as-is.
- The parser must handle SOA records that span multiple lines (enclosed in parentheses).
- Ignore comment lines (lines starting with `;`) and inline comments (text after `;`).
