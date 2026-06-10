## Configure LEMP Stack with WordPress on Ubuntu 22.04

Deploy a functional WordPress site on Ubuntu 22.04 using a LEMP stack (Linux, Nginx, MySQL/MariaDB, PHP-FPM). Generate all necessary configuration files and a setup script.

### Technical Requirements

- Operating System: Ubuntu 22.04
- Web Server: Nginx
- Database: MySQL 8.0 (or MariaDB 10.6+)
- PHP: PHP 8.1 with FPM
- Application: WordPress (latest)
- All output files go under `/app/`

### Deliverables

Produce the following files:

1. `/app/setup.sh` — A single idempotent Bash script that, when run as root on a fresh Ubuntu 22.04 system, performs the full LEMP + WordPress deployment described below. The script must be executable and start with `#!/bin/bash`.

2. `/app/nginx/wordpress.conf` — The Nginx server block configuration file for the WordPress site.

3. `/app/php/www.conf` — The PHP-FPM pool configuration file for the WordPress pool.

4. `/app/wp-config.php` — A WordPress configuration file with database credentials and security keys filled in.

5. `/app/security/ufw-rules.sh` — A script that configures UFW firewall rules.

6. `/app/security/hardening.conf` — An Nginx security hardening snippet to be included in the server block.

### setup.sh Requirements

The script must perform these steps in order:

1. Update apt package lists and install prerequisites: `curl`, `gnupg2`, `ca-certificates`, `lsb-release`, `apt-transport-https`, `unzip`.
2. Install and start MySQL 8.0 (or MariaDB). Create a database named `wordpress_db`, a MySQL user named `wp_user` with password `WpS3cur3!Pass`, and grant that user all privileges on `wordpress_db`.
3. Install Nginx from the official Nginx repository or Ubuntu repos. Enable and start the Nginx service.
4. Add the Ondřej Surý PHP PPA and install `php8.1-fpm` plus these extensions: `php8.1-mysql`, `php8.1-curl`, `php8.1-gd`, `php8.1-intl`, `php8.1-mbstring`, `php8.1-soap`, `php8.1-xml`, `php8.1-zip`, `php8.1-imagick`. Enable and start PHP-FPM.
5. Download the latest WordPress tarball from `https://wordpress.org/latest.tar.gz`, extract it to `/var/www/wordpress`, and set ownership to `www-data:www-data`. Set directory permissions to `755` and file permissions to `644`.
6. Copy the generated `wp-config.php` into `/var/www/wordpress/wp-config.php`.
7. Deploy the Nginx server block config to `/etc/nginx/sites-available/wordpress.conf`, symlink it to `/etc/nginx/sites-enabled/`, remove the default site symlink from `sites-enabled`, and reload Nginx.
8. Install `certbot` and `python3-certbot-nginx`. Include a commented-out certbot command showing how to obtain a certificate for the domain (use `example.com` as placeholder). Add a cron entry or systemd timer for automatic certificate renewal.
9. Install and enable `fail2ban`.

### nginx/wordpress.conf Requirements

- Listen on port 80 with `server_name example.com www.example.com;`.
- Set `root /var/www/wordpress;` and `index index.php index.html;`.
- Include a `location /` block with `try_files $uri $uri/ /index.php?$args;`.
- Include a `location ~ \.php$` block that passes requests to the PHP-FPM socket at `unix:/run/php/php8.1-fpm.sock` using `fastcgi_pass`, and includes `fastcgi_params`. Set `fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;`.
- Include a `location ~ /\.ht` block that returns `deny all;`.
- Include the security hardening snippet via `include /etc/nginx/snippets/hardening.conf;`.

### php/www.conf Requirements

- Pool name: `[www]`
- `user = www-data`
- `group = www-data`
- `listen = /run/php/php8.1-fpm.sock`
- `listen.owner = www-data`
- `listen.group = www-data`
- `pm = dynamic`
- `pm.max_children = 10`
- `pm.start_servers = 2`
- `pm.min_spare_servers = 1`
- `pm.max_spare_servers = 5`

### wp-config.php Requirements

- `DB_NAME` set to `wordpress_db`
- `DB_USER` set to `wp_user`
- `DB_PASSWORD` set to `WpS3cur3!Pass`
- `DB_HOST` set to `localhost`
- `$table_prefix` set to `wp_`
- Must contain all 8 WordPress authentication keys/salts (`AUTH_KEY`, `SECURE_AUTH_KEY`, `LOGGED_IN_KEY`, `NONCE_KEY`, `AUTH_SALT`, `SECURE_AUTH_SALT`, `LOGGED_IN_SALT`, `NONCE_SALT`), each defined with a non-empty unique string value.
- Must contain `define( 'WP_DEBUG', false );`
- Must include the standard `ABSPATH` definition and `require_once` for `wp-settings.php`.

### security/ufw-rules.sh Requirements

- Must be an executable Bash script starting with `#!/bin/bash`.
- Set default incoming policy to deny: `ufw default deny incoming`.
- Set default outgoing policy to allow: `ufw default allow outgoing`.
- Allow SSH (port 22), HTTP (port 80), and HTTPS (port 443).
- Enable UFW non-interactively (use `--force` or `yes |` to avoid interactive prompt).

### security/hardening.conf Requirements

This is an Nginx config snippet (not a full server block). It must contain at minimum:

- `add_header X-Frame-Options "SAMEORIGIN" always;`
- `add_header X-Content-Type-Options "nosniff" always;`
- `add_header X-XSS-Protection "1; mode=block" always;`
- `server_tokens off;`
