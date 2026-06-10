Harden a freshly-installed Apache2 web server on an Ubuntu 22.04 LTS container so that it emits OWASP-recommended secure headers, blocks insecure HTTP methods, and hides server identity information. Apache2 is already installed and running on port 80.

## Requirements

1. **Apache2 must remain running and reachable.** After all changes, Apache2 must be active (running) and respond to HTTP requests on port 80. A GET request to `http://localhost/` must return HTTP status 200 or 403 (not 500 or connection refused).

2. **Enable required Apache modules.** Ensure the `headers` and `rewrite` modules are enabled.

3. **OWASP Secure Response Headers.** Every HTTP response from Apache2 on port 80 must include all of the following headers (case-insensitive header names):

   | Header | Required Value |
   |---|---|
   | X-Frame-Options | DENY |
   | X-Content-Type-Options | nosniff |
   | X-XSS-Protection | 0 |
   | Strict-Transport-Security | max-age=31536000; includeSubDomains |
   | Referrer-Policy | strict-origin-when-cross-origin |
   | Content-Security-Policy | default-src 'self' |

4. **Block insecure HTTP methods.** The server must reject requests using the TRACE and TRACK methods. A `curl -X TRACE http://localhost/` and `curl -X TRACK http://localhost/` must each return HTTP status 405 (Method Not Allowed) or 403 (Forbidden). The `TraceEnable` directive must be set to `off`.

5. **Allow standard HTTP methods.** Requests using GET, HEAD, and POST must still be served normally (not blocked).

6. **Hide server identity.** The Apache server signature and version must be suppressed:
   - `ServerTokens` must be set to `Prod`
   - `ServerSignature` must be set to `Off`
   - The `Server` response header must not reveal the Apache version number (e.g., it must not contain a string like `Apache/2.4.52`; showing just `Apache` is acceptable).

7. **Configuration validity.** The Apache configuration must pass a syntax check (`apachectl configtest` or `apache2ctl configtest` must succeed).

8. **Summary report.** Write a plain-text summary report to `/app/report.txt` that lists each security change made (one change per line). The file must exist and be non-empty.
