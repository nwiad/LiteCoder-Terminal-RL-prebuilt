"""
Tests for User Audit and SSH Hardening task.
Validates /app/audit_report.json and /app/sshd_config against instruction.md requirements.
"""

import json
import os
from datetime import datetime, timedelta

AUDIT_REPORT_PATH = "/app/audit_report.json"
SSHD_CONFIG_PATH = "/app/sshd_config"
INPUT_PATH = "/app/input.json"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    assert os.path.isfile(path), f"File not found: {path}"
    size = os.path.getsize(path)
    assert size > 0, f"File is empty: {path}"
    with open(path, "r") as f:
        return json.load(f)


def load_text(path):
    assert os.path.isfile(path), f"File not found: {path}"
    size = os.path.getsize(path)
    assert size > 0, f"File is empty: {path}"
    with open(path, "r") as f:
        return f.read()


def load_input():
    return load_json(INPUT_PATH)


def expected_classification(user):
    """Recompute expected classification from the rules in instruction.md."""
    uid = user["uid"]
    shell = user["shell"]
    if uid == 0:
        return "service"
    if uid < 1000:
        return "service"
    if shell.endswith("nologin") or shell.endswith("false"):
        return "service"
    return "human"


# ─── Test: File Existence & Basic Structure ────────────────────────────────────

class TestFileExistence:
    def test_audit_report_exists(self):
        assert os.path.isfile(AUDIT_REPORT_PATH), "audit_report.json not found"

    def test_sshd_config_exists(self):
        assert os.path.isfile(SSHD_CONFIG_PATH), "sshd_config not found"

    def test_audit_report_not_empty(self):
        assert os.path.getsize(AUDIT_REPORT_PATH) > 10, "audit_report.json is too small"

    def test_sshd_config_not_empty(self):
        assert os.path.getsize(SSHD_CONFIG_PATH) > 10, "sshd_config is too small"

    def test_audit_report_valid_json(self):
        load_json(AUDIT_REPORT_PATH)  # will raise on invalid JSON


# ─── Test: Audit Report Top-Level Structure ────────────────────────────────────

