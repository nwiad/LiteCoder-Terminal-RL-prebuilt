"""
Tests for LVM Storage Expansion Script task.

Validates:
1. /app/solution.sh exists and is executable
2. /app/output.json exists and is valid JSON with correct schema
3. JSON values are semantically correct (types, ranges, enums)
4. The script contains essential LVM operations (not just a hardcoded output generator)
5. The script has proper error handling and idempotency logic
"""

import os
import json
import stat

SOLUTION_SCRIPT = "/app/solution.sh"
OUTPUT_JSON = "/app/output.json"


# ─── Helpers ───

def load_output_json():
    """Load and parse output.json, returning the dict or None."""
    if not os.path.isfile(OUTPUT_JSON):
        return None
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    if not content:
        return None
    return json.loads(content)


def read_script():
    """Read solution.sh content."""
    if not os.path.isfile(SOLUTION_SCRIPT):
        return None
    with open(SOLUTION_SCRIPT, "r") as f:
        return f.read()


# ─── Test: Script file existence and permissions ───

def test_solution_script_exists():
    """solution.sh must exist at /app/solution.sh."""
    assert os.path.isfile(SOLUTION_SCRIPT), (
        f"Expected script at {SOLUTION_SCRIPT} but file does not exist"
    )


def test_solution_script_is_executable():
    """solution.sh must have executable permission."""
    assert os.path.isfile(SOLUTION_SCRIPT), f"{SOLUTION_SCRIPT} does not exist"
    mode = os.stat(SOLUTION_SCRIPT).st_mode
    assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, (
        f"{SOLUTION_SCRIPT} is not executable (mode: {oct(mode)})"
    )


def test_solution_script_is_bash():
    """solution.sh must be a bash script (shebang line)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    first_line = content.strip().split("\n")[0]
    assert first_line.startswith("#!"), "Script missing shebang line"
    assert "bash" in first_line or "sh" in first_line, (
        f"Script shebang does not reference bash/sh: {first_line}"
    )


# ─── Test: Output JSON existence and validity ───

def test_output_json_exists():
    """output.json must exist at /app/output.json."""
    assert os.path.isfile(OUTPUT_JSON), (
        f"Expected output at {OUTPUT_JSON} but file does not exist"
    )


def test_output_json_is_valid_json():
    """output.json must be parseable as valid JSON."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"output.json is not valid JSON: {e}"


def test_output_json_not_empty_object():
    """output.json must not be an empty object or array."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert isinstance(data, dict), "output.json root must be a JSON object"
    assert len(data) >= 3, (
        f"output.json has only {len(data)} keys, expected at least 6"
    )


# ─── Test: Top-level status field ───

def test_status_field_exists():
    """output.json must have a 'status' field."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "status" in data, "output.json missing 'status' field"


def test_status_is_success():
    """status must be 'success' for a successful run."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert data.get("status") == "success", (
        f"Expected status 'success', got '{data.get('status')}'"
    )


# ─── Test: partition section ───

def test_partition_section_exists():
    """output.json must have a 'partition' section."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "partition" in data, "output.json missing 'partition' section"
    assert isinstance(data["partition"], dict), "'partition' must be a dict"


def test_partition_device():
    """partition.device must reference /dev/sdb (sdb or sdb1)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    part = data.get("partition", {})
    device = part.get("device", "")
    assert isinstance(device, str) and len(device) > 0, "partition.device is missing or empty"
    assert "/dev/sdb" in device, (
        f"partition.device should reference /dev/sdb*, got '{device}'"
    )


def test_partition_type():
    """partition.type must be '8e' (Linux LVM type code)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    part = data.get("partition", {})
    ptype = str(part.get("type", "")).strip().lower()
    assert ptype == "8e", (
        f"partition.type should be '8e', got '{ptype}'"
    )


# ─── Test: pv section ───

def test_pv_section_exists():
    """output.json must have a 'pv' section."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "pv" in data, "output.json missing 'pv' section"
    assert isinstance(data["pv"], dict), "'pv' must be a dict"


def test_pv_device():
    """pv.device must reference /dev/sdb (sdb or sdb1)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    pv = data.get("pv", {})
    device = pv.get("device", "")
    assert isinstance(device, str) and "/dev/sdb" in device, (
        f"pv.device should reference /dev/sdb*, got '{device}'"
    )


def test_pv_vg_name():
    """pv.vg_name must be a non-empty string."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    pv = data.get("pv", {})
    vg_name = pv.get("vg_name", "")
    assert isinstance(vg_name, str) and len(vg_name.strip()) > 0, (
        f"pv.vg_name must be a non-empty string, got '{vg_name}'"
    )


# ─── Test: vg section ───

def test_vg_section_exists():
    """output.json must have a 'vg' section."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "vg" in data, "output.json missing 'vg' section"
    assert isinstance(data["vg"], dict), "'vg' must be a dict"


