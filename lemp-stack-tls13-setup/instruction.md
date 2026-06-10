## Task: Configure a LEMP Stack with TLS 1.3 Support

Set up a production-ready LEMP stack (Linux, Nginx, MySQL 8, PHP-FPM) on Ubuntu 22.04 with TLS 1.3 enabled and create verification outputs to prove the configuration is correct.

### Technical Requirements

- **Platform:** Ubuntu 22.04
- **Web Server:** Nginx (latest stable)
- **Database:** MySQL 8.0
- **PHP:** PHP-FPM 8.1 or higher
- **TLS:** TLS 1.3 minimum protocol version
- **Output:** Configuration verification file at `/app/verification.json`

### Implementation Requirements

1. **Nginx with TLS 1.3:**
   - Install Nginx
   - Generate a self-signed SSL certificate (valid for 365 days, 2048-bit RSA key)
   - Configure Nginx to serve HTTPS on port 443 with TLS 1.3 as minimum protocol
   - Disable TLS 1.0, 1.1, and 1.2
   - Configure server to listen on default server name

2. **MySQL 8.0:**
   - Install MySQL 8.0
   - Run security configuration (remove test database, disable remote root login)
   - Create a test database named `testdb`
   - Create a user `testuser` with password `testpass123` with full privileges on `testdb`

3. **PHP-FPM:**
   - Install PHP-FPM (version 8.1+)
   - Install required extensions: `php-mysql`, `php-curl`, `php-json`, `php-mbstring`
   - Configure Nginx to process `.php` files via PHP-FPM socket

4. **Verification Requirements:**
   - Create `/var/www/html/info.php` that calls `phpinfo()`
   - Create `/var/www/html/dbtest.php` that connects to MySQL using the test credentials and outputs "Database connection successful" on success
   - Create `/app/verification.json` with the following structure:

```json
{
  "nginx_version": "<version string>",
  "nginx_running": true,
  "tls_1_3_enabled": true,
  "ssl_certificate_exists": true,
  "mysql_version": "<version string>",
  "mysql_running": true,
  "testdb_exists": true,
  "testuser_exists": true,
  "php_version": "<version string>",
  "php_fpm_running": true,
  "php_extensions": ["mysql", "curl", "json", "mbstring"],
  "info_php_exists": true,
  "dbtest_php_exists": true,
  "firewall_enabled": true
}
```

5. **Firewall Configuration:**
   - Enable UFW firewall
   - Allow SSH (port 22), HTTP (port 80), and HTTPS (port 443)

6. **Performance Optimization:**
   - Configure Nginx worker processes to auto
   - Set worker connections to at least 1024
   - Enable gzip compression in Nginx

### Output Specifications

- **Primary Output:** `/app/verification.json` containing all verification data as specified above
- **Web Files:** `/var/www/html/info.php` and `/var/www/html/dbtest.php` must be accessible
- **Services:** Nginx, MySQL, and PHP-FPM must be running and enabled to start on boot

### Validation Criteria

The setup is considered complete when:
- All services (Nginx, MySQL, PHP-FPM) are running
- HTTPS is accessible with TLS 1.3 minimum protocol
- PHP files are processed correctly via PHP-FPM
- Database connectivity works from PHP
- `/app/verification.json` exists with all required fields set to correct values
- Firewall is active with correct rules
