Deploy a production-ready WordPress site on Ubuntu 22.04 with Nginx, MySQL, and SSL certificate, ensuring all services are properly configured and secured.

## Technical Requirements

- Platform: Ubuntu 22.04 LTS
- Web Server: Nginx
- Database: MySQL 8.0+
- PHP: PHP-FPM 8.1+
- SSL: Let's Encrypt (Certbot)
- Domain: example.com (use for configuration)

## Implementation Requirements

### 1. System Setup
Install and configure the following packages:
- nginx
- mysql-server
- php-fpm (version 8.1 or higher)
- php-mysql
- certbot
- python3-certbot-nginx

### 2. MySQL Database Configuration
Create a MySQL database with the following specifications:
- Database name: wordpress_db
- Database user: wp_user
- User must have full privileges on wordpress_db only
- MySQL root access must be secured (remove test databases, anonymous users)

### 3. WordPress Installation
- Download WordPress latest version to /var/www/wordpress
- Configure wp-config.php with database credentials
- Set ownership to www-data:www-data
- Set directory permissions to 755
- Set file permissions to 644

### 4. Nginx Configuration
Create Nginx server block at /etc/nginx/sites-available/wordpress with:
- Server name: example.com
- Document root: /var/www/wordpress
- PHP-FPM socket configuration
- Index priority: index.php, index.html
- PHP file handling for WordPress permalinks
- Client max body size: 64M

Enable the site and ensure Nginx configuration is valid.

### 5. SSL Configuration
- Install SSL certificate for example.com using Certbot
- Configure Nginx to serve HTTPS on port 443
- Redirect all HTTP (port 80) traffic to HTTPS
- SSL certificate auto-renewal must be enabled

### 6. Firewall Configuration
Configure UFW firewall to allow:
- SSH (port 22)
- HTTP (port 80)
- HTTPS (port 443)
- UFW must be enabled and active

### 7. Backup Automation
Create a cron job that runs weekly to backup the WordPress database:
- Backup file location: /var/backups/wordpress/
- Backup filename format: wordpress_db_YYYY-MM-DD.sql
- Schedule: Every Sunday at 2:00 AM
- Ensure backup directory exists with proper permissions

## Verification Points

The deployment must satisfy:
- Nginx service is active and running
- MySQL service is active and running
- PHP-FPM service is active and running
- WordPress files exist at /var/www/wordpress with correct permissions
- Nginx configuration syntax is valid
- SSL certificate is installed and valid
- HTTP to HTTPS redirect is functional
- UFW firewall is active with correct rules
- Database backup cron job is configured
- All services start automatically on system boot