class TestAuditReportStructure:
    def test_top_level_keys(self):
        report = load_json(AUDIT_REPORT_PATH)
        required = {"audit_date", "total_users", "human_users", "service_users", "accounts"}
        assert required.issubset(set(report.keys())), (
            f"Missing keys: {required - set(report.keys())}"
        )

    def test_audit_date_format(self):
        report = load_json(AUDIT_REPORT_PATH)
        date_str = report["audit_date"]
        assert isinstance(date_str, str), "audit_date must be a string"
        # Must be YYYY-MM-DD
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed is not None

    def test_total_users_is_int(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert isinstance(report["total_users"], int)

    def test_human_users_is_int(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert isinstance(report["human_users"], int)

    def test_service_users_is_int(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert isinstance(report["service_users"], int)

    def test_accounts_is_list(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert isinstance(report["accounts"], list)


# ─── Test: User Counts ────────────────────────────────────────────────────────

class TestUserCounts:
    def test_total_users_matches_input(self):
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        assert report["total_users"] == len(inp["users"]), (
            f"total_users={report['total_users']} but input has {len(inp['users'])} users"
        )

    def test_total_users_equals_12(self):
        """Specific to the known input.json with 12 users."""
        report = load_json(AUDIT_REPORT_PATH)
        assert report["total_users"] == 12

    def test_human_plus_service_equals_total(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert report["human_users"] + report["service_users"] == report["total_users"], (
            "human_users + service_users must equal total_users"
        )

    def test_human_count(self):
        """Expected: jdoe, asmith, bwong, cjones = 4 human users."""
        report = load_json(AUDIT_REPORT_PATH)
        assert report["human_users"] == 4, f"Expected 4 human users, got {report['human_users']}"

    def test_service_count(self):
        """Expected: root, daemon, bin, sys, nobody, nginx, postgres, deploy = 8 service users."""
        report = load_json(AUDIT_REPORT_PATH)
        assert report["service_users"] == 8, f"Expected 8 service users, got {report['service_users']}"

    def test_accounts_length_matches_total(self):
        report = load_json(AUDIT_REPORT_PATH)
        assert len(report["accounts"]) == report["total_users"], (
            "accounts array length must match total_users"
        )


# ─── Test: Per-Account Classification ──────────────────────────────────────────

class TestAccountClassification:
    def test_account_fields_present(self):
        report = load_json(AUDIT_REPORT_PATH)
        required_fields = {"username", "uid", "classification", "action", "expiration_date", "shell_status"}
        for acct in report["accounts"]:
            missing = required_fields - set(acct.keys())
            assert not missing, f"Account {acct.get('username','?')} missing fields: {missing}"

    def test_classification_values_valid(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            assert acct["classification"] in ("human", "service"), (
                f"{acct['username']}: classification must be 'human' or 'service', got '{acct['classification']}'"
            )

    def test_each_user_classification(self):
        """Verify every user is classified correctly against the rules."""
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        for user, acct in zip(inp["users"], report["accounts"]):
            expected = expected_classification(user)
            assert acct["classification"] == expected, (
                f"{user['username']} (uid={user['uid']}, shell={user['shell']}): "
                f"expected '{expected}', got '{acct['classification']}'"
            )

    def test_root_is_service(self):
        report = load_json(AUDIT_REPORT_PATH)
        root = [a for a in report["accounts"] if a["username"] == "root"]
        assert len(root) == 1 and root[0]["classification"] == "service"

    def test_nobody_is_service(self):
        """nobody has uid=65534 (>=1000) but nologin shell -> service."""
        report = load_json(AUDIT_REPORT_PATH)
        nobody = [a for a in report["accounts"] if a["username"] == "nobody"]
        assert len(nobody) == 1 and nobody[0]["classification"] == "service"

    def test_deploy_is_service(self):
        """deploy has uid=1005 (>=1000) but nologin shell -> service."""
        report = load_json(AUDIT_REPORT_PATH)
        deploy = [a for a in report["accounts"] if a["username"] == "deploy"]
        assert len(deploy) == 1 and deploy[0]["classification"] == "service"

    def test_cjones_is_human(self):
        """cjones has uid=1004, shell=/bin/sh -> human (sh is NOT nologin/false)."""
        report = load_json(AUDIT_REPORT_PATH)
        cjones = [a for a in report["accounts"] if a["username"] == "cjones"]
        assert len(cjones) == 1 and cjones[0]["classification"] == "human"

    def test_postgres_is_service(self):
        """postgres has uid=998 and shell=/bin/false -> service."""
        report = load_json(AUDIT_REPORT_PATH)
        pg = [a for a in report["accounts"] if a["username"] == "postgres"]
        assert len(pg) == 1 and pg[0]["classification"] == "service"


# ─── Test: Actions, Expiration Dates, Shell Status ─────────────────────────────

class TestAccountActions:
    def test_human_action_is_expiration_set(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            if acct["classification"] == "human":
                assert acct["action"] == "expiration_set", (
                    f"{acct['username']}: human action must be 'expiration_set', got '{acct['action']}'"
                )

    def test_service_action_is_login_disabled(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            if acct["classification"] == "service":
                assert acct["action"] == "login_disabled", (
                    f"{acct['username']}: service action must be 'login_disabled', got '{acct['action']}'"
                )

    def test_human_expiration_date_is_90_days(self):
        report = load_json(AUDIT_REPORT_PATH)
        audit_date = datetime.strptime(report["audit_date"], "%Y-%m-%d").date()
        expected_exp = (audit_date + timedelta(days=90)).strftime("%Y-%m-%d")
        for acct in report["accounts"]:
            if acct["classification"] == "human":
                assert acct["expiration_date"] == expected_exp, (
                    f"{acct['username']}: expiration_date should be {expected_exp}, "
                    f"got {acct['expiration_date']}"
                )

    def test_service_expiration_date_is_null(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            if acct["classification"] == "service":
                assert acct["expiration_date"] is None, (
                    f"{acct['username']}: service expiration_date must be null, "
                    f"got {acct['expiration_date']}"
                )

    def test_human_expiration_date_format(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            if acct["classification"] == "human":
                assert isinstance(acct["expiration_date"], str)
                datetime.strptime(acct["expiration_date"], "%Y-%m-%d")

    def test_service_shell_status_nologin(self):
        report = load_json(AUDIT_REPORT_PATH)
        for acct in report["accounts"]:
            if acct["classification"] == "service":
                assert acct["shell_status"] == "nologin", (
                    f"{acct['username']}: service shell_status must be 'nologin', "
                    f"got '{acct['shell_status']}'"
                )

    def test_human_shell_status_is_original(self):
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        user_shells = {u["username"]: u["shell"] for u in inp["users"]}
        for acct in report["accounts"]:
            if acct["classification"] == "human":
                expected_shell = user_shells.get(acct["username"])
                assert acct["shell_status"] == expected_shell, (
                    f"{acct['username']}: human shell_status should be '{expected_shell}', "
                    f"got '{acct['shell_status']}'"
                )


# ─── Test: Account Ordering ───────────────────────────────────────────────────

class TestAccountOrdering:
    def test_accounts_same_order_as_input(self):
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        input_usernames = [u["username"] for u in inp["users"]]
        report_usernames = [a["username"] for a in report["accounts"]]
        assert report_usernames == input_usernames, (
            f"Account order must match input.\nExpected: {input_usernames}\nGot: {report_usernames}"
        )

    def test_accounts_uids_match_input(self):
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        for user, acct in zip(inp["users"], report["accounts"]):
            assert acct["uid"] == user["uid"], (
                f"{user['username']}: uid should be {user['uid']}, got {acct['uid']}"
            )


# ─── Test: SSH Config Hardening ───────────────────────────────────────────────

class TestSSHDConfig:
    def _parse_directives(self, config_text):
        """Parse sshd_config into a dict of key->value for non-comment, non-empty lines."""
        directives = {}
        for line in config_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                directives[parts[0]] = parts[1]
            elif len(parts) == 1:
                directives[parts[0]] = ""
        return directives

    def test_permit_root_login_no(self):
        config = load_text(SSHD_CONFIG_PATH)
        directives = self._parse_directives(config)
        assert directives.get("PermitRootLogin") == "no", (
            f"PermitRootLogin must be 'no', got '{directives.get('PermitRootLogin')}'"
        )

    def test_protocol_2(self):
        config = load_text(SSHD_CONFIG_PATH)
        directives = self._parse_directives(config)
        assert directives.get("Protocol") == "2", (
            f"Protocol must be '2', got '{directives.get('Protocol')}'"
        )

    def test_password_authentication_no(self):
        config = load_text(SSHD_CONFIG_PATH)
        directives = self._parse_directives(config)
        assert directives.get("PasswordAuthentication") == "no", (
            f"PasswordAuthentication must be 'no', got '{directives.get('PasswordAuthentication')}'"
        )

    def test_ends_with_newline(self):
        config = load_text(SSHD_CONFIG_PATH)
        assert config.endswith("\n"), "sshd_config must end with a newline"

    def test_no_duplicate_directives(self):
        config = load_text(SSHD_CONFIG_PATH)
        seen = {}
        for line in config.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(None, 1)
            if parts:
                key = parts[0]
                if key in seen:
                    assert False, f"Duplicate directive found: '{key}' on lines {seen[key]} and current"
                seen[key] = stripped


    def test_preserved_lines_from_original(self):
        """Non-hardened directives and comments from original must be preserved."""
        inp = load_input()
        config = load_text(SSHD_CONFIG_PATH)
        original = inp["sshd_config_original"]

        hardened_keys = {"PermitRootLogin", "Protocol", "PasswordAuthentication"}

        # Collect non-hardened, non-empty, non-comment lines from original
        original_preserved = []
        for line in original.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(None, 1)
            if parts and parts[0] not in hardened_keys:
                original_preserved.append(parts[0])

        # All those directive keys must still appear in the output
        output_directives = self._parse_directives(config)
        for key in original_preserved:
            assert key in output_directives, (
                f"Original directive '{key}' was not preserved in hardened config"
            )

    def test_hardened_directive_format(self):
        """Each hardened directive must be 'Key Value' with single space."""
        config = load_text(SSHD_CONFIG_PATH)
        lines = config.splitlines()
        hardened = {"PermitRootLogin": "no", "Protocol": "2", "PasswordAuthentication": "no"}
        for key, val in hardened.items():
            expected_line = f"{key} {val}"
            matching = [l for l in lines if l.strip().startswith(key)]
            assert len(matching) == 1, f"Expected exactly one line for {key}, found {len(matching)}"
            assert matching[0].strip() == expected_line, (
                f"Expected '{expected_line}', got '{matching[0].strip()}'"
            )

    def test_original_comments_preserved(self):
        """Comment lines from the original config should be preserved."""
        inp = load_input()
        config = load_text(SSHD_CONFIG_PATH)
        original = inp["sshd_config_original"]

        original_comments = [l.strip() for l in original.splitlines() if l.strip().startswith("#")]
        output_comments = [l.strip() for l in config.splitlines() if l.strip().startswith("#")]

        for comment in original_comments:
            assert comment in output_comments, (
                f"Original comment not preserved: '{comment}'"
            )


# ─── Test: Anti-Cheat / Consistency ───────────────────────────────────────────

class TestConsistency:
    def test_classification_counts_match_accounts(self):
        """Verify reported counts actually match the accounts array."""
        report = load_json(AUDIT_REPORT_PATH)
        actual_human = sum(1 for a in report["accounts"] if a["classification"] == "human")
        actual_service = sum(1 for a in report["accounts"] if a["classification"] == "service")
        assert report["human_users"] == actual_human, (
            f"human_users={report['human_users']} but counted {actual_human} in accounts"
        )
        assert report["service_users"] == actual_service, (
            f"service_users={report['service_users']} but counted {actual_service} in accounts"
        )

    def test_all_input_users_present(self):
        """Every user from input must appear in the report."""
        inp = load_input()
        report = load_json(AUDIT_REPORT_PATH)
        input_names = {u["username"] for u in inp["users"]}
        report_names = {a["username"] for a in report["accounts"]}
        assert input_names == report_names, (
            f"Missing users: {input_names - report_names}, Extra users: {report_names - input_names}"
        )

