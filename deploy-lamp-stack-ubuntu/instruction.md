Deploy a functional LAMP (Linux, Apache, MySQL, PHP) stack on Ubuntu 22.04 with secured MySQL installation and verify all components are operational.

## Technical Requirements

- Platform: Ubuntu 22.04
- Web Server: Apache 2.4+ with mod_rewrite enabled
- Database: MySQL 8.0+ with secure installation
- PHP: Version 8.1 with common extensions (mysqli, curl, xml, mbstring)
- Apache module: libapache2-mod-php

## Implementation Requirements

1. **System Setup**
   - Update package manager and upgrade existing packages
   - Install and configure Apache to start on boot
   - Install MySQL server and run secure installation
   - Install PHP 8.1 with required extensions

2. **Apache Configuration**
   - Enable mod_rewrite module
   - Configure Apache to process PHP files
   - Ensure Apache service is running and enabled

3. **MySQL Configuration**
   - Create database named: `webapp_db`
   - Create MySQL user: `webapp_user` with password: `WebApp2024!`
   - Grant all privileges on `webapp_db` to `webapp_user`

4. **Verification Files**
   - Create PHP info page at: `/var/www/html/info.php` (displays phpinfo())
   - Create database connection test at: `/var/www/html/dbtest.php`
   - The dbtest.php must connect to MySQL using webapp_user credentials and output connection status

5. **Output Requirements**
   - Generate system status report at: `/app/lamp_status.json`
   - JSON structure:
     ```json
     {
       "apache": {"installed": true, "running": true, "mod_rewrite_enabled": true},
       "mysql": {"installed": true, "running": true, "webapp_db_exists": true, "webapp_user_exists": true},
       "php": {"installed": true, "version": "8.1.x", "mysqli_enabled": true},
       "test_files": {"info_php_exists": true, "dbtest_php_exists": true}
     }
     ```

## Validation Criteria

- All services (Apache, MySQL) must be active and enabled
- PHP info page must be accessible and display PHP 8.1+ information
- Database connection test must successfully connect to webapp_db
- Status report must accurately reflect all component states
