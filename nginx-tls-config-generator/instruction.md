# Securing a Web Server with TLS Configuration

Write a Python 3 script (`/app/solution.py`) that generates a complete set of Nginx TLS/HTTPS configuration files and supporting shell scripts for securing a web server. The script reads a domain configuration from `/app/input.json` and produces all artifacts needed to enable HTTPS with hardened TLS settings.

## Input

`/app/input.json` — a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `domain` | string | Primary domain name (e.g., `"example.com"`) |
| `additional_domains` | array of strings | Optional SANs (Subject Alternative Names), may be empty |
| `webroot` | string | Document root path (e.g., `"/var/www/html"`) |
| `email` | string | Contact email for certificate registration |
| `nginx_conf_dir` | string | Nginx config directory (e.g., `"/etc/nginx"`) |
| `cert_dir` | string | Directory for certificate files (e.g., `"/etc/letsencrypt/live/example.com"`) |
| `enable_ocsp_stapling` | boolean | Whether to enable OCSP stapling |
| `hsts_max_age` | integer | HSTS max-age in seconds (0 means do not include HSTS header) |

Example:
```json
{
  "domain": "example.com",
  "additional_domains": ["www.example.com"],
  "webroot": "/var/www/html",
  "email": "admin@example.com",
  "nginx_conf_dir": "/etc/nginx",
  "cert_dir": "/etc/letsencrypt/live/example.com",
  "enable_ocsp_stapling": true,
  "hsts_max_age": 31536000
}
```

## Output

The script must produce the following files:

### 1. `/app/output/nginx_https.conf`

A valid Nginx server block configuration file that includes:

- A server block listening on port 80 that redirects ALL HTTP requests to HTTPS (301 redirect) for the primary domain and all additional domains.
- A server block listening on port 443 with `ssl` enabled, with `server_name` set to the primary domain and all additional domains.
- `ssl_certificate` pointing to `{cert_dir}/fullchain.pem`.
- `ssl_certificate_key` pointing to `{cert_dir}/privkey.pem`.
- `ssl_protocols` set to `TLSv1.2 TLSv1.3` only (no older protocols).
- `ssl_ciphers` set to a modern cipher string that excludes NULL, MD5, RC4, DES, and 3DES ciphers.
- `ssl_prefer_server_ciphers on;`
- A `location /.well-known/acme-challenge/` block pointing to the webroot for certificate validation.
- If `enable_ocsp_stapling` is true: `ssl_stapling on;`, `ssl_stapling_verify on;`, and `ssl_trusted_certificate` pointing to `{cert_dir}/chain.pem`.
- If `hsts_max_age` > 0: an `add_header Strict-Transport-Security` directive with the specified max-age and `includeSubDomains`.
- A `root` directive pointing to the webroot.

### 2. `/app/output/ssl_params.conf`

A separate Nginx snippet file containing:

- `ssl_session_timeout` set to a value between 1h and 24h (inclusive).
- `ssl_session_cache` using `shared:SSL:` with a size of at least 10m.
- `ssl_session_tickets off;`
- `ssl_buffer_size` set to a value (e.g., `4k` or `8k`).

### 3. `/app/output/certbot_command.sh`

A shell script (with `#!/bin/bash` shebang) containing the certbot command to obtain a certificate. Requirements:

- Uses `certbot certonly` with `--webroot` mode.
- Includes `--webroot-path` set to the webroot value.
- Includes `-d` flags for the primary domain and each additional domain.
- Includes `--email` with the provided email.
- Includes `--agree-tos` and `--non-interactive` flags.

### 4. `/app/output/renewal_cron.txt`

A single-line cron entry that:

- Runs `certbot renew` at least once per day.
- Includes a post-hook or follow-up command to reload Nginx (must contain `nginx` and `reload` in the line).

### 5. `/app/output/summary.json`

A JSON file summarizing the configuration:

```json
{
  "domain": "<primary domain>",
  "all_domains": ["<primary>", "<additional1>", ...],
  "https_port": 443,
  "http_port": 80,
  "http_redirect": true,
  "tls_protocols": ["TLSv1.2", "TLSv1.3"],
  "ocsp_stapling": <boolean>,
  "hsts_enabled": <boolean>,
  "hsts_max_age": <integer>,
  "cert_path": "<cert_dir>/fullchain.pem",
  "key_path": "<cert_dir>/privkey.pem",
  "renewal_method": "cron"
}
```

All fields must match the input configuration. `all_domains` must list the primary domain first, followed by additional domains in order. `hsts_enabled` is `true` if and only if `hsts_max_age` > 0.

## Constraints

- The script must create the `/app/output/` directory if it does not exist.
- All generated config files must use Unix line endings (`\n`).
- The Nginx config files must be syntactically reasonable (properly matched braces, semicolons after directives).
- `summary.json` must be valid JSON and parseable by `json.loads()`.
- If `additional_domains` is empty, the configuration should work with only the primary domain.
