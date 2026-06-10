## Task: Configure a Basic LAMP Stack for Development

Set up a fully functional LAMP (Linux, Apache, MySQL, PHP) development stack on Ubuntu 22.04 with proper configuration and verification.

**Technical Requirements:**
- Platform: Ubuntu 22.04
- Services: Apache 2.4+, MySQL 8.0+, PHP 8.1+
- PHP Extensions: mysqli, json, mbstring, curl
- All services must be running and enabled at boot

**Implementation Requirements:**

1. **Apache Configuration:**
   - Install and start Apache web server
   - Enable mod_rewrite and mod_php
   - Configure to serve from /var/www/html
   - Create virtual host configuration at /etc/apache2/sites-available/dev.conf
   - Virtual host should listen on port 80 with ServerName localhost

2. **MySQL Setup:**
   - Install MySQL server
   - Create database named `devdb`
   - Create user `devuser` with password `devpass123` with full privileges on `devdb`
   - MySQL service must be active and enabled

3. **PHP Installation:**
   - Install PHP with required extensions: php-mysqli, php-json, php-mbstring, php-curl
   - Create test file at /var/www/html/info.php that displays phpinfo()
   - Create database test file at /var/www/html/dbtest.php that connects to MySQL using devuser credentials and outputs "Database connection successful" on success

4. **Verification Output:**
   - Create file /app/setup_report.json with the following structure:
   ```json
   {
     "apache": {
       "installed": true,
       "version": "2.4.x",
       "status": "active",
       "enabled": true
     },
     "mysql": {
       "installed": true,
       "version": "8.0.x",
       "status": "active",
       "enabled": true,
       "database_created": true,
       "user_created": true
     },
     "php": {
       "installed": true,
       "version": "8.1.x",
       "extensions": ["mysqli", "json", "mbstring", "curl"]
     },
     "test_files": {
       "info_php": "/var/www/html/info.php",
       "dbtest_php": "/var/www/html/dbtest.php"
     }
   }
   ```

5. **Service Verification:**
   - All version numbers should reflect actual installed versions
   - Status fields must be "active" for running services
   - Enabled field must be true if service starts on boot
   - Database and user creation must be verified as successful

**Success Criteria:**
- Apache serves PHP files correctly
- MySQL accepts connections from devuser
- PHP can connect to MySQL database
- All services are active and enabled
- setup_report.json contains accurate system state
