## PostgreSQL Streaming Replication Configuration Generator

Generate a complete set of configuration files and shell scripts for deploying a PostgreSQL 15 streaming replication cluster with one primary node and two standby nodes.

### Technical Requirements

- Language: Bash scripts; PostgreSQL configuration file syntax
- All output files must be placed under `/app/output/`
- The cluster uses three nodes with the following hostnames and IPs:
  - Primary: `pg-primary` / `10.0.1.10`
  - Standby 1: `pg-standby1` / `10.0.1.11`
  - Standby 2: `pg-standby2` / `10.0.1.12`
- PostgreSQL version: 15
- PostgreSQL data directory: `/var/lib/postgresql/15/main`
- PostgreSQL config directory: `/etc/postgresql/15/main`
- Replication user: `replicator` with password `R3pl!cat0r_S3cure`
- Replication slots named: `standby1_slot` and `standby2_slot`

### Output Files

Generate the following files under `/app/output/`:

1. **`primary_postgresql.conf`** — PostgreSQL configuration for the primary node. Must include at minimum:
   - `listen_addresses` set to `'*'`
   - `wal_level` set to `replica`
   - `max_wal_senders` set to at least `10`
   - `max_replication_slots` set to at least `10`
   - `hot_standby` set to `on`
   - `wal_keep_size` set to at least `1GB`
   - `synchronous_standby_names` referencing both standbys
   - `archive_mode` set to `on`
   - `archive_command` defined (non-empty)

2. **`primary_pg_hba.conf`** — Host-based authentication for the primary node. Must include:
   - A replication entry allowing the replication user `replicator` from the subnet `10.0.1.0/24` using `md5` or `scram-sha-256` authentication
   - Standard local access entries

3. **`standby1_postgresql.conf`** — PostgreSQL configuration for standby1. Must include:
   - `hot_standby` set to `on`
   - `primary_conninfo` containing host `10.0.1.10`, port `5432`, user `replicator`, and password
   - `primary_slot_name` set to `standby1_slot`

4. **`standby2_postgresql.conf`** — PostgreSQL configuration for standby2. Must include:
   - `hot_standby` set to `on`
   - `primary_conninfo` containing host `10.0.1.10`, port `5432`, user `replicator`, and password
   - `primary_slot_name` set to `standby2_slot`

5. **`setup_primary.sh`** — Bash script to initialize the primary node. Must:
   - Start with `#!/bin/bash`
   - Contain a SQL command (via `psql` or similar) to create the `replicator` role with `REPLICATION` and `LOGIN` privileges
   - Contain commands to create both replication slots (`standby1_slot` and `standby2_slot`) using `pg_create_physical_replication_slot`
   - Include a command to reload or restart PostgreSQL

6. **`setup_standby.sh`** — Bash script to initialize a standby node from the primary. Must:
   - Start with `#!/bin/bash`
   - Accept the standby node number (1 or 2) as a command-line argument (e.g., `$1`)
   - Use `pg_basebackup` with host `10.0.1.10`, user `replicator`, and the appropriate slot name based on the argument
   - Create a `standby.signal` file in the data directory
   - Include a command to start PostgreSQL

7. **`monitor.sh`** — Bash script for basic replication monitoring. Must:
   - Start with `#!/bin/bash`
   - Query `pg_stat_replication` to show replication status
   - Query replication lag information (e.g., using `pg_wal_lsn_diff` or replay lag from `pg_stat_replication`)
   - Output results to stdout

8. **`cluster_info.json`** — JSON file documenting the cluster. Must be valid JSON with the following structure:
   ```json
   {
     "cluster_name": "<string>",
     "postgresql_version": 15,
     "nodes": [
       {
         "role": "primary",
         "hostname": "pg-primary",
         "ip": "10.0.1.10",
         "port": 5432
       },
       {
         "role": "standby",
         "hostname": "pg-standby1",
         "ip": "10.0.1.11",
         "port": 5432
       },
       {
         "role": "standby",
         "hostname": "pg-standby2",
         "ip": "10.0.1.12",
         "port": 5432
       }
     ],
     "replication_user": "replicator",
     "replication_slots": ["standby1_slot", "standby2_slot"]
   }
   ```
   - `nodes` array must contain exactly 3 entries with roles and IPs as specified above
   - `postgresql_version` must be the integer `15`
   - `replication_slots` must list both slot names

### Configuration File Format

- PostgreSQL `.conf` files use `key = value` syntax (one setting per line). Lines starting with `#` are comments.
- `pg_hba.conf` uses whitespace-separated columns: `type database user address method`
- All `.sh` files must be executable shell scripts with a proper shebang line.
