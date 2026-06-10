"""
Tests for PostgreSQL Performance Tuning task.

Verifies:
- Output files exist and have correct content
- tuning_report.json has correct schema and values
- pgbench_results.txt contains real benchmark output
- PostgreSQL is running with correct configuration
- Database, user, and pgbench tables exist
- pgBouncer is configured correctly
- Logging parameters are set
"""

import os
import json
import re
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=10):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def psql_query(query, db="webapp_db", user="postgres"):
    """Run a psql query and return stdout."""
    cmd = f'su - postgres -c "psql -t -A -d {db} -c \\"{query}\\""'
    stdout, stderr, rc = run_cmd(cmd)
    return stdout


def pg_setting(name):
    """Query a single PostgreSQL setting value from pg_settings."""
    val = psql_query(f"SELECT setting FROM pg_settings WHERE name = '{name}';")
    return val.strip() if val else None


def find_pg_conf():
    """Find the postgresql.conf path dynamically."""
    stdout, _, _ = run_cmd("find /etc/postgresql -name postgresql.conf 2>/dev/null | head -1")
    if stdout:
        return stdout
    # Fallback: ask PostgreSQL itself
    val = psql_query("SHOW config_file;", db="postgres")
    return val.strip() if val else None


# ---------------------------------------------------------------------------
# 1. Output file existence
# ---------------------------------------------------------------------------

def test_pgbench_results_file_exists():
    assert os.path.isfile("/app/pgbench_results.txt"), \
        "/app/pgbench_results.txt does not exist"


def test_tuning_report_file_exists():
    assert os.path.isfile("/app/tuning_report.json"), \
        "/app/tuning_report.json does not exist"


# ---------------------------------------------------------------------------
# 2. pgbench_results.txt content validation
# ---------------------------------------------------------------------------

def test_pgbench_results_not_empty():
    content = open("/app/pgbench_results.txt").read()
    assert len(content.strip()) > 50, \
        "pgbench_results.txt appears empty or too short to be real output"


def test_pgbench_results_contains_tps():
    """Real pgbench output always reports transactions per second."""
    content = open("/app/pgbench_results.txt").read().lower()
    assert "tps" in content, \
        "pgbench_results.txt does not contain 'tps' — likely not real pgbench output"


def test_pgbench_results_contains_transaction_info():
    """Real pgbench output reports number of transactions actually processed."""
    content = open("/app/pgbench_results.txt").read().lower()
    assert "transaction" in content, \
        "pgbench_results.txt missing transaction information"


def test_pgbench_results_contains_latency_or_duration():
    """Real pgbench output includes latency or duration info."""
    content = open("/app/pgbench_results.txt").read().lower()
    has_latency = "latency" in content
    has_duration = "duration" in content or "time" in content
    assert has_latency or has_duration, \
        "pgbench_results.txt missing latency/duration information"


def test_pgbench_results_clients_and_threads():
    """Verify the benchmark was run with correct client/thread counts."""
    content = open("/app/pgbench_results.txt").read()
    # pgbench output typically says "number of clients: 20" and "number of threads: 4"
    has_clients = re.search(r"clients[:\s]+20", content, re.IGNORECASE)
    has_threads = re.search(r"threads[:\s]+4", content, re.IGNORECASE)
    assert has_clients, "pgbench output should show 20 clients"
    assert has_threads, "pgbench output should show 4 threads"


# ---------------------------------------------------------------------------
# 3. tuning_report.json schema and value validation
# ---------------------------------------------------------------------------

def _load_report():
    with open("/app/tuning_report.json") as f:
        return json.load(f)


def test_tuning_report_valid_json():
    """File must be parseable JSON."""
    try:
        _load_report()
    except json.JSONDecodeError as e:
        assert False, f"tuning_report.json is not valid JSON: {e}"


def test_tuning_report_top_level_keys():
    report = _load_report()
    required = {
        "server_specs", "memory_settings", "wal_settings",
        "logging_settings", "pgbouncer_settings", "pgbench_config",
    }
    missing = required - set(report.keys())
    assert not missing, f"Missing top-level keys: {missing}"


def test_tuning_report_server_specs():
    specs = _load_report()["server_specs"]
    assert specs.get("cpu_cores") == 4, "cpu_cores should be 4"
    assert specs.get("ram_gb") == 8, "ram_gb should be 8"


def test_tuning_report_memory_settings():
    mem = _load_report()["memory_settings"]
    assert mem.get("shared_buffers") == "2GB"
    assert mem.get("effective_cache_size") == "6GB"
    assert mem.get("work_mem") == "64MB"
    assert mem.get("maintenance_work_mem") == "512MB"
    assert mem.get("max_connections") == 200


