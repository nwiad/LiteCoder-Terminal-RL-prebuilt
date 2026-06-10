"""
Tests for Qt5 Multi-Version Build Matrix task.

Validates:
- Demo app project structure
- Build script existence and executability
- Build log JSON schema and consistency
- Tarball existence, naming, structure, and size
- Launch script (run.sh) correctness inside tarballs
"""

import os
import json
import tarfile
import stat
import subprocess

# ── Constants ──

APP_DIR = "/app"
DEMO_DIR = os.path.join(APP_DIR, "demo-app")
BUILD_SCRIPT = os.path.join(APP_DIR, "build.sh")
BUILD_LOG = os.path.join(APP_DIR, "build-log.json")
DIST_DIR = os.path.join(APP_DIR, "dist")

QT_VERSIONS = ["5.12.12", "5.15.2", "5.15.10"]

TARBALL_NAMES = {
    v: f"research-app-qt5-{v}-linux-x86_64.tar.gz" for v in QT_VERSIONS
}

MAX_COMBINED_SIZE_BYTES = 300 * 1024 * 1024  # 300 MB


# ── Helpers ──

def _load_build_log():
    """Load and return the build log JSON."""
    assert os.path.isfile(BUILD_LOG), f"Build log not found at {BUILD_LOG}"
    with open(BUILD_LOG, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "Build log is empty or trivial"
    data = json.loads(content)
    return data


def _tarball_path(version):
    return os.path.join(DIST_DIR, TARBALL_NAMES[version])


def _list_tarball_members(tarball_path):
    """Return set of member names in a tarball."""
    with tarfile.open(tarball_path, "r:gz") as tf:
        return set(tf.getnames())


def _extract_tarball_to(tarball_path, dest):
    """Extract tarball to destination directory."""
    with tarfile.open(tarball_path, "r:gz") as tf:
        tf.extractall(dest)


# ══════════════════════════════════════════════════════════════
# 1. Demo App Project
# ══════════════════════════════════════════════════════════════

def test_demo_app_directory_exists():
    assert os.path.isdir(DEMO_DIR), f"Demo app directory not found at {DEMO_DIR}"


def test_demo_app_pro_file_exists():
    pro_file = os.path.join(DEMO_DIR, "demo-app.pro")
    assert os.path.isfile(pro_file), f".pro file not found at {pro_file}"


def test_demo_app_pro_no_hardcoded_qt_paths():
    """The .pro file must not hardcode absolute paths to any Qt installation."""
    pro_file = os.path.join(DEMO_DIR, "demo-app.pro")
    assert os.path.isfile(pro_file), ".pro file missing"
    with open(pro_file, "r") as f:
        content = f.read()
    for v in QT_VERSIONS:
        assert f"/opt/qt5-{v}" not in content, (
            f".pro file hardcodes path to /opt/qt5-{v}"
        )
    # Also check generic /opt/qt patterns
    assert "/opt/qt" not in content.lower(), (
        ".pro file appears to hardcode a Qt installation path"
    )


def test_demo_app_has_source_files():
    """At least one .cpp source file must exist."""
    cpp_files = [
        f for f in os.listdir(DEMO_DIR)
        if f.endswith(".cpp") or f.endswith(".cxx") or f.endswith(".cc")
    ]
    assert len(cpp_files) > 0, "No C++ source files found in demo-app/"


# ══════════════════════════════════════════════════════════════
# 2. Build Script
# ══════════════════════════════════════════════════════════════

def test_build_script_exists():
    assert os.path.isfile(BUILD_SCRIPT), f"Build script not found at {BUILD_SCRIPT}"


def test_build_script_is_executable():
    assert os.path.isfile(BUILD_SCRIPT), "Build script missing"
    mode = os.stat(BUILD_SCRIPT).st_mode
    assert mode & stat.S_IXUSR, "build.sh is not executable (missing user execute bit)"


def test_build_script_is_bash():
    """Build script should have a bash shebang."""
    with open(BUILD_SCRIPT, "r") as f:
        first_line = f.readline().strip()
    assert first_line.startswith("#!"), "build.sh missing shebang"
    assert "bash" in first_line or "sh" in first_line, (
        f"build.sh shebang doesn't reference bash/sh: {first_line}"
    )


# ══════════════════════════════════════════════════════════════
# 3. Build Log JSON
# ══════════════════════════════════════════════════════════════

def test_build_log_exists():
    assert os.path.isfile(BUILD_LOG), f"Build log not found at {BUILD_LOG}"


def test_build_log_is_valid_json():
    data = _load_build_log()
    assert isinstance(data, dict), "Build log root must be a JSON object"


def test_build_log_has_builds_key():
    data = _load_build_log()
    assert "builds" in data, "Build log missing 'builds' key"
    assert isinstance(data["builds"], list), "'builds' must be a list"


def test_build_log_has_three_entries():
    data = _load_build_log()
    assert len(data["builds"]) == 3, (
        f"Expected 3 build entries, got {len(data['builds'])}"
    )


def test_build_log_covers_all_versions():
    data = _load_build_log()
    logged_versions = {b["qt_version"] for b in data["builds"]}
    expected = set(QT_VERSIONS)
    assert logged_versions == expected, (
        f"Build log versions {logged_versions} != expected {expected}"
    )


def test_build_log_entry_schema():
    """Each build entry must have the required keys with correct types."""
    data = _load_build_log()
    required_keys = {
        "qt_version": str,
        "status": str,
        "qt_prefix": str,
        "binary_path": str,
        "tarball_path": str,
        "tarball_size_bytes": (int, float),
        "dynamic_qt_deps": list,
    }
    for entry in data["builds"]:
        for key, expected_type in required_keys.items():
            assert key in entry, f"Build entry missing key '{key}'"
            assert isinstance(entry[key], expected_type), (
                f"Key '{key}' has type {type(entry[key]).__name__}, "
                f"expected {expected_type}"
            )


def test_build_log_status_values():
    data = _load_build_log()
    for entry in data["builds"]:
        assert entry["status"] in ("success", "failure"), (
            f"Invalid status '{entry['status']}' for Qt {entry['qt_version']}"
        )


def test_build_log_all_success():
    """All three builds should succeed."""
    data = _load_build_log()
    for entry in data["builds"]:
        assert entry["status"] == "success", (
            f"Build for Qt {entry['qt_version']} has status '{entry['status']}', expected 'success'"
        )


def test_build_log_qt_prefix_format():
    data = _load_build_log()
    for entry in data["builds"]:
        v = entry["qt_version"]
        expected_prefix = f"/opt/qt5-{v}"
        assert entry["qt_prefix"] == expected_prefix, (
            f"qt_prefix for {v} is '{entry['qt_prefix']}', expected '{expected_prefix}'"
        )


def test_build_log_tarball_sizes_match_actual():
    """tarball_size_bytes must match the actual file size on disk."""
    data = _load_build_log()
    for entry in data["builds"]:
        if entry["status"] != "success":
            continue
        tarball = entry["tarball_path"]
        assert os.path.isfile(tarball), f"Tarball not found: {tarball}"
        actual_size = os.path.getsize(tarball)
        logged_size = int(entry["tarball_size_bytes"])
        assert logged_size == actual_size, (
            f"Tarball size mismatch for Qt {entry['qt_version']}: "
            f"logged={logged_size}, actual={actual_size}"
        )


def test_build_log_total_size_is_sum():
    data = _load_build_log()
    assert "total_tarball_size_bytes" in data, "Missing 'total_tarball_size_bytes'"
    individual_sum = sum(int(b["tarball_size_bytes"]) for b in data["builds"])
    total = int(data["total_tarball_size_bytes"])
    assert total == individual_sum, (
        f"total_tarball_size_bytes ({total}) != sum of individual sizes ({individual_sum})"
    )


def test_build_log_dynamic_deps_are_strings():
    data = _load_build_log()
    for entry in data["builds"]:
        deps = entry["dynamic_qt_deps"]
        for dep in deps:
            assert isinstance(dep, str), (
                f"dynamic_qt_deps entry is not a string: {dep}"
            )


# ══════════════════════════════════════════════════════════════
# 4. Tarballs — Existence, Naming, Size
# ══════════════════════════════════════════════════════════════

def test_dist_directory_exists():
    assert os.path.isdir(DIST_DIR), f"dist/ directory not found at {DIST_DIR}"


def test_all_tarballs_exist():
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        assert os.path.isfile(path), f"Tarball missing: {path}"


def test_tarballs_are_valid_gzip():
    """Each tarball must be a valid gzip tar archive."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        assert tarfile.is_tarfile(path), f"{path} is not a valid tar file"
        with tarfile.open(path, "r:gz") as tf:
            members = tf.getnames()
            assert len(members) > 0, f"Tarball for Qt {v} is empty"


def test_tarballs_not_empty_size():
    """Each tarball must have non-trivial size (> 1KB)."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        assert size > 1024, (
            f"Tarball for Qt {v} is suspiciously small: {size} bytes"
        )


