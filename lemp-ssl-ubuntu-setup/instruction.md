## LEMP Stack with SSL Configuration on Ubuntu

Set up a fully operational LEMP stack (Nginx, MySQL, PHP-FPM) on Ubuntu and prepare Nginx configuration for HTTPS with self-signed SSL certificates. Produce working configuration files, a PHP test page, and a setup script.

### Technical Requirements

- OS: Ubuntu 22.04
- Stack: Nginx, MySQL (or MariaDB), PHP-FPM (PHP 8.x)
- All configuration and output files go under `/app/`

### Deliverables

1. **Setup script:** `/app/setup.sh`
   - A bash script that, when run as root, performs the following in order:
     - Updates apt package lists
     - Installs Nginx, MySQL server (or MariaDB server), PHP-FPM, and these PHP extensions: `php-mysql`, `php-curl`, `php-xml`, `php-mbstring`
     - Starts and enables the Nginx, MySQL (or MariaDB), and PHP-FPM services
     - Generates a self-signed SSL certificate and key at `/etc/ssl/certs/selfsigned.crt` and `/etc/ssl/private/selfsigned.key` (valid for 365 days, RSA 2048-bit, subject CN=localhost)
     - Copies the Nginx config file to `/etc/nginx/sites-available/default` and creates a symlink at `/etc/nginx/sites-enabled/default` if not already present
     - Copies the PHP test page to `/var/www/html/info.php`
     - Tests Nginx configuration (`nginx -t`) and reloads Nginx
   - The script must be executable and start with `#!/bin/bash`
   - The script must run non-interactively (no user prompts; use `DEBIAN_FRONTEND=noninteractive` and appropriate flags for mysql-server)

2. **Nginx configuration file:** `/app/nginx.conf`
   - Defines two `server` blocks:
     - **HTTP block:** listens on port `80`, returns a `301` redirect to `https://$host$request_uri` for all requests
     - **HTTPS block:** listens on port `443 ssl`, with `root /var/www/html` and `index index.php index.html`
       - References SSL certificate at `/etc/ssl/certs/selfsigned.crt` and key at `/etc/ssl/private/selfsigned.key`
       - Contains a `location ~ \.php$` block that passes requests to PHP-FPM via the Unix socket (e.g., `unix:/run/php/php8.1-fpm.sock` — use the version-appropriate socket path)
       - Includes `fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;`
       - Contains a `location /` block with `try_files $uri $uri/ =404;`

3. **PHP test page:** `/app/info.php`
   - A PHP file that calls `phpinfo();` and outputs the full PHP info page
   - Must start with `<?php` tag

4. **MySQL secure setup script:** `/app/secure_mysql.sh`
   - A bash script (executable, starting with `#!/bin/bash`) that:
     - Removes anonymous MySQL users
     - Disables remote root login
     - Removes the `test` database if it exists
     - Flushes privileges
   - Uses `mysql -u root` to execute SQL statements

### Constraints

- All four files must exist and be non-empty.
- `setup.sh` and `secure_mysql.sh` must have executable permission.
- The Nginx config must pass syntax validation (`nginx -t`) after being placed in the appropriate location and with the SSL certs generated.
- Do NOT use Certbot or Let's Encrypt (use self-signed certificates for testability).