def test_tuning_report_wal_settings():
    wal = _load_report()["wal_settings"]
    assert wal.get("wal_buffers") == "64MB"
    assert abs(wal.get("checkpoint_completion_target", 0) - 0.9) < 0.01
    assert wal.get("max_wal_size") == "2GB"
    assert wal.get("min_wal_size") == "512MB"
    assert abs(wal.get("random_page_cost", 0) - 1.1) < 0.01
    assert wal.get("effective_io_concurrency") == 200


def test_tuning_report_logging_settings():
    log = _load_report()["logging_settings"]
    assert log.get("logging_collector") == "on"
    assert log.get("log_min_duration_statement") == 500
    assert log.get("log_checkpoints") == "on"
    assert log.get("log_connections") == "on"
    assert log.get("log_disconnections") == "on"
    assert log.get("log_lock_waits") == "on"


def test_tuning_report_pgbouncer_settings():
    pgb = _load_report()["pgbouncer_settings"]
    assert pgb.get("listen_port") == 6432
    assert pgb.get("pool_mode") == "transaction"
    assert pgb.get("max_client_conn") == 400
    assert pgb.get("default_pool_size") == 40


def test_tuning_report_pgbench_config():
    bench = _load_report()["pgbench_config"]
    assert bench.get("scale_factor") == 50
    assert bench.get("clients") == 20
    assert bench.get("threads") == 4
    assert bench.get("duration_seconds") == 60


# ---------------------------------------------------------------------------
# 4. PostgreSQL is running and accessible
# ---------------------------------------------------------------------------

def test_postgresql_is_running():
    """PostgreSQL must be accepting connections."""
    _, _, rc = run_cmd("pg_isready")
    assert rc == 0, "PostgreSQL is not running or not accepting connections"


def test_webapp_db_exists():
    """The webapp_db database must exist."""
    out = psql_query(
        "SELECT datname FROM pg_database WHERE datname = 'webapp_db';",
        db="postgres",
    )
    assert "webapp_db" in out, "Database webapp_db does not exist"


def test_webapp_user_exists():
    """The webapp_user role must exist."""
    out = psql_query(
        "SELECT rolname FROM pg_roles WHERE rolname = 'webapp_user';",
        db="postgres",
    )
    assert "webapp_user" in out, "Role webapp_user does not exist"


def test_webapp_user_owns_webapp_db():
    """webapp_user should own webapp_db."""
    out = psql_query(
        "SELECT pg_catalog.pg_get_userbyid(d.datdba) "
        "FROM pg_database d WHERE d.datname = 'webapp_db';",
        db="postgres",
    )
    assert "webapp_user" in out, "webapp_db is not owned by webapp_user"


# ---------------------------------------------------------------------------
# 5. PostgreSQL memory parameters (live settings)
# ---------------------------------------------------------------------------

def test_pg_shared_buffers():
    val = pg_setting("shared_buffers")
    # shared_buffers is reported in 8kB pages; 2GB = 262144 pages
    assert val is not None
    assert int(val) == 262144, f"shared_buffers should be 262144 (2GB), got {val}"


def test_pg_effective_cache_size():
    val = pg_setting("effective_cache_size")
    # 6GB = 786432 pages of 8kB
    assert val is not None
    assert int(val) == 786432, f"effective_cache_size should be 786432 (6GB), got {val}"


def test_pg_work_mem():
    val = pg_setting("work_mem")
    # 64MB = 65536 kB
    assert val is not None
    assert int(val) == 65536, f"work_mem should be 65536 (64MB), got {val}"


def test_pg_maintenance_work_mem():
    val = pg_setting("maintenance_work_mem")
    # 512MB = 524288 kB
    assert val is not None
    assert int(val) == 524288, f"maintenance_work_mem should be 524288 (512MB), got {val}"


def test_pg_max_connections():
    val = pg_setting("max_connections")
    assert val is not None
    assert int(val) == 200, f"max_connections should be 200, got {val}"


# ---------------------------------------------------------------------------
# 6. WAL / checkpoint parameters (live settings)
# ---------------------------------------------------------------------------

def test_pg_wal_buffers():
    val = pg_setting("wal_buffers")
    # 64MB in 8kB pages = 8192
    assert val is not None
    assert int(val) == 8192, f"wal_buffers should be 8192 (64MB), got {val}"


def test_pg_checkpoint_completion_target():
    val = pg_setting("checkpoint_completion_target")
    assert val is not None
    assert abs(float(val) - 0.9) < 0.01, \
        f"checkpoint_completion_target should be 0.9, got {val}"


def test_pg_max_wal_size():
    val = pg_setting("max_wal_size")
    # max_wal_size is reported in MB: 2GB = 2048
    assert val is not None
    assert int(val) == 2048, f"max_wal_size should be 2048 (2GB), got {val}"


