## Host Multiple Websites with Apache Virtual Hosts

Configure Apache on Ubuntu to serve two distinct websites (`site1.local` and `site2.local`) using name-based virtual hosts on port 80, all on a single machine.

### Requirements

1. **Install Apache** (`apache2` package) and ensure the service is running.

2. **Directory structure:** Create the following document roots with appropriate ownership (`www-data:www-data`) and permissions (directories `755`, files `644`):
   - `/var/www/site1.local/`
   - `/var/www/site2.local/`

3. **Site content:** Each site must have an `index.html`:
   - `/var/www/site1.local/index.html` — must contain the exact string `site1.local` somewhere in the body.
   - `/var/www/site2.local/index.html` — must contain the exact string `site2.local` somewhere in the body.
   - The two files must have different content (they must NOT be identical).

4. **Virtual host configuration files:**
   - `/etc/apache2/sites-available/site1.local.conf` — a `<VirtualHost *:80>` block with:
     - `ServerName site1.local`
     - `DocumentRoot /var/www/site1.local`
   - `/etc/apache2/sites-available/site2.local.conf` — a `<VirtualHost *:80>` block with:
     - `ServerName site2.local`
     - `DocumentRoot /var/www/site2.local`

5. **Enable/disable sites:**
   - Both `site1.local.conf` and `site2.local.conf` must be enabled (symlinked in `/etc/apache2/sites-enabled/`).
   - The default site (`000-default.conf`) must be disabled (no symlink in `sites-enabled`).

6. **Local DNS:** Add entries to `/etc/hosts` so that both `site1.local` and `site2.local` resolve to `127.0.0.1`.

7. **Apache status:** Apache configuration must pass syntax check (`apachectl configtest` returns `Syntax OK`), and the service must be running and listening on port 80.

8. **Verification via curl:**
   - `curl -s http://site1.local` must return content containing `site1.local` but NOT containing `site2.local`.
   - `curl -s http://site2.local` must return content containing `site2.local` but NOT containing `site1.local`.
   - `curl -s http://localhost` must NOT return the default Apache "It works" page (i.e., the response must not contain the string `It works!`).