def test_combined_tarball_size_under_300mb():
    total = 0
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if os.path.isfile(path):
            total += os.path.getsize(path)
    assert total < MAX_COMBINED_SIZE_BYTES, (
        f"Combined tarball size {total} bytes exceeds 300 MB limit"
    )


# ══════════════════════════════════════════════════════════════
# 5. Tarball Internal Structure
# ══════════════════════════════════════════════════════════════

def _normalize_members(members):
    """Normalize tarball member paths (strip leading ./ or /)."""
    normalized = set()
    for m in members:
        m = m.lstrip("./")
        if m:
            normalized.add(m)
    return normalized


def _has_path_prefix(normalized_members, prefix):
    """Check if any member starts with the given prefix."""
    prefix = prefix.strip("/")
    for m in normalized_members:
        if m == prefix or m.startswith(prefix + "/"):
            return True
    return False


def test_tarball_contains_bin_directory():
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _normalize_members(_list_tarball_members(path))
        assert _has_path_prefix(members, "bin"), (
            f"Tarball for Qt {v} missing bin/ directory"
        )


def test_tarball_contains_lib_directory():
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _normalize_members(_list_tarball_members(path))
        assert _has_path_prefix(members, "lib"), (
            f"Tarball for Qt {v} missing lib/ directory"
        )


