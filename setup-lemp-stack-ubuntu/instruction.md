## Local Web Server Setup with MySQL and PHP Support

Configure a fully-functional LEMP stack (Linux, Nginx, MySQL, PHP) on this Ubuntu system that can serve a PHP info page and connect to MySQL.

### Requirements

1. **System packages**: Update all system packages to their latest versions before installing new software.

2. **Nginx**:
   - Install and start the Nginx web server.
   - Nginx must be running and listening on port 80.
   - Configure a server block (default site) with document root `/var/www/html` that processes `.php` files through PHP-FPM.

3. **MySQL**:
   - Install MySQL server and ensure the service is running.
   - Create a database named `testdb`.
   - Create a MySQL user `testuser` with password `testpass` that has full privileges on `testdb`.

4. **PHP**:
   - Install PHP-FPM and the PHP MySQL extension (`php-mysql`).
   - PHP-FPM service must be running.
   - Nginx must be configured to pass `.php` requests to the PHP-FPM socket.

5. **PHP Info Page**:
   - Create a file at `/var/www/html/info.php` that calls `phpinfo()` and outputs the full PHP information page.
   - `curl http://localhost/info.php` must return HTML output containing the string `phpinfo()`.

6. **MySQL Connectivity Test**:
   - Create a file at `/var/www/html/db_test.php` that:
     - Connects to MySQL using the credentials above (`testuser` / `testpass` / `testdb`).
     - On success, outputs exactly: `DB_CONNECTION_SUCCESS`
     - On failure, outputs exactly: `DB_CONNECTION_FAILED`
   - `curl http://localhost/db_test.php` must return `DB_CONNECTION_SUCCESS`.

7. **Version Documentation**:
   - Write a file at `/app/versions.txt` with the installed version numbers, one per line, in this exact format:
     ```
     nginx: <version>
     mysql: <version>
     php: <version>
     ```
   - Each line must start with the lowercase service name, followed by a colon and a space, then the version string (e.g., `nginx: 1.18.0`).

8. **Cleanup**:
   - Clean the package manager cache (`apt clean`) after all installations are complete.
