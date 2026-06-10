Configure MySQL master-slave replication between two servers with automated verification and monitoring.

## Technical Requirements

- MySQL 8.0+ on Ubuntu
- Configuration files: `/app/master.cnf` and `/app/slave.cnf`
- Replication setup script: `/app/setup_replication.sh`
- Monitoring script: `/app/check_replication.sh`
- Documentation: `/app/replication_config.json`

## Input Specifications

You will work with two MySQL server configurations:
- Master server: handles write operations, binary logging enabled
- Slave server: replicates from master, handles read operations

## Output Requirements

### 1. Master Configuration (`/app/master.cnf`)
MySQL configuration for the master server including:
- Unique server-id
- Binary logging enabled with log_bin
- binlog_format set appropriately
- Replication user credentials

### 2. Slave Configuration (`/app/slave.cnf`)
MySQL configuration for the slave server including:
- Unique server-id (different from master)
- Relay log configuration
- Read-only mode enabled

### 3. Setup Script (`/app/setup_replication.sh`)
Bash script that:
- Creates replication user on master
- Exports master database state
- Configures slave to connect to master
- Starts replication process
- Must be executable and idempotent

### 4. Monitoring Script (`/app/check_replication.sh`)
Bash script that outputs replication status in JSON format to `/app/replication_status.json`:
```json
{
  "slave_io_running": "Yes",
  "slave_sql_running": "Yes",
  "seconds_behind_master": 0,
  "last_error": "",
  "status": "healthy"
}
```

### 5. Configuration Documentation (`/app/replication_config.json`)
JSON file documenting the setup:
```json
{
  "master": {
    "host": "master_host",
    "port": 3306,
    "server_id": 1
  },
  "slave": {
    "host": "slave_host",
    "port": 3306,
    "server_id": 2
  },
  "replication_user": "repl_user",
  "binlog_format": "ROW"
}
```

## Validation Criteria

- Configuration files must be valid MySQL configuration syntax
- Scripts must handle connection errors gracefully
- Replication status must be verifiable programmatically
- All file paths must use `/app/` prefix
- Scripts must include proper error checking and exit codes
