Install and configure a fully functional LEMP (Linux, Nginx, MariaDB, PHP-FPM) stack on this Ubuntu system, with SSL support and a configured virtual host.

## Technical Requirements

- OS: Ubuntu (current system)
- Web server: Nginx
- Database: MariaDB
- PHP: PHP-FPM with common extensions

## Tasks

### 1. System Packages & Nginx
- Update system package lists.
- Install Nginx and ensure it is running and enabled to start on boot.
- Nginx must listen on ports 80 and 443.

### 2. Firewall (UFW)
- Enable UFW if not already enabled.
- Allow incoming traffic on ports 22 (SSH), 80 (HTTP), and 443 (HTTPS).

### 3. MariaDB
- Install MariaDB server and ensure it is running and enabled on boot.
- Create a database named `lemp_test_db`.
- Create a MariaDB user `lemp_user` with password `lemp_pass` that has full privileges on `lemp_test_db`.

### 4. PHP-FPM
- Install PHP-FPM and the following PHP extensions: `php-mysql`, `php-curl`, `php-gd`, `php-mbstring`, `php-xml`, `php-zip`.
- Ensure the PHP-FPM service is running and enabled on boot.

### 5. Nginx PHP Configuration
- Configure Nginx to process `.php` files through PHP-FPM.
- Create a test PHP file at `/var/www/testsite/info.php` containing a call to `phpinfo()`.
- Requesting this file through Nginx must return valid PHP output (not the raw source code).

### 6. SSL Configuration
- Generate a self-signed SSL certificate and key:
  - Certificate: `/etc/ssl/certs/nginx-selfsigned.crt`
  - Key: `/etc/ssl/private/nginx-selfsigned.key`
- The certificate must be a valid x509 certificate (verifiable with `openssl x509 -in ... -noout`).

### 7. Virtual Host (Server Block)
- Create an Nginx server block configuration file at `/etc/nginx/sites-available/testsite`.
- This server block must:
  - Set `server_name` to `testsite.local`.
  - Set `root` to `/var/www/testsite`.
  - Listen on port 80 and port 443 with SSL using the self-signed certificate and key from step 6.
  - Include a `location ~ \.php$` block that passes requests to PHP-FPM.
- Enable the site by symlinking to `/etc/nginx/sites-enabled/testsite`.
- Nginx configuration must pass `nginx -t` validation.

### 8. Verification File
- Create the file `/var/www/testsite/index.php` with the following exact content:

```php
<?php
echo "LEMP Stack OK";
?>
```

- Ensure the directory `/var/www/testsite` and its contents are owned by `www-data:www-data`.

### 9. End-to-End Verification
- Add `127.0.0.1 testsite.local` to `/etc/hosts` if not already present.
- Requesting `http://testsite.local/index.php` via curl must return a response body containing the string `LEMP Stack OK`.
- Requesting `https://testsite.local/index.php` via curl (with `-k` for self-signed cert) must also return a response body containing `LEMP Stack OK`.
