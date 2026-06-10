## PHP Multi-Vhost Deployment with MySQL Backend

Configure a production-ready LAMP stack on a single server hosting two distinct PHP applications (WordPress and Laravel) on separate ports, backed by isolated MySQL databases, with Apache virtual host configurations. Script the entire build so it can be reproduced.

### Technical Requirements

- OS: Ubuntu 22.04
- Web server: Apache2
- Database: MySQL 8
- PHP: 8.1 with extensions: mysqli, pdo_mysql, mbstring, xml, curl, zip, gd, imagick, intl, bcmath
- All configuration is done via a single reproducible shell script at `/app/setup.sh`

### Implementation Details

1. **Package Installation**
   - Update the package index.
   - Install Apache2, MySQL 8, PHP 8.1 and all required extensions listed above.

2. **MySQL Setup**
   - Start and enable the MySQL service.
   - Create two databases: `wp_demo` and `laravel_demo`.
   - Create dedicated MySQL users with passwords:
     - User `wp_user` with password `WpStr0ng!Pass` granted all privileges on `wp_demo`.
     - User `laravel_user` with password `LaravelStr0ng!Pass` granted all privileges on `laravel_demo`.
   - Each user must only have access to its own database.

3. **Apache Port Configuration**
   - Apache must listen on ports `8080` and `8081` (in addition to or instead of the default port 80).
   - Enable Apache modules: `rewrite`, `headers`, `env`.

4. **Virtual Host Configuration**
   - Create `/etc/apache2/sites-available/000-wp.conf`:
     - `<VirtualHost *:8080>`
     - `ServerName wp.acme.test`
     - `DocumentRoot /var/www/wp`
     - Must include `AllowOverride All` for the document root directory.
   - Create `/etc/apache2/sites-available/001-laravel.conf`:
     - `<VirtualHost *:8081>`
     - `ServerName laravel.acme.test`
     - `DocumentRoot /var/www/laravel/public`
     - Must include `AllowOverride All` for the document root directory.
   - Both virtual hosts must be enabled (symlinked into `/etc/apache2/sites-enabled/`).

5. **Application Deployment**
   - Download and extract the latest WordPress into `/var/www/wp`. The directory must contain `wp-login.php` at `/var/www/wp/wp-login.php`.
   - Install Laravel 10.x via Composer into `/var/www/laravel`. The directory must contain `artisan` at `/var/www/laravel/artisan`.

6. **File Ownership and Permissions**
   - Both `/var/www/wp` and `/var/www/laravel` (recursively) must be owned by `www-data:www-data`.
   - Directories under both webroots must have permission `755`.
   - Files under both webroots must have permission `644`.

7. **Laravel Environment Configuration**
   - Create `/var/www/laravel/.env` (from `.env.example` if available).
   - The `.env` file must contain at minimum:
     - `DB_DATABASE=laravel_demo`
     - `DB_USERNAME=laravel_user`
     - `DB_PASSWORD=LaravelStr0ng!Pass`

8. **Health-Check Script**
   - Create an executable script at `/usr/local/bin/check-sites.sh`.
   - The script must:
     - Perform an HTTP request to `http://localhost:8080/` and verify it returns HTTP status 200.
     - Perform an HTTP request to `http://localhost:8081/` and verify it returns HTTP status 200.
     - Exit with code `0` if both return 200, or exit with a non-zero code otherwise.
   - The script must be executable (`chmod +x`).

9. **Artifacts**
   - Create directory `/root/artifacts/`.
   - Copy the following files into `/root/artifacts/`:
     - `/usr/local/bin/check-sites.sh` → `/root/artifacts/check-sites.sh`
     - `/etc/apache2/sites-available/000-wp.conf` → `/root/artifacts/000-wp.conf`
     - `/etc/apache2/sites-available/001-laravel.conf` → `/root/artifacts/001-laravel.conf`

10. **Final State**
    - Apache must be running and serving both virtual hosts.
    - MySQL must be running.
    - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/` must return `200`.
    - `curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/` must return `200`.