def test_vg_name_matches_pv():
    """vg.name must match pv.vg_name (consistency check)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    vg_name = data.get("vg", {}).get("name", "")
    pv_vg_name = data.get("pv", {}).get("vg_name", "")
    assert isinstance(vg_name, str) and len(vg_name.strip()) > 0, (
        "vg.name must be a non-empty string"
    )
    assert vg_name.strip() == pv_vg_name.strip(), (
        f"vg.name ('{vg_name}') must match pv.vg_name ('{pv_vg_name}')"
    )


def test_vg_pv_count_is_integer():
    """vg.pv_count must be an integer."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    pv_count = data.get("vg", {}).get("pv_count")
    assert isinstance(pv_count, int), (
        f"vg.pv_count must be an integer, got {type(pv_count).__name__}: {pv_count}"
    )


def test_vg_pv_count_at_least_2():
    """After adding /dev/sdb, the VG must have at least 2 PVs."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    pv_count = data.get("vg", {}).get("pv_count", 0)
    assert isinstance(pv_count, int) and pv_count >= 2, (
        f"vg.pv_count should be >= 2 after expansion, got {pv_count}"
    )


# ─── Test: lv section ───

def test_lv_section_exists():
    """output.json must have an 'lv' section."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "lv" in data, "output.json missing 'lv' section"
    assert isinstance(data["lv"], dict), "'lv' must be a dict"


def test_lv_path_is_valid():
    """lv.path must be a non-empty string starting with /dev/."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    lv = data.get("lv", {})
    lv_path = lv.get("path", "")
    assert isinstance(lv_path, str) and lv_path.startswith("/dev/"), (
        f"lv.path must start with /dev/, got '{lv_path}'"
    )


def test_lv_size_bytes_is_integer():
    """lv.size_bytes must be an integer."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    size = data.get("lv", {}).get("size_bytes")
    assert isinstance(size, int), (
        f"lv.size_bytes must be an integer, got {type(size).__name__}: {size}"
    )


def test_lv_size_bytes_is_positive():
    """lv.size_bytes must be a positive value (LV has real size)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    size = data.get("lv", {}).get("size_bytes", 0)
    assert isinstance(size, int) and size > 0, (
        f"lv.size_bytes must be positive, got {size}"
    )


def test_lv_size_bytes_includes_expansion():
    """lv.size_bytes should reflect the 10GB expansion (at least ~5GB total)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    size = data.get("lv", {}).get("size_bytes", 0)
    # The added disk is 10GB. The LV should be at least 5GB after expansion.
    min_expected = 5 * 1024 * 1024 * 1024  # 5 GiB
    assert isinstance(size, int) and size >= min_expected, (
        f"lv.size_bytes should be >= 5GiB ({min_expected}) after 10GB expansion, got {size}"
    )


# ─── Test: filesystem section ───

def test_filesystem_section_exists():
    """output.json must have a 'filesystem' section."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    assert "filesystem" in data, "output.json missing 'filesystem' section"
    assert isinstance(data["filesystem"], dict), "'filesystem' must be a dict"


def test_filesystem_mount_point():
    """filesystem.mount_point must be '/'."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    fs = data.get("filesystem", {})
    mp = fs.get("mount_point", "")
    assert mp == "/", f"filesystem.mount_point must be '/', got '{mp}'"


def test_filesystem_type():
    """filesystem.type must be 'ext4' or 'xfs'."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    fs = data.get("filesystem", {})
    fs_type = fs.get("type", "").strip()
    assert fs_type in ("ext4", "xfs", "ext3", "ext2"), (
        f"filesystem.type must be ext4/xfs/ext3/ext2, got '{fs_type}'"
    )


def test_filesystem_total_size_kb_is_integer():
    """filesystem.total_size_kb must be an integer."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    size_kb = data.get("filesystem", {}).get("total_size_kb")
    assert isinstance(size_kb, int), (
        f"filesystem.total_size_kb must be an integer, got {type(size_kb).__name__}: {size_kb}"
    )


def test_filesystem_total_size_kb_is_positive():
    """filesystem.total_size_kb must be positive."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    size_kb = data.get("filesystem", {}).get("total_size_kb", 0)
    assert isinstance(size_kb, int) and size_kb > 0, (
        f"filesystem.total_size_kb must be positive, got {size_kb}"
    )


# ─── Test: Cross-field consistency ───

def test_partition_device_matches_pv_device():
    """partition.device and pv.device should be consistent (both reference sdb)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    part_dev = data.get("partition", {}).get("device", "")
    pv_dev = data.get("pv", {}).get("device", "")
    assert part_dev == pv_dev, (
        f"partition.device ('{part_dev}') should match pv.device ('{pv_dev}')"
    )


