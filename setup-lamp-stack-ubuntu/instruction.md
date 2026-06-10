Set up a LAMP stack (Linux, Apache, MySQL, PHP) on Ubuntu with a virtual host configuration for a project called "devproject" accessible via "devproject.local".

## Technical Requirements

- Platform: Ubuntu Linux
- Web Server: Apache2
- Database: MySQL Server
- PHP: Version 7.x or 8.x with common modules (php-mysql, php-cli)
- Virtual Host Domain: devproject.local
- Document Root: /var/www/devproject

## Implementation Requirements

1. **System Setup**
   - Update package lists and upgrade existing packages
   - Install Apache2, MySQL server, and PHP with required modules

2. **Virtual Host Configuration**
   - Create document root directory at `/var/www/devproject`
   - Create Apache virtual host configuration file at `/etc/apache2/sites-available/devproject.conf` with:
     - ServerName: devproject.local
     - DocumentRoot: /var/www/devproject
     - Directory permissions allowing .htaccess overrides
   - Enable the virtual host configuration
   - Enable Apache mod_rewrite module

3. **DNS Resolution**
   - Configure `/etc/hosts` to resolve devproject.local to 127.0.0.1

4. **Verification Output**
   - Create a PHP info file at `/var/www/devproject/index.php` that displays PHP configuration
   - Generate a configuration summary file at `/app/output.json` containing:
     ```json
     {
       "apache_version": "Apache/2.x.x",
       "php_version": "7.x.x or 8.x.x",
       "mysql_version": "8.x.x or 5.x.x",
       "virtual_host_enabled": true,
       "document_root": "/var/www/devproject",
       "server_name": "devproject.local",
       "modules_enabled": ["rewrite"]
     }
     ```

## Expected Outputs

- `/app/output.json`: JSON file with LAMP stack configuration details
- `/var/www/devproject/index.php`: PHP file that displays phpinfo()
- `/etc/apache2/sites-available/devproject.conf`: Virtual host configuration file
- Apache service running and enabled
- MySQL service running and enabled
