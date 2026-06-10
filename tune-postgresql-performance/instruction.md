## PostgreSQL Performance Tuning

Optimize a PostgreSQL database's performance by tuning configuration parameters and implementing best practices for a server with 4 CPU cores and 8 GB RAM.

### Technical Requirements

- PostgreSQL (latest available via system package manager)
- pgBouncer for connection pooling
- pgbench for benchmarking
- OS: Linux (Debian/Ubuntu-based)

### Tasks

**1. Install PostgreSQL and Initialize Database Cluster**

Install PostgreSQL and ensure the service is running. Create a database named `webapp_db` owned by a user named `webapp_user` (password: `webapp_pass`). The user should have full privileges on `webapp_db`.

**2. Configure Memory Parameters**

Edit the PostgreSQL configuration to tune memory for an 8 GB RAM system. The following parameters in `postgresql.conf` must be set:

- `shared_buffers`: set to `2GB`
- `effective_cache_size`: set to `6GB`
- `work_mem`: set to `64MB`
- `maintenance_work_mem`: set to `512MB`
- `max_connections`: set to `200`

After changes, restart PostgreSQL so the settings take effect.

**3. Configure Checkpoint and WAL Settings**

Tune checkpoint and WAL parameters for write-heavy workloads in `postgresql.conf`:

- `wal_buffers`: set to `64MB`
- `checkpoint_completion_target`: set to `0.9`
- `max_wal_size`: set to `2GB`
- `min_wal_size`: set to `512MB`
- `random_page_cost`: set to `1.1`
- `effective_io_concurrency`: set to `200`

Restart PostgreSQL after applying changes.

**4. Set Up Connection Pooling with pgBouncer**

Install and configure pgBouncer with the following settings in `/etc/pgbouncer/pgbouncer.ini`:

- Listen on `127.0.0.1` port `6432`
- Pool mode: `transaction`
- `max_client_conn`: `400`
- `default_pool_size`: `40`
- Database entry for `webapp_db` pointing to the local PostgreSQL instance on port `5432` with user `webapp_user`

Configure the pgBouncer userlist file (`/etc/pgbouncer/userlist.txt`) to include `webapp_user`. Ensure the pgBouncer service is running.

**5. Configure Logging for Performance Monitoring**

Set the following logging parameters in `postgresql.conf`:

- `logging_collector`: `on`
- `log_directory`: `log`
- `log_filename`: `postgresql-%Y-%m-%d.log`
- `log_min_duration_statement`: `500` (log queries taking more than 500ms)
- `log_checkpoints`: `on`
- `log_connections`: `on`
- `log_disconnections`: `on`
- `log_lock_waits`: `on`
- `log_temp_files`: `0`

Restart PostgreSQL after applying changes.

**6. Create Sample Database with Test Data**

Connect to `webapp_db` as `webapp_user` and initialize it with pgbench:

```
pgbench -i -s 50 webapp_db -U webapp_user
```

This creates the standard pgbench tables with a scale factor of 50.

**7. Run pgbench Benchmark**

Run a pgbench benchmark against `webapp_db` with the following parameters:

- Clients: `20`
- Threads: `4`
- Duration: `60` seconds

Save the full benchmark output (stdout and stderr) to `/app/pgbench_results.txt`.

**8. Document Configuration Changes**

Write a JSON documentation file to `/app/tuning_report.json` with the following structure:

```json
{
  "server_specs": {
    "cpu_cores": 4,
    "ram_gb": 8
  },
  "memory_settings": {
    "shared_buffers": "2GB",
    "effective_cache_size": "6GB",
    "work_mem": "64MB",
    "maintenance_work_mem": "512MB",
    "max_connections": 200
  },
  "wal_settings": {
    "wal_buffers": "64MB",
    "checkpoint_completion_target": 0.9,
    "max_wal_size": "2GB",
    "min_wal_size": "512MB",
    "random_page_cost": 1.1,
    "effective_io_concurrency": 200
  },
  "logging_settings": {
    "logging_collector": "on",
    "log_min_duration_statement": 500,
    "log_checkpoints": "on",
    "log_connections": "on",
    "log_disconnections": "on",
    "log_lock_waits": "on"
  },
  "pgbouncer_settings": {
    "listen_port": 6432,
    "pool_mode": "transaction",
    "max_client_conn": 400,
    "default_pool_size": 40
  },
  "pgbench_config": {
    "scale_factor": 50,
    "clients": 20,
    "threads": 4,
    "duration_seconds": 60
  }
}
```

### Output Files

| File | Description |
|------|-------------|
| `/app/pgbench_results.txt` | Full pgbench benchmark output |
| `/app/tuning_report.json` | JSON documentation of all configuration changes |