def test_pg_min_wal_size():
    val = pg_setting("min_wal_size")
    # min_wal_size is reported in MB: 512MB = 512
    assert val is not None
    assert int(val) == 512, f"min_wal_size should be 512 (512MB), got {val}"


def test_pg_random_page_cost():
    val = pg_setting("random_page_cost")
    assert val is not None
    assert abs(float(val) - 1.1) < 0.01, \
        f"random_page_cost should be 1.1, got {val}"


def test_pg_effective_io_concurrency():
    val = pg_setting("effective_io_concurrency")
    assert val is not None
    assert int(val) == 200, f"effective_io_concurrency should be 200, got {val}"


# ---------------------------------------------------------------------------
# 7. Logging parameters (live settings)
# ---------------------------------------------------------------------------

def test_pg_logging_collector():
    val = pg_setting("logging_collector")
    assert val is not None
    assert val == "on", f"logging_collector should be on, got {val}"


def test_pg_log_min_duration_statement():
    val = pg_setting("log_min_duration_statement")
    assert val is not None
    assert int(val) == 500, f"log_min_duration_statement should be 500, got {val}"


def test_pg_log_checkpoints():
    val = pg_setting("log_checkpoints")
    assert val is not None
    assert val == "on", f"log_checkpoints should be on, got {val}"


def test_pg_log_connections():
    val = pg_setting("log_connections")
    assert val is not None
    assert val == "on", f"log_connections should be on, got {val}"


def test_pg_log_disconnections():
    val = pg_setting("log_disconnections")
    assert val is not None
    assert val == "on", f"log_disconnections should be on, got {val}"


def test_pg_log_lock_waits():
    val = pg_setting("log_lock_waits")
    assert val is not None
    assert val == "on", f"log_lock_waits should be on, got {val}"


# ---------------------------------------------------------------------------
# 8. pgBouncer configuration file validation
# ---------------------------------------------------------------------------

def test_pgbouncer_ini_exists():
    assert os.path.isfile("/etc/pgbouncer/pgbouncer.ini"), \
        "/etc/pgbouncer/pgbouncer.ini does not exist"


def test_pgbouncer_ini_listen_port():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    assert re.search(r"listen_port\s*=\s*6432", content), \
        "pgbouncer.ini should have listen_port = 6432"


def test_pgbouncer_ini_listen_addr():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    assert re.search(r"listen_addr\s*=\s*127\.0\.0\.1", content), \
        "pgbouncer.ini should have listen_addr = 127.0.0.1"


def test_pgbouncer_ini_pool_mode():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    assert re.search(r"pool_mode\s*=\s*transaction", content), \
        "pgbouncer.ini should have pool_mode = transaction"


def test_pgbouncer_ini_max_client_conn():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    assert re.search(r"max_client_conn\s*=\s*400", content), \
        "pgbouncer.ini should have max_client_conn = 400"


def test_pgbouncer_ini_default_pool_size():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    assert re.search(r"default_pool_size\s*=\s*40", content), \
        "pgbouncer.ini should have default_pool_size = 40"


def test_pgbouncer_ini_webapp_db_entry():
    content = open("/etc/pgbouncer/pgbouncer.ini").read()
    # The databases section should reference webapp_db on port 5432
    assert "webapp_db" in content, \
        "pgbouncer.ini should have a webapp_db database entry"
    assert "5432" in content, \
        "pgbouncer.ini webapp_db entry should point to port 5432"


def test_pgbouncer_userlist_exists():
    assert os.path.isfile("/etc/pgbouncer/userlist.txt"), \
        "/etc/pgbouncer/userlist.txt does not exist"


def test_pgbouncer_userlist_contains_webapp_user():
    content = open("/etc/pgbouncer/userlist.txt").read()
    assert "webapp_user" in content, \
        "userlist.txt should contain webapp_user"


# ---------------------------------------------------------------------------
# 9. pgbench tables exist in webapp_db (proves init was run)
# ---------------------------------------------------------------------------

def test_pgbench_accounts_table_exists():
    """pgbench -i creates pgbench_accounts, pgbench_branches, etc."""
    out = psql_query(
        "SELECT tablename FROM pg_tables "
        "WHERE tablename = 'pgbench_accounts' AND schemaname = 'public';",
    )
    assert "pgbench_accounts" in out, \
        "pgbench_accounts table not found — pgbench -i may not have been run"


def test_pgbench_scale_factor():
    """Scale factor 50 means pgbench_branches has 50 rows."""
    out = psql_query("SELECT count(*) FROM pgbench_branches;")
    count = int(out.strip()) if out.strip().isdigit() else 0
    assert count == 50, \
        f"pgbench_branches should have 50 rows (scale factor 50), got {count}"
