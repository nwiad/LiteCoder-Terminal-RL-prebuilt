## Multi-Site Web Hosting with Nginx

Set up a containerized Nginx server that serves multiple websites from different domains using virtual hosts (server blocks).

**Technical Requirements:**
- Docker container with Nginx installed
- Two static websites with distinct content
- Domain names: `site1.local` and `site2.local`
- Virtual host configuration for both domains

**Directory Structure:**
Create the following structure:
- `/var/www/site1/` - content directory for site1.local
- `/var/www/site2/` - content directory for site2.local
- Each directory must contain an `index.html` file

**Website Content Requirements:**
- `/var/www/site1/index.html` must contain the text "Welcome to Site 1"
- `/var/www/site2/index.html` must contain the text "Welcome to Site 2"

**Nginx Configuration:**
- Configure two server blocks in Nginx
- `site1.local` should serve content from `/var/www/site1/`
- `site2.local` should serve content from `/var/www/site2/`
- Both sites should listen on port 80

**DNS Resolution:**
Configure `/etc/hosts` to map both domain names to localhost (127.0.0.1)

**Verification:**
The setup must satisfy these conditions:
- `curl http://site1.local` returns content containing "Welcome to Site 1"
- `curl http://site2.local` returns content containing "Welcome to Site 2"
- Both sites must be accessible simultaneously from within the container
