Containerize a legacy PHP/MySQL application into a Dockerized LAMP stack using Docker Compose, with persistent data, secure credentials, and automated database seeding.

## Technical Requirements

- Docker and Docker Compose (Compose file format version "3.8")
- All project files under `/app/`

## Project Structure

Create the following directory layout:

```
/app/
  docker-compose.yml
  .env
  Makefile
  php/
    Dockerfile
  src/
    index.php
  mysql/
    init/
      seed.sql
```

## File Specifications

### `.env`

Must define exactly these variables (values are your choice but must be non-empty):

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`

### `php/Dockerfile`

- Base image: `php:5.6-apache`
- Install and enable these PHP extensions: `mysqli`, `gd`, `mcrypt`, `zip`
- Set the Apache document root to `/var/www/html`
- The container must serve files from the bind-mounted `src/` directory

### `src/index.php`

Create a minimal PHP page that:

1. Reads database credentials from environment variables (`MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`)
2. Connects to the MySQL host named `db` on port 3306 using `mysqli`
3. Queries the `campaigns` table with `SELECT * FROM campaigns`
4. Outputs an HTML page containing the query results. If the connection or query fails, output an HTML page containing the text `Error`.

### `mysql/init/seed.sql`

Create a SQL seed script that:

1. Creates a table `campaigns` with columns:
   - `id` INT AUTO_INCREMENT PRIMARY KEY
   - `name` VARCHAR(255) NOT NULL
   - `status` VARCHAR(50) NOT NULL
   - `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
2. Inserts exactly 3 rows:
   - (`'Summer Sale'`, `'active'`)
   - (`'Winter Promo'`, `'paused'`)
   - (`'Spring Launch'`, `'draft'`)

### `docker-compose.yml`

Must define exactly two services:

**Service `web`:**
- Builds from `./php/`
- Bind-mounts `./src` to `/var/www/html` in the container
- Maps host port `8080` to container port `80`
- Loads environment variables from the `.env` file using `env_file`
- Depends on the `db` service
- Sets `restart: unless-stopped`

**Service `db`:**
- Uses image `mysql:5.7`
- Loads environment variables from the `.env` file using `env_file`
- Stores data in a named volume `mysql_data` mounted at `/var/lib/mysql`
- Bind-mounts `./mysql/init/` to `/docker-entrypoint-initdb.d/` for automatic seed execution on first launch
- Includes a health check that runs `mysqladmin ping -h localhost` with interval 10s, timeout 5s, and 5 retries

**Volumes section:**
- Declare the named volume `mysql_data`

### `Makefile`

Must include these targets:

- `build` : runs `docker-compose build`
- `up` : runs `docker-compose up -d`
- `down` : runs `docker-compose down`
- `logs` : runs `docker-compose logs -f`
- `destroy` : runs `docker-compose down -v`
