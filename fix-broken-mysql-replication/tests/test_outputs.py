"""
Tests for MySQL Replication Diagnosis and Repair Plan Generator.

Validates /app/output.json and /app/REPAIR_LOG.txt produced by the agent
against the deterministic rules in instruction.md, using the primary
input.json as well as the supplementary test_data/ scenarios.
"""

import json
import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
REPAIR_LOG = "/app/REPAIR_LOG.txt"
INPUT_JSON = "/app/input.json"
TEST_DATA_DIR = "/app/test_data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return parsed JSON from *path*, or None on failure."""
    if not os.path.isfile(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def expected_error_type(errno):
    """Map errno to the expected error_type string."""
    mapping = {1062: "duplicate_key", 1032: "row_not_found", 1236: "binlog_missing", 0: "none"}
    return mapping.get(errno, "other")


def expected_needs_reimaging(error_type, position_diff):
    return error_type == "binlog_missing" or position_diff > 1_000_000_000


def compute_expected_diagnosis(slave_data, master_data):
    """Compute the expected diagnosis dict for a single slave."""
    io_ok = slave_data["slave_io_running"] == "Yes"
    sql_ok = slave_data["slave_sql_running"] == "Yes"
    errno = slave_data["last_sql_errno"]
    etype = expected_error_type(errno)
    file_match = slave_data["relay_master_log_file"] == master_data["binlog_file"]
    pos_diff = master_data["binlog_position"] - slave_data["exec_master_log_pos"]
    reimaging = expected_needs_reimaging(etype, pos_diff)
    return {
        "io_thread_ok": io_ok,
        "sql_thread_ok": sql_ok,
        "error_type": etype,
        "error_code": errno,
        "error_message": slave_data["last_sql_error"],
        "binlog_lag": {"file_match": file_match, "position_diff": pos_diff},
        "needs_reimaging": reimaging,
    }


def compute_expected_repair_steps(diag, host, start_step):
    """Return (steps_list, next_step) for a single slave."""
    steps = []
    etype = diag["error_type"]
    if diag["needs_reimaging"]:
        steps.append({
            "host": host,
            "step": start_step,
            "action": "reimage_from_backup",
            "sql_command": "STOP SLAVE; RESET SLAVE ALL;",
        })
    elif etype in ("duplicate_key", "row_not_found"):
        steps.append({
            "host": host,
            "step": start_step,
            "action": "skip_error",
            "sql_command": "STOP SLAVE; SET GLOBAL sql_slave_skip_counter = 1; START SLAVE;",
        })
        steps.append({
            "host": host,
            "step": start_step + 1,
            "action": "verify_replication",
            "sql_command": "SHOW SLAVE STATUS\\G",
        })
    elif etype == "none":
        steps.append({
            "host": host,
            "step": start_step,
            "action": "start_slave",
            "sql_command": "START SLAVE;",
        })
    return steps, start_step + len(steps)


# ===================================================================
# TESTS — Primary output file existence and structure
# ===================================================================

class TestFileExistence:
    """Verify that required output files exist and are non-empty."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"

    def test_output_json_non_empty(self):
        assert os.path.getsize(OUTPUT_JSON) > 2, f"{OUTPUT_JSON} is empty or trivial"

    def test_repair_log_exists(self):
        assert os.path.isfile(REPAIR_LOG), f"{REPAIR_LOG} does not exist"

    def test_repair_log_non_empty(self):
        assert os.path.getsize(REPAIR_LOG) > 10, f"{REPAIR_LOG} is too short"


class TestOutputStructure:
    """Validate top-level keys and nested structure of output.json."""

    def test_valid_json(self):
        data = load_json(OUTPUT_JSON)
        assert data is not None, "output.json is not valid JSON"

    def test_top_level_keys(self):
        data = load_json(OUTPUT_JSON)
        for key in ("diagnosis", "repair_plan", "root_cause", "post_repair"):
            assert key in data, f"Missing top-level key: {key}"

    def test_diagnosis_has_both_slaves(self):
        data = load_json(OUTPUT_JSON)
        diag = data["diagnosis"]
        assert "slave1" in diag, "diagnosis missing slave1"
        assert "slave2" in diag, "diagnosis missing slave2"

    def test_diagnosis_slave_keys(self):
        data = load_json(OUTPUT_JSON)
        required = {
            "io_thread_ok", "sql_thread_ok", "error_type", "error_code",
            "error_message", "binlog_lag", "needs_reimaging",
        }
        for slave in ("slave1", "slave2"):
            actual = set(data["diagnosis"][slave].keys())
            missing = required - actual
            assert not missing, f"diagnosis.{slave} missing keys: {missing}"

    def test_binlog_lag_keys(self):
        data = load_json(OUTPUT_JSON)
        for slave in ("slave1", "slave2"):
            lag = data["diagnosis"][slave]["binlog_lag"]
            assert "file_match" in lag, f"diagnosis.{slave}.binlog_lag missing file_match"
            assert "position_diff" in lag, f"diagnosis.{slave}.binlog_lag missing position_diff"

    def test_repair_plan_is_list(self):
        data = load_json(OUTPUT_JSON)
        assert isinstance(data["repair_plan"], list), "repair_plan must be a list"

    def test_repair_plan_step_keys(self):
        data = load_json(OUTPUT_JSON)
        required = {"host", "step", "action", "sql_command"}
        for i, step in enumerate(data["repair_plan"]):
            missing = required - set(step.keys())
            assert not missing, f"repair_plan[{i}] missing keys: {missing}"

    def test_post_repair_keys(self):
        data = load_json(OUTPUT_JSON)
        pr = data["post_repair"]
        assert "slave1_ready" in pr, "post_repair missing slave1_ready"
        assert "slave2_ready" in pr, "post_repair missing slave2_ready"

    def test_root_cause_is_nonempty_string(self):
        data = load_json(OUTPUT_JSON)
        rc = data["root_cause"]
        assert isinstance(rc, str), "root_cause must be a string"
        assert len(rc.strip()) > 20, "root_cause is too short to be meaningful"


# ===================================================================
# TESTS — Diagnosis correctness for the primary input.json
# ===================================================================

class TestDiagnosisPrimaryInput:
    """Verify diagnosis values against the primary /app/input.json."""

    def _load(self):
        inp = load_json(INPUT_JSON)
        out = load_json(OUTPUT_JSON)
        return inp, out

    # -- slave1: errno 1062 (duplicate_key) --

    def test_slave1_io_thread(self):
        inp, out = self._load()
        assert out["diagnosis"]["slave1"]["io_thread_ok"] is True

    def test_slave1_sql_thread(self):
        _, out = self._load()
        assert out["diagnosis"]["slave1"]["sql_thread_ok"] is False

    def test_slave1_error_type(self):
        _, out = self._load()
        assert out["diagnosis"]["slave1"]["error_type"] == "duplicate_key"

    def test_slave1_error_code(self):
        _, out = self._load()
        assert out["diagnosis"]["slave1"]["error_code"] == 1062

    def test_slave1_binlog_file_match(self):
        _, out = self._load()
        # slave1 relay_master_log_file == master binlog_file (both mysql-bin.000042)
        assert out["diagnosis"]["slave1"]["binlog_lag"]["file_match"] is True

    def test_slave1_position_diff(self):
        inp, out = self._load()
        expected = inp["master"]["binlog_position"] - inp["slave1"]["exec_master_log_pos"]
        assert out["diagnosis"]["slave1"]["binlog_lag"]["position_diff"] == expected

    def test_slave1_needs_reimaging(self):
        _, out = self._load()
        # position_diff = 85432176 - 85431000 = 1176, error_type=duplicate_key → false
        assert out["diagnosis"]["slave1"]["needs_reimaging"] is False

    # -- slave2: errno 1236 (binlog_missing) --

    def test_slave2_io_thread(self):
        _, out = self._load()
        assert out["diagnosis"]["slave2"]["io_thread_ok"] is True

    def test_slave2_sql_thread(self):
        _, out = self._load()
        assert out["diagnosis"]["slave2"]["sql_thread_ok"] is False

    def test_slave2_error_type(self):
        _, out = self._load()
        assert out["diagnosis"]["slave2"]["error_type"] == "binlog_missing"

    def test_slave2_error_code(self):
        _, out = self._load()
        assert out["diagnosis"]["slave2"]["error_code"] == 1236

    def test_slave2_binlog_file_match(self):
        _, out = self._load()
        # slave2 relay_master_log_file=mysql-bin.000039 != master mysql-bin.000042
        assert out["diagnosis"]["slave2"]["binlog_lag"]["file_match"] is False

    def test_slave2_position_diff(self):
        inp, out = self._load()
        expected = inp["master"]["binlog_position"] - inp["slave2"]["exec_master_log_pos"]
        assert out["diagnosis"]["slave2"]["binlog_lag"]["position_diff"] == expected

    def test_slave2_needs_reimaging(self):
        _, out = self._load()
        # error_type=binlog_missing → always true
        assert out["diagnosis"]["slave2"]["needs_reimaging"] is True


# ===================================================================
# TESTS — Repair plan correctness for the primary input
# ===================================================================

class TestRepairPlanPrimaryInput:
    """Verify repair_plan against the primary input.json."""

    def _load(self):
        return load_json(OUTPUT_JSON)

    def test_total_step_count(self):
        data = self._load()
        # slave1: skip_error + verify = 2 steps; slave2: reimage = 1 step → 3 total
        assert len(data["repair_plan"]) == 3

    def test_steps_sequential_numbering(self):
        data = self._load()
        steps = [s["step"] for s in data["repair_plan"]]
        assert steps == list(range(1, len(steps) + 1)), f"Steps not sequential: {steps}"

    def test_slave1_steps_before_slave2(self):
        data = self._load()
        plan = data["repair_plan"]
        s1_indices = [i for i, s in enumerate(plan) if s["host"] == "slave1"]
        s2_indices = [i for i, s in enumerate(plan) if s["host"] == "slave2"]
        if s1_indices and s2_indices:
            assert max(s1_indices) < min(s2_indices), "slave1 steps must come before slave2"

    def test_slave1_skip_error_action(self):
        data = self._load()
        plan = data["repair_plan"]
        s1_steps = [s for s in plan if s["host"] == "slave1"]
        assert s1_steps[0]["action"] == "skip_error"
        assert "sql_slave_skip_counter" in s1_steps[0]["sql_command"]

    def test_slave1_verify_action(self):
        data = self._load()
        plan = data["repair_plan"]
        s1_steps = [s for s in plan if s["host"] == "slave1"]
        assert len(s1_steps) == 2
        assert s1_steps[1]["action"] == "verify_replication"
        assert "SHOW SLAVE STATUS" in s1_steps[1]["sql_command"]

    def test_slave2_reimage_action(self):
        data = self._load()
        plan = data["repair_plan"]
        s2_steps = [s for s in plan if s["host"] == "slave2"]
        assert len(s2_steps) == 1
        assert s2_steps[0]["action"] == "reimage_from_backup"
        assert "RESET SLAVE ALL" in s2_steps[0]["sql_command"]


# ===================================================================
# TESTS — Post-repair and root cause for primary input
# ===================================================================

class TestPostRepairPrimaryInput:

    def test_slave1_ready(self):
        data = load_json(OUTPUT_JSON)
        # slave1 does NOT need reimaging → ready
        assert data["post_repair"]["slave1_ready"] is True

    def test_slave2_not_ready(self):
        data = load_json(OUTPUT_JSON)
        # slave2 needs reimaging → not ready
        assert data["post_repair"]["slave2_ready"] is False


class TestRootCausePrimaryInput:

    def test_root_cause_mentions_duplicate_key(self):
        data = load_json(OUTPUT_JSON)
        rc = data["root_cause"].lower()
        assert "duplicate" in rc or "1062" in rc, \
            "root_cause should mention duplicate key or errno 1062"

    def test_root_cause_mentions_binlog(self):
        data = load_json(OUTPUT_JSON)
        rc = data["root_cause"].lower()
        assert "binlog" in rc or "1236" in rc or "binary log" in rc, \
            "root_cause should mention binlog issue or errno 1236"

    def test_repair_log_matches_root_cause(self):
        data = load_json(OUTPUT_JSON)
        with open(REPAIR_LOG, "r") as f:
            log_text = f.read().strip()
        assert log_text == data["root_cause"].strip(), \
            "REPAIR_LOG.txt content must match root_cause in output.json"


# ===================================================================
# TESTS — Type validation (catches hardcoded / dummy outputs)
# ===================================================================

class TestTypeValidation:
    """Ensure fields have correct types — catches lazy dummy outputs."""

    def test_boolean_fields(self):
        data = load_json(OUTPUT_JSON)
        for slave in ("slave1", "slave2"):
            d = data["diagnosis"][slave]
            assert isinstance(d["io_thread_ok"], bool), f"{slave}.io_thread_ok not bool"
            assert isinstance(d["sql_thread_ok"], bool), f"{slave}.sql_thread_ok not bool"
            assert isinstance(d["needs_reimaging"], bool), f"{slave}.needs_reimaging not bool"
            assert isinstance(d["binlog_lag"]["file_match"], bool), f"{slave}.file_match not bool"

    def test_integer_fields(self):
        data = load_json(OUTPUT_JSON)
        for slave in ("slave1", "slave2"):
            d = data["diagnosis"][slave]
            assert isinstance(d["error_code"], int), f"{slave}.error_code not int"
            assert isinstance(d["binlog_lag"]["position_diff"], int), f"{slave}.position_diff not int"

    def test_string_fields(self):
        data = load_json(OUTPUT_JSON)
        for slave in ("slave1", "slave2"):
            d = data["diagnosis"][slave]
            assert isinstance(d["error_type"], str), f"{slave}.error_type not str"
            assert isinstance(d["error_message"], str), f"{slave}.error_message not str"

    def test_post_repair_booleans(self):
        data = load_json(OUTPUT_JSON)
        assert isinstance(data["post_repair"]["slave1_ready"], bool)
        assert isinstance(data["post_repair"]["slave2_ready"], bool)

    def test_step_numbers_are_ints(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            assert isinstance(s["step"], int), f"step must be int, got {type(s['step'])}"


# ===================================================================
# TESTS — Cross-validation with helper functions (generalized logic)
# ===================================================================

class TestCrossValidation:
    """
    Re-derive expected output from input.json using helper functions
    and compare against the agent's output.json.  This catches subtle
    logic errors without being tied to a single hardcoded expectation.
    """

    def _expected(self):
        inp = load_json(INPUT_JSON)
        master = inp["master"]
        d1 = compute_expected_diagnosis(inp["slave1"], master)
        d2 = compute_expected_diagnosis(inp["slave2"], master)
        steps1, nxt = compute_expected_repair_steps(d1, "slave1", 1)
        steps2, _ = compute_expected_repair_steps(d2, "slave2", nxt)
        return d1, d2, steps1 + steps2

    def test_diagnosis_slave1_full(self):
        d1, _, _ = self._expected()
        out = load_json(OUTPUT_JSON)
        actual = out["diagnosis"]["slave1"]
        for key in d1:
            assert actual[key] == d1[key], f"slave1.{key}: expected {d1[key]}, got {actual[key]}"

    def test_diagnosis_slave2_full(self):
        _, d2, _ = self._expected()
        out = load_json(OUTPUT_JSON)
        actual = out["diagnosis"]["slave2"]
        for key in d2:
            assert actual[key] == d2[key], f"slave2.{key}: expected {d2[key]}, got {actual[key]}"

    def test_repair_plan_full(self):
        _, _, expected_plan = self._expected()
        out = load_json(OUTPUT_JSON)
        actual_plan = out["repair_plan"]
        assert len(actual_plan) == len(expected_plan), \
            f"Expected {len(expected_plan)} steps, got {len(actual_plan)}"
        for i, (exp, act) in enumerate(zip(expected_plan, actual_plan)):
            assert act["host"] == exp["host"], f"Step {i}: host mismatch"
            assert act["step"] == exp["step"], f"Step {i}: step number mismatch"
            assert act["action"] == exp["action"], f"Step {i}: action mismatch"
            assert act["sql_command"] == exp["sql_command"], f"Step {i}: sql_command mismatch"

    def test_post_repair_derived(self):
        d1, d2, _ = self._expected()
        out = load_json(OUTPUT_JSON)
        assert out["post_repair"]["slave1_ready"] == (not d1["needs_reimaging"])
        assert out["post_repair"]["slave2_ready"] == (not d2["needs_reimaging"])


# ===================================================================
# TESTS — Error type classification edge cases
# ===================================================================

class TestErrorTypeClassification:
    """Verify the error_type values match the classification rules."""

    def test_valid_error_types(self):
        data = load_json(OUTPUT_JSON)
        valid = {"duplicate_key", "row_not_found", "binlog_missing", "none", "other"}
        for slave in ("slave1", "slave2"):
            etype = data["diagnosis"][slave]["error_type"]
            assert etype in valid, f"{slave}.error_type '{etype}' not in valid set"

    def test_error_type_matches_code(self):
        """error_type must be consistent with error_code."""
        data = load_json(OUTPUT_JSON)
        mapping = {1062: "duplicate_key", 1032: "row_not_found", 1236: "binlog_missing", 0: "none"}
        for slave in ("slave1", "slave2"):
            code = data["diagnosis"][slave]["error_code"]
            etype = data["diagnosis"][slave]["error_type"]
            if code in mapping:
                assert etype == mapping[code], \
                    f"{slave}: code {code} should map to '{mapping[code]}', got '{etype}'"
            else:
                assert etype == "other", \
                    f"{slave}: unknown code {code} should map to 'other', got '{etype}'"


# ===================================================================
# TESTS — Reimaging threshold logic
# ===================================================================

class TestReimagingThreshold:
    """Verify the 1-billion-byte threshold and binlog_missing override."""

    def test_small_diff_no_reimaging(self):
        """slave1 in primary input has small position_diff → no reimaging."""
        data = load_json(OUTPUT_JSON)
        d = data["diagnosis"]["slave1"]
        assert d["binlog_lag"]["position_diff"] < 1_000_000_000
        assert d["needs_reimaging"] is False

    def test_binlog_missing_always_reimaging(self):
        """slave2 in primary input has binlog_missing → reimaging regardless of diff."""
        data = load_json(OUTPUT_JSON)
        d = data["diagnosis"]["slave2"]
        assert d["error_type"] == "binlog_missing"
        assert d["needs_reimaging"] is True


# ===================================================================
# TESTS — Repair plan action/sql_command consistency
# ===================================================================

class TestRepairPlanConsistency:
    """Verify that action values map to the correct sql_command strings."""

    def test_skip_error_sql(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            if s["action"] == "skip_error":
                assert "STOP SLAVE" in s["sql_command"]
                assert "sql_slave_skip_counter" in s["sql_command"]
                assert "START SLAVE" in s["sql_command"]

    def test_verify_replication_sql(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            if s["action"] == "verify_replication":
                assert "SHOW SLAVE STATUS" in s["sql_command"]

    def test_reimage_sql(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            if s["action"] == "reimage_from_backup":
                assert "STOP SLAVE" in s["sql_command"]
                assert "RESET SLAVE ALL" in s["sql_command"]

    def test_start_slave_sql(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            if s["action"] == "start_slave":
                assert "START SLAVE" in s["sql_command"]

    def test_valid_actions_only(self):
        data = load_json(OUTPUT_JSON)
        valid_actions = {"skip_error", "verify_replication", "reimage_from_backup", "start_slave"}
        for s in data["repair_plan"]:
            assert s["action"] in valid_actions, \
                f"Unknown action '{s['action']}'"

    def test_valid_hosts_only(self):
        data = load_json(OUTPUT_JSON)
        for s in data["repair_plan"]:
            assert s["host"] in ("slave1", "slave2"), \
                f"Unknown host '{s['host']}'"


# ===================================================================
# TESTS — Anti-cheat: detect hardcoded / empty / dummy outputs
# ===================================================================

class TestAntiCheat:
    """Detect lazy or hardcoded outputs."""

    def test_error_message_from_input(self):
        """error_message must come from the actual input, not be fabricated."""
        inp = load_json(INPUT_JSON)
        out = load_json(OUTPUT_JSON)
        for slave in ("slave1", "slave2"):
            expected_msg = inp[slave]["last_sql_error"]
            actual_msg = out["diagnosis"][slave]["error_message"]
            assert actual_msg == expected_msg, \
                f"{slave}.error_message doesn't match input"

    def test_position_diff_not_zero_for_lagging_slave(self):
        """slave2 is far behind — position_diff must not be 0."""
        out = load_json(OUTPUT_JSON)
        diff = out["diagnosis"]["slave2"]["binlog_lag"]["position_diff"]
        assert diff > 0, "slave2 position_diff should be positive (slave is behind)"

    def test_not_all_same_diagnosis(self):
        """slave1 and slave2 have different errors — diagnoses must differ."""
        out = load_json(OUTPUT_JSON)
        d1 = out["diagnosis"]["slave1"]
        d2 = out["diagnosis"]["slave2"]
        assert d1["error_type"] != d2["error_type"], \
            "slave1 and slave2 have different errors but got same error_type"

    def test_repair_plan_not_empty(self):
        """Primary input has errors on both slaves — plan must not be empty."""
        out = load_json(OUTPUT_JSON)
        assert len(out["repair_plan"]) >= 2, \
            "Both slaves have errors, repair_plan should have at least 2 steps"