def test_tarball_contains_plugins_platforms():
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _normalize_members(_list_tarball_members(path))
        assert _has_path_prefix(members, "plugins/platforms") or \
               _has_path_prefix(members, "plugins"), (
            f"Tarball for Qt {v} missing plugins/platforms/ directory"
        )


def test_tarball_contains_run_sh():
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _normalize_members(_list_tarball_members(path))
        assert "run.sh" in members, (
            f"Tarball for Qt {v} missing run.sh at root"
        )


def test_tarball_contains_binary_in_bin():
    """bin/ must contain at least one file (the compiled binary)."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _normalize_members(_list_tarball_members(path))
        bin_files = [m for m in members if m.startswith("bin/") and m != "bin/"]
        assert len(bin_files) > 0, (
            f"Tarball for Qt {v} has empty bin/ directory"
        )


# ══════════════════════════════════════════════════════════════
# 6. Launch Script (run.sh) Content Validation
# ══════════════════════════════════════════════════════════════

def _extract_run_sh_content(version):
    """Extract and return the content of run.sh from a tarball."""
    path = _tarball_path(version)
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            name = member.name.lstrip("./")
            if name == "run.sh":
                f = tf.extractfile(member)
                if f:
                    return f.read().decode("utf-8", errors="replace")
    return None


def test_run_sh_sets_ld_library_path():
    """run.sh must set LD_LIBRARY_PATH to the bundled lib/ directory."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        content = _extract_run_sh_content(v)
        assert content is not None, f"Could not read run.sh from tarball for Qt {v}"
        assert "LD_LIBRARY_PATH" in content, (
            f"run.sh for Qt {v} does not set LD_LIBRARY_PATH"
        )


