## Custom Package Repository Mirror

Set up the configuration and infrastructure for a local Ubuntu package repository mirror for the jammy (22.04) release, restricted to main and universe components, and configure the local system to use this mirror.

### Technical Requirements

- OS: Ubuntu (Debian-based system with apt)
- Tools: `apt-mirror`, a web server (e.g., `nginx` or `apache2`), `cron`

### Tasks

1. **Install apt-mirror** — Ensure the `apt-mirror` package is installed on the system.

2. **Configure apt-mirror** — Create/modify the apt-mirror configuration file at `/etc/apt/mirror.list` with the following requirements:
   - Mirror source: `http://archive.ubuntu.com/ubuntu`
   - Distribution: `jammy`
   - Components: exactly `main` and `universe` (no other components such as `restricted` or `multiverse`)
   - Include both `deb` and `deb-src` lines
   - The `base_path` must be set to `/var/spool/apt-mirror`

3. **Set up a web server** — Install and configure a web server to serve the mirrored repository:
   - The web server service (nginx or apache2) must be installed and enabled
   - The document root or an alias must point to `/var/spool/apt-mirror/mirror` so that the mirrored packages are accessible via HTTP on the local machine (e.g., `http://localhost/ubuntu`)

4. **Configure the local system to use the mirror** — Create a new apt sources list file at `/etc/apt/sources.list.d/local-mirror.list` that:
   - Points to the local mirror (e.g., `http://localhost/ubuntu`)
   - Includes `jammy` distribution with `main` and `universe` components
   - Contains at least one `deb` line

5. **Set up a daily cron job** — Create a cron job that runs `apt-mirror` daily to keep the mirror updated. The cron entry must:
   - Be located in `/etc/cron.d/apt-mirror-update` (as a system cron file)
   - Execute `apt-mirror` at least once per day
   - The cron file must be valid (proper cron syntax with user field)

6. **Document disk space usage** — Write a script at `/app/check_mirror_size.sh` that:
   - Is executable (`chmod +x`)
   - When run, outputs the disk usage of `/var/spool/apt-mirror` using `du`
   - The output must include the path `/var/spool/apt-mirror`

### Output Summary

| Artifact | Path |
|---|---|
| apt-mirror config | `/etc/apt/mirror.list` |
| Web server config | nginx: `/etc/nginx/sites-enabled/` or apache: `/etc/apache2/sites-enabled/` |
| Local apt source | `/etc/apt/sources.list.d/local-mirror.list` |
| Cron job | `/etc/cron.d/apt-mirror-update` |
| Disk usage script | `/app/check_mirror_size.sh` |