def test_lv_size_bytes_consistent_with_fs_size_kb():
    """LV size in bytes should be >= filesystem size in KB * 1024 (FS fits inside LV)."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    lv_bytes = data.get("lv", {}).get("size_bytes", 0)
    fs_kb = data.get("filesystem", {}).get("total_size_kb", 0)
    if isinstance(lv_bytes, int) and isinstance(fs_kb, int) and lv_bytes > 0 and fs_kb > 0:
        fs_bytes = fs_kb * 1024
        # LV must be >= filesystem (filesystem lives inside the LV)
        # Allow small tolerance for metadata overhead
        assert lv_bytes >= fs_bytes * 0.8, (
            f"LV size ({lv_bytes} bytes) should be >= ~80% of FS size "
            f"({fs_bytes} bytes). LV contains the filesystem."
        )


# ─── Test: All required top-level keys present ───

def test_all_required_sections_present():
    """output.json must have all 6 required top-level keys."""
    data = load_output_json()
    assert data is not None, "output.json missing or empty"
    required_keys = {"partition", "pv", "vg", "lv", "filesystem", "status"}
    missing = required_keys - set(data.keys())
    assert len(missing) == 0, (
        f"output.json missing required top-level keys: {missing}"
    )


# ─── Test: Script content validation (anti-hardcoding checks) ───

def test_script_uses_pvcreate():
    """Script must use pvcreate to initialize the physical volume."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    assert "pvcreate" in content, (
        "Script must use 'pvcreate' to create a physical volume"
    )


def test_script_uses_vgextend():
    """Script must use vgextend to add PV to the volume group."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    assert "vgextend" in content, (
        "Script must use 'vgextend' to extend the volume group"
    )


def test_script_uses_lvextend():
    """Script must use lvextend to extend the logical volume."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    assert "lvextend" in content, (
        "Script must use 'lvextend' to extend the logical volume"
    )


def test_script_handles_filesystem_resize():
    """Script must handle filesystem resize (resize2fs or xfs_growfs)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    has_resize2fs = "resize2fs" in content
    has_xfs_growfs = "xfs_growfs" in content
    assert has_resize2fs or has_xfs_growfs, (
        "Script must use 'resize2fs' and/or 'xfs_growfs' to resize the filesystem"
    )


def test_script_detects_vg_name():
    """Script must auto-detect VG name (uses vgs or vgdisplay, not hardcoded)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    # Must query VG info dynamically
    has_vgs = "vgs" in content
    has_vgdisplay = "vgdisplay" in content
    has_vgscan = "vgscan" in content
    assert has_vgs or has_vgdisplay or has_vgscan, (
        "Script must use 'vgs', 'vgdisplay', or 'vgscan' to detect VG name"
    )


def test_script_detects_lv_path():
    """Script must auto-detect LV path (uses lvs, lvdisplay, or df)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    has_lvs = "lvs" in content
    has_lvdisplay = "lvdisplay" in content
    has_df = "df" in content
    assert has_lvs or has_lvdisplay or has_df, (
        "Script must use 'lvs', 'lvdisplay', or 'df' to detect LV path"
    )


def test_script_writes_output_json():
    """Script must write to /app/output.json."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    assert "output.json" in content, (
        "Script must reference 'output.json' for writing the report"
    )


def test_script_has_error_handling():
    """Script must have error handling (check for /dev/sdb existence)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    # Must check if /dev/sdb exists
    has_sdb_check = "/dev/sdb" in content
    has_error_status = '"error"' in content or "'error'" in content or "error" in content.lower()
    assert has_sdb_check and has_error_status, (
        "Script must check for /dev/sdb existence and handle errors"
    )


def test_script_has_sdb_reference():
    """Script must reference /dev/sdb as the input disk."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    assert "/dev/sdb" in content, (
        "Script must reference '/dev/sdb' as the disk to add"
    )


def test_script_not_trivially_short():
    """Script must be non-trivial (not just echoing hardcoded JSON)."""
    content = read_script()
    assert content is not None, f"{SOLUTION_SCRIPT} does not exist or is empty"
    lines = [l for l in content.strip().split("\n") if l.strip() and not l.strip().startswith("#")]
    assert len(lines) >= 15, (
        f"Script has only {len(lines)} non-comment lines. "
        "A real LVM expansion script requires substantial logic."
    )
