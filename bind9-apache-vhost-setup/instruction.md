## DNS Configuration & Web Hosting

Set up a BIND9 DNS server and Apache2 web server with virtual hosting for three domains on a Linux server, then create a health check script to verify all services.

### Technical Requirements

- OS: Linux (Debian/Ubuntu-based)
- DNS Server: BIND9
- Web Server: Apache2
- Health check script: Bash

### 1. BIND9 DNS Server

Install and configure BIND9 with the following:

- Use `127.0.0.1` as the DNS server IP address.
- Forward lookup zone for `company.com` in zone file `/etc/bind/db.company.com`.
- Reverse lookup zone for `127.in-addr.arpa` in zone file `/etc/bind/db.127`.
- The zone configuration must be declared in `/etc/bind/named.conf.local`.

DNS records to create in the forward zone (`db.company.com`):

| Record Type | Name                  | Value       |
|-------------|-----------------------|-------------|
| SOA         | company.com           | ns1.company.com. admin.company.com. |
| NS          | company.com           | ns1.company.com. |
| A           | ns1.company.com       | 127.0.0.1   |
| A           | company.com           | 127.0.0.1   |
| A           | portal.company.com    | 127.0.0.1   |
| A           | api.company.com       | 127.0.0.1   |

The reverse zone (`db.127`) must contain a PTR record mapping `1.0.0.127.in-addr.arpa` to `ns1.company.com.`.

BIND9 must be configured to listen on `127.0.0.1` port `53` and allow queries from `localhost` and `127.0.0.1`.

Enable query logging by configuring a `logging` section in `/etc/bind/named.conf.options` or `/etc/bind/named.conf.local` that logs queries to `/var/log/named/query.log`.

### 2. Apache2 Virtual Hosts

Install and enable Apache2 with three virtual host configurations:

**a) Main site — `company.com`**
- Config file: `/etc/apache2/sites-available/company.com.conf`
- `ServerName`: `company.com`
- `DocumentRoot`: `/var/www/company.com`
- Index page: `/var/www/company.com/index.html`
- The index page must contain the text: `Welcome to Company`

**b) Customer portal — `portal.company.com`**
- Config file: `/etc/apache2/sites-available/portal.company.com.conf`
- `ServerName`: `portal.company.com`
- `DocumentRoot`: `/var/www/portal.company.com`
- Index page: `/var/www/portal.company.com/index.html`
- The index page must contain the text: `Customer Portal`

**c) API gateway — `api.company.com`**
- Config file: `/etc/apache2/sites-available/api.company.com.conf`
- `ServerName`: `api.company.com`
- `DocumentRoot`: `/var/www/api.company.com`
- Index page: `/var/www/api.company.com/index.html`
- The index page must contain the text: `API Gateway`

All three virtual hosts must listen on port `80`. Each site must be enabled (e.g., via `a2ensite`). Apache access logs for each virtual host should be written to `/var/log/apache2/<domain>-access.log` and error logs to `/var/log/apache2/<domain>-error.log`.

### 3. Firewall

Configure `iptables` to allow inbound traffic on:
- TCP and UDP port `53` (DNS)
- TCP port `80` (HTTP)

### 4. Health Check Script

Create a Bash script at `/app/health_check.sh` that verifies all services are running. The script must:

- Check that BIND9 (named) service is active.
- Check that Apache2 service is active.
- Use `dig` against `127.0.0.1` to verify DNS resolution for `company.com`, `portal.company.com`, and `api.company.com` (each must resolve to `127.0.0.1`).
- Use `curl` with a `Host` header to verify each web service responds with HTTP 200 on `http://127.0.0.1/` for each domain.
- Print results to stdout, one line per check, in the format: `<check_name>: OK` or `<check_name>: FAIL`
- The check names must be exactly: `bind9_running`, `apache2_running`, `dns_company.com`, `dns_portal.company.com`, `dns_api.company.com`, `http_company.com`, `http_portal.company.com`, `http_api.company.com`
- Exit with code `0` if all checks pass, or `1` if any check fails.
- The script must be executable (`chmod +x`).