def test_run_sh_sets_qt_plugin_path():
    """run.sh must set QT_PLUGIN_PATH to the bundled plugins/ directory."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        content = _extract_run_sh_content(v)
        assert content is not None, f"Could not read run.sh from tarball for Qt {v}"
        assert "QT_PLUGIN_PATH" in content, (
            f"run.sh for Qt {v} does not set QT_PLUGIN_PATH"
        )


def test_run_sh_forwards_arguments():
    """run.sh must forward command-line arguments (uses $@ or "$@")."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        content = _extract_run_sh_content(v)
        assert content is not None, f"Could not read run.sh from tarball for Qt {v}"
        # Check for argument forwarding patterns
        assert '$@' in content or '${@}' in content or '"$@"' in content, (
            f"run.sh for Qt {v} does not appear to forward arguments ($@)"
        )


def test_run_sh_is_executable_in_tarball():
    """run.sh must have executable permission in the tarball."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        with tarfile.open(path, "r:gz") as tf:
            for member in tf.getmembers():
                name = member.name.lstrip("./")
                if name == "run.sh":
                    mode = member.mode
                    assert mode & stat.S_IXUSR, (
                        f"run.sh in tarball for Qt {v} is not executable"
                    )
                    break


def test_run_sh_references_lib_and_plugins():
    """run.sh must reference both lib/ and plugins/ directories."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        content = _extract_run_sh_content(v)
        assert content is not None
        assert "lib" in content, (
            f"run.sh for Qt {v} doesn't reference lib/ directory"
        )
        assert "plugins" in content or "plugin" in content, (
            f"run.sh for Qt {v} doesn't reference plugins/ directory"
        )


# ══════════════════════════════════════════════════════════════
# 7. No Intermediate Build Artifacts in Tarballs
# ══════════════════════════════════════════════════════════════

def test_no_object_files_in_tarballs():
    """Tarballs must not contain .o files (intermediate build artifacts)."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _list_tarball_members(path)
        obj_files = [m for m in members if m.endswith(".o")]
        assert len(obj_files) == 0, (
            f"Tarball for Qt {v} contains object files: {obj_files}"
        )


def test_no_moc_files_in_tarballs():
    """Tarballs must not contain moc_*.cpp files."""
    for v in QT_VERSIONS:
        path = _tarball_path(v)
        if not os.path.isfile(path):
            continue
        members = _list_tarball_members(path)
        moc_files = [m for m in members if "moc_" in os.path.basename(m) and m.endswith(".cpp")]
        assert len(moc_files) == 0, (
            f"Tarball for Qt {v} contains moc output files: {moc_files}"
        )


# ══════════════════════════════════════════════════════════════
# 8. Tarball Naming Consistency with Build Log
# ══════════════════════════════════════════════════════════════

def test_build_log_tarball_paths_match_dist():
    """Tarball paths in build log must point to files under /app/dist/."""
    data = _load_build_log()
    for entry in data["builds"]:
        if entry["status"] != "success":
            continue
        tp = entry["tarball_path"]
        assert tp.startswith("/app/dist/") or tp.startswith("dist/"), (
            f"Tarball path '{tp}' for Qt {entry['qt_version']} "
            f"is not under /app/dist/"
        )
        # The actual file must exist
        assert os.path.isfile(tp), (
            f"Tarball path in build log does not exist: {tp}"
        )


def test_tarball_names_follow_convention():
    """Tarball filenames must match research-app-qt5-<VER>-linux-x86_64.tar.gz."""
    for v in QT_VERSIONS:
        expected_name = f"research-app-qt5-{v}-linux-x86_64.tar.gz"
        path = os.path.join(DIST_DIR, expected_name)
        assert os.path.isfile(path), (
            f"Expected tarball with exact name '{expected_name}' in {DIST_DIR}"
        )
