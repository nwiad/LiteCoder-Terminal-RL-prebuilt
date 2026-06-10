## Deploy LEMP Stack with Enhanced Security

Create a Bash deployment script that installs and configures a production-ready LEMP stack (Nginx, MariaDB, PHP-FPM) with SSL/TLS, fail2ban, and firewall hardening on an Ubuntu 22.04 system.

### Technical Requirements

- Language: Bash
- Target OS: Ubuntu 22.04
- Main script: `/app/deploy.sh` (must be executable, `chmod +x`)
- Verification script: `/app/verify.sh` (must be executable, `chmod +x`)
- Report output: `/app/deployment_report.txt`
- The deployment script must be idempotent (safe to run multiple times without errors)
- All scripts must use `#!/bin/bash` shebang

### Deployment Script (`/app/deploy.sh`)

The script must perform the following steps in order:

1. **System Update**: Update package lists and upgrade installed packages.

2. **Nginx Installation & Configuration**:
   - Install Nginx.
   - Create a server block configuration file at `/etc/nginx/sites-available/webapp`.
   - The server block must listen on ports 80 and 443.
   - Configure SSL directives pointing to certificate files at `/etc/ssl/certs/webapp.crt` and `/etc/ssl/private/webapp.key`.
   - Generate a self-signed SSL certificate (valid for 365 days, CN=localhost) at the paths above.
   - Enable the site by creating a symlink in `/etc/nginx/sites-enabled/`.
   - The Nginx config must include `fastcgi_pass` directive pointing to the PHP-FPM socket.
   - Set `server_name` to `localhost`.
   - Set document root to `/var/www/webapp`.

3. **MariaDB Installation & Hardening**:
   - Install MariaDB server.
   - Set the MariaDB root password to `SecureR00tP@ss`.
   - Remove anonymous users.
   - Remove the test database if it exists.
   - Disallow remote root login.
   - Create a database named `webapp_db`.
   - Create a database user `webapp_user` with password `W3bAppUs3r!` and grant all privileges on `webapp_db`.

4. **PHP-FPM Installation & Configuration**:
   - Install PHP-FPM and the `php-mysql` extension.
   - Create a PHP info test page at `/var/www/webapp/info.php` containing exactly `<?php phpinfo(); ?>`.
   - Create an index file at `/var/www/webapp/index.php` that contains a PHP script which outputs exactly the string `LEMP Stack Operational` (as plain text).
   - Set proper ownership of `/var/www/webapp` to `www-data:www-data`.

5. **UFW Firewall Configuration**:
   - Install and enable UFW.
   - Default policy: deny incoming, allow outgoing.
   - Allow the following ports: 22 (SSH), 80 (HTTP), 443 (HTTPS).
   - No other incoming ports should be allowed.

6. **Fail2ban Installation & Configuration**:
   - Install fail2ban.
   - Create a local jail configuration at `/etc/fail2ban/jail.local`.
   - The jail config must define at minimum these two jails:
     - `[sshd]` — enabled, maxretry = 3, bantime = 3600
     - `[nginx-http-auth]` — enabled, maxretry = 3, bantime = 3600
   - Enable and start the fail2ban service.

7. **Service Management**:
   - Ensure nginx, mariadb (or mysql), php-fpm, and fail2ban services are enabled to start on boot.
   - Restart all services at the end of the script.

8. **Generate Deployment Report**:
   - At the end of execution, write a report to `/app/deployment_report.txt`.
   - The report must contain the following lines (one per line, in any order):
     ```
     nginx=installed
     mariadb=installed
     php-fpm=installed
     ufw=active
     fail2ban=installed
     ssl=configured
     firewall_ports=22,80,443
     ```

### Verification Script (`/app/verify.sh`)

Create a script that checks the deployment and prints results to stdout. It must check and print one line per check in the format `CHECK_NAME=PASS` or `CHECK_NAME=FAIL`:

- `NGINX_INSTALLED` — nginx binary exists
- `MARIADB_INSTALLED` — mariadb binary exists
- `PHP_FPM_INSTALLED` — php-fpm binary or service exists
- `SSL_CERT_EXISTS` — `/etc/ssl/certs/webapp.crt` exists
- `SSL_KEY_EXISTS` — `/etc/ssl/private/webapp.key` exists
- `NGINX_CONFIG_EXISTS` — `/etc/nginx/sites-available/webapp` exists
- `SITE_ENABLED` — symlink exists in `/etc/nginx/sites-enabled/` for webapp
- `DOCUMENT_ROOT_EXISTS` — `/var/www/webapp` directory exists
- `INDEX_PHP_EXISTS` — `/var/www/webapp/index.php` exists
- `INFO_PHP_EXISTS` — `/var/www/webapp/info.php` exists
- `FAIL2BAN_JAIL_EXISTS` — `/etc/fail2ban/jail.local` exists
- `UFW_ENABLED` — UFW status shows active
- `REPORT_EXISTS` — `/app/deployment_report.txt` exists
