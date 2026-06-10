## Configure Apache Virtual Hosts with SSL

Set up Apache HTTP Server with SSL-enabled virtual hosts serving three domains (`site1.local`, `site2.local`, `site3.local`) from the same server, each with its own self-signed SSL certificate, custom web content, and log files.

### Requirements

1. **Apache and SSL Module**
   - Install Apache (`apache2`) and enable the `ssl` module (`mod_ssl`).
   - Apache must be running and enabled to start on boot.

2. **Document Roots**
   - Create the following document root directories:
     - `/var/www/site1.local`
     - `/var/www/site2.local`
     - `/var/www/site3.local`
   - Each directory must be owned by `www-data:www-data` with permissions `755`.

3. **Index Pages**
   - Create an `index.html` file in each document root.
   - Each `index.html` must contain at minimum an `<h1>` tag with the text `Welcome to <domain>` where `<domain>` is the respective domain name (e.g., `Welcome to site1.local`).

4. **Self-Signed SSL Certificates**
   - Generate a self-signed SSL certificate and key for each domain, stored at:
     - `/etc/ssl/certs/<domain>.crt` (certificate)
     - `/etc/ssl/private/<domain>.key` (private key)
   - For example: `/etc/ssl/certs/site1.local.crt` and `/etc/ssl/private/site1.local.key`.
   - Each certificate's Common Name (CN) must match its domain name.
   - Key files must have permissions `600`.

5. **Virtual Host Configuration**
   - Create a separate Apache virtual host configuration file for each domain under `/etc/apache2/sites-available/`:
     - `/etc/apache2/sites-available/site1.local.conf`
     - `/etc/apache2/sites-available/site2.local.conf`
     - `/etc/apache2/sites-available/site3.local.conf`
   - Each configuration file must define:
     - A `<VirtualHost *:443>` block with `ServerName` set to the domain.
     - `DocumentRoot` pointing to the correct document root.
     - `SSLEngine on` with `SSLCertificateFile` and `SSLCertificateKeyFile` pointing to the correct cert/key paths.
     - Custom log files:
       - Access log: `/var/log/apache2/<domain>-access.log`
       - Error log: `/var/log/apache2/<domain>-error.log`
   - All three virtual host configurations must be enabled (symlinked in `/etc/apache2/sites-enabled/`).

6. **Local DNS Resolution**
   - Add entries to `/etc/hosts` so that `site1.local`, `site2.local`, and `site3.local` all resolve to `127.0.0.1`.

7. **Service Validation**
   - Apache must pass configuration syntax check (`apachectl configtest` or `apache2ctl configtest` returns `Syntax OK`).
   - Apache must be actively running after all configuration is complete.
   - Each domain must be accessible via HTTPS on port 443 (e.g., `https://site1.local` should return the corresponding `index.html` content).
