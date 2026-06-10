## Fix Broken MySQL Replication

A small e-commerce company runs MySQL 8.0 on Ubuntu 20.04. The master database is in the local data-center; two slaves (slave1 and slave2) are in the cloud. After last night's maintenance window, replication broke on both slaves. The SQL threads are stopped and errors are present. Business-critical reports and the web-shop's read-only queries are now hitting the master.

You are given a JSON file `/app/input.json` containing the replication status snapshots from all three hosts. Analyze the data, produce a structured repair plan, and generate a root-cause report.

### Input

`/app/input.json` — a JSON object with three top-level keys: `master`, `slave1`, `slave2`.

The `master` object contains:
- `binlog_file` (string): current binary log file name, e.g. `"mysql-bin.000042"`
- `binlog_position` (integer): current binary log position
- `executed_gtid_set` (string): GTID set executed on master
- `server_id` (integer)
- `read_only` (boolean): should be `false` for master

Each slave object (`slave1`, `slave2`) contains:
- `server_id` (integer)
- `master_host` (string)
- `read_only` (boolean): should be `true` for slaves
- `slave_io_running` (string): `"Yes"` or `"No"`
- `slave_sql_running` (string): `"Yes"` or `"No"`
- `master_log_file` (string): the binlog file the slave IO thread is reading from
- `read_master_log_pos` (integer): position the IO thread has read up to
- `relay_master_log_file` (string): the binlog file the SQL thread is executing from
- `exec_master_log_pos` (integer): position the SQL thread has executed up to
- `seconds_behind_master` (integer or `null`)
- `last_sql_errno` (integer): 0 means no error
- `last_sql_error` (string): empty string if no error
- `last_io_errno` (integer): 0 means no error
- `last_io_error` (string): empty string if no error
- `retrieved_gtid_set` (string)
- `executed_gtid_set` (string)
- `auto_position` (integer): 1 if GTID auto-positioning is enabled

### Output

Write a single JSON file to `/app/output.json` with the following structure:

```json
{
  "diagnosis": {
    "slave1": {
      "io_thread_ok": <boolean>,
      "sql_thread_ok": <boolean>,
      "error_type": "<string>",
      "error_code": <integer>,
      "error_message": "<string>",
      "binlog_lag": {
        "file_match": <boolean>,
        "position_diff": <integer>
      },
      "needs_reimaging": <boolean>
    },
    "slave2": {
      // same structure as slave1
    }
  },
  "repair_plan": [
    {
      "host": "<string: slave1 or slave2>",
      "step": <integer>,
      "action": "<string>",
      "sql_command": "<string>"
    }
  ],
  "root_cause": "<string: one-paragraph summary of what went wrong>",
  "post_repair": {
    "slave1_ready": <boolean>,
    "slave2_ready": <boolean>
  }
}
```

### Requirements

Use Python 3.

**diagnosis rules:**
- `io_thread_ok`: `true` if `slave_io_running` is `"Yes"`, else `false`.
- `sql_thread_ok`: `true` if `slave_sql_running` is `"Yes"`, else `false`.
- `error_type`: classify the error based on `last_sql_errno`:
  - `1062` → `"duplicate_key"`
  - `1032` → `"row_not_found"`
  - `1236` → `"binlog_missing"`
  - `0` → `"none"`
  - anything else → `"other"`
- `error_code`: copy of `last_sql_errno`.
- `error_message`: copy of `last_sql_error`.
- `binlog_lag.file_match`: `true` if the slave's `relay_master_log_file` equals the master's `binlog_file`.
- `binlog_lag.position_diff`: master's `binlog_position` minus slave's `exec_master_log_pos`.
- `needs_reimaging`: `true` if `error_type` is `"binlog_missing"` OR `position_diff > 1000000000` (1 billion); otherwise `false`.

**repair_plan rules:**
- For each slave that has errors, generate an ordered list of repair steps.
- If `needs_reimaging` is `true`, include a single step with `action` set to `"reimage_from_backup"` and `sql_command` set to `"STOP SLAVE; RESET SLAVE ALL;"`.
- If `needs_reimaging` is `false` and `error_type` is `"duplicate_key"` or `"row_not_found"`, generate two steps:
  1. `action`: `"skip_error"`, `sql_command`: `"STOP SLAVE; SET GLOBAL sql_slave_skip_counter = 1; START SLAVE;"`
  2. `action`: `"verify_replication"`, `sql_command`: `"SHOW SLAVE STATUS\\G"`
- If `error_type` is `"none"`, generate one step: `action`: `"start_slave"`, `sql_command`: `"START SLAVE;"`.
- Steps for slave1 come before steps for slave2. Step numbers are sequential starting from 1 across all slaves.

**root_cause:**
- A non-empty string summarizing the errors found across both slaves.

**post_repair:**
- `slave1_ready`: `true` if slave1's repair plan does NOT require reimaging, else `false`.
- `slave2_ready`: `true` if slave2's repair plan does NOT require reimaging, else `false`.

Also write the root-cause summary (same string as `root_cause` in the JSON) to `/app/REPAIR_LOG.txt` as plain text.
