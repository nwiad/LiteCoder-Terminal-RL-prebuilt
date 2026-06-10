"""
Tests for the Build Python 3.12 Scientific Environment task.

Verifies:
- Python 3.12 binary exists at /opt/py312/bin/python3.12 and is executable
- pip3 exists at /opt/py312/bin/pip3 and is executable
- Python version output starts with "Python 3.12"
- numpy, scipy, matplotlib are importable by the custom interpreter
- Each library prints a valid version string
- Smoke test PNG exists at /opt/py312/smoke_test_output.png and is valid
- Tarball exists at /app/py312-scientific.tar.gz, is valid, and contains expected entries
- OpenBLAS is installed under /opt/py312
- The environment is self-contained under /opt/py312
"""

import os
import subprocess
import tarfile

# ── Constants ──────────────────────────────────────────────────────────────

PREFIX = "/opt/py312"
PYTHON_BIN = os.path.join(PREFIX, "bin", "python3.12")
PIP_BIN = os.path.join(PREFIX, "bin", "pip3")
SMOKE_PNG = os.path.join(PREFIX, "smoke_test_output.png")
TARBALL = "/app/py312-scientific.tar.gz"


# ── Helpers ────────────────────────────────────────────────────────────────

def run_python(code, timeout=30):
    """Run a snippet with the custom Python interpreter and return stdout."""
    result = subprocess.run(
        [PYTHON_BIN, "-c", code],
        capture_output=True, text=True, timeout=timeout,
        env={
            **os.environ,
            "LD_LIBRARY_PATH": f"{PREFIX}/lib:" + os.environ.get("LD_LIBRARY_PATH", ""),
        },
    )
    return result


def is_valid_png(path):
    """Check PNG magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header[:8] == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
# 1. Python binary existence and executability
# ══════════════════════════════════════════════════════════════════════════

def test_python_binary_exists():
    """Python 3.12 binary must exist at the expected path."""
    assert os.path.isfile(PYTHON_BIN), f"Python binary not found at {PYTHON_BIN}"


def test_python_binary_executable():
    """Python 3.12 binary must be executable."""
    assert os.access(PYTHON_BIN, os.X_OK), f"{PYTHON_BIN} is not executable"


def test_pip_binary_exists():
    """pip3 binary must exist at the expected path."""
    assert os.path.isfile(PIP_BIN), f"pip3 binary not found at {PIP_BIN}"


def test_pip_binary_executable():
    """pip3 binary must be executable."""
    assert os.access(PIP_BIN, os.X_OK), f"{PIP_BIN} is not executable"


# ══════════════════════════════════════════════════════════════════════════
# 2. Python version check
# ══════════════════════════════════════════════════════════════════════════

def test_python_version():
    """python3.12 --version must output 'Python 3.12.x'."""
    result = subprocess.run(
        [PYTHON_BIN, "--version"],
        capture_output=True, text=True, timeout=10,
        env={
            **os.environ,
            "LD_LIBRARY_PATH": f"{PREFIX}/lib:" + os.environ.get("LD_LIBRARY_PATH", ""),
        },
    )
    assert result.returncode == 0, f"python3.12 --version failed: {result.stderr}"
    version_output = result.stdout.strip() + result.stderr.strip()
    assert version_output.startswith("Python 3.12"), (
        f"Expected version starting with 'Python 3.12', got: '{version_output}'"
    )


# ══════════════════════════════════════════════════════════════════════════
# 3. Library import tests — numpy
# ══════════════════════════════════════════════════════════════════════════

def test_numpy_importable():
    """numpy must be importable by the custom interpreter."""
    result = run_python("import numpy; print(numpy.__version__)")
    assert result.returncode == 0, f"Failed to import numpy: {result.stderr}"


def test_numpy_version_string():
    """numpy version must be a non-empty dotted version string."""
    result = run_python("import numpy; print(numpy.__version__)")
    version = result.stdout.strip()
    assert len(version) > 0, "numpy version string is empty"
    # Version should contain at least one dot (e.g. "1.26.2")
    assert "." in version, f"numpy version doesn't look like a version: '{version}'"


# ══════════════════════════════════════════════════════════════════════════
# 4. Library import tests — scipy
# ══════════════════════════════════════════════════════════════════════════

def test_scipy_importable():
    """scipy must be importable by the custom interpreter."""
    result = run_python("import scipy; print(scipy.__version__)")
    assert result.returncode == 0, f"Failed to import scipy: {result.stderr}"


def test_scipy_version_string():
    """scipy version must be a non-empty dotted version string."""
    result = run_python("import scipy; print(scipy.__version__)")
    version = result.stdout.strip()
    assert len(version) > 0, "scipy version string is empty"
    assert "." in version, f"scipy version doesn't look like a version: '{version}'"


# ══════════════════════════════════════════════════════════════════════════
# 5. Library import tests — matplotlib
# ══════════════════════════════════════════════════════════════════════════

def test_matplotlib_importable():
    """matplotlib must be importable by the custom interpreter."""
    result = run_python("import matplotlib; print(matplotlib.__version__)")
    assert result.returncode == 0, f"Failed to import matplotlib: {result.stderr}"


def test_matplotlib_version_string():
    """matplotlib version must be a non-empty dotted version string."""
    result = run_python("import matplotlib; print(matplotlib.__version__)")
    version = result.stdout.strip()
    assert len(version) > 0, "matplotlib version string is empty"
    assert "." in version, f"matplotlib version doesn't look like a version: '{version}'"


# ══════════════════════════════════════════════════════════════════════════
# 6. Smoke test PNG validation
# ══════════════════════════════════════════════════════════════════════════

def test_smoke_png_exists():
    """Smoke test PNG must exist at /opt/py312/smoke_test_output.png."""
    assert os.path.isfile(SMOKE_PNG), f"Smoke test PNG not found at {SMOKE_PNG}"


def test_smoke_png_not_empty():
    """Smoke test PNG must have non-zero size."""
    assert os.path.isfile(SMOKE_PNG), f"Smoke test PNG not found at {SMOKE_PNG}"
    size = os.path.getsize(SMOKE_PNG)
    assert size > 0, f"Smoke test PNG is empty (0 bytes)"
    # A real plot PNG should be at least a few KB
    assert size > 1000, f"Smoke test PNG suspiciously small ({size} bytes)"


def test_smoke_png_valid():
    """Smoke test PNG must have valid PNG magic bytes."""
    assert os.path.isfile(SMOKE_PNG), f"Smoke test PNG not found at {SMOKE_PNG}"
    assert is_valid_png(SMOKE_PNG), f"{SMOKE_PNG} does not have valid PNG header"


# ══════════════════════════════════════════════════════════════════════════
# 7. Tarball validation
# ══════════════════════════════════════════════════════════════════════════

def test_tarball_exists():
    """Tarball must exist at /app/py312-scientific.tar.gz."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"


def test_tarball_not_empty():
    """Tarball must have non-zero size."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    size = os.path.getsize(TARBALL)
    # A real scientific env tarball should be at least several MB
    assert size > 1_000_000, (
        f"Tarball suspiciously small ({size} bytes); expected multi-MB archive"
    )


def test_tarball_is_valid_gzip():
    """Tarball must be a valid gzip-compressed tar archive."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    try:
        with tarfile.open(TARBALL, "r:gz") as tf:
            # Just reading members is enough to validate structure
            members = tf.getnames()
            assert len(members) > 0, "Tarball is empty (no members)"
    except (tarfile.TarError, OSError) as e:
        raise AssertionError(f"Tarball is not a valid gzip tar archive: {e}")


def test_tarball_contains_python_binary():
    """Tarball must contain the opt/py312/bin/python3.12 entry."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    with tarfile.open(TARBALL, "r:gz") as tf:
        names = tf.getnames()
    # The entry could be with or without leading slash
    matches = [n for n in names if n.rstrip("/").endswith("opt/py312/bin/python3.12")]
    assert len(matches) > 0, (
        "Tarball does not contain 'opt/py312/bin/python3.12'. "
        f"Sample entries: {names[:20]}"
    )


def test_tarball_contains_lib_directory():
    """Tarball must contain the opt/py312/lib/ directory tree."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    with tarfile.open(TARBALL, "r:gz") as tf:
        names = tf.getnames()
    lib_entries = [n for n in names if "opt/py312/lib/" in n]
    assert len(lib_entries) > 10, (
        f"Tarball has too few lib entries ({len(lib_entries)}); "
        "expected a full Python lib tree"
    )


def test_tarball_contains_numpy():
    """Tarball must contain numpy package files."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    with tarfile.open(TARBALL, "r:gz") as tf:
        names = tf.getnames()
    numpy_entries = [n for n in names if "numpy" in n.lower()]
    assert len(numpy_entries) > 0, "Tarball does not contain any numpy files"


def test_tarball_contains_scipy():
    """Tarball must contain scipy package files."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    with tarfile.open(TARBALL, "r:gz") as tf:
        names = tf.getnames()
    scipy_entries = [n for n in names if "scipy" in n.lower()]
    assert len(scipy_entries) > 0, "Tarball does not contain any scipy files"


def test_tarball_contains_matplotlib():
    """Tarball must contain matplotlib package files."""
    assert os.path.isfile(TARBALL), f"Tarball not found at {TARBALL}"
    with tarfile.open(TARBALL, "r:gz") as tf:
        names = tf.getnames()
    mpl_entries = [n for n in names if "matplotlib" in n.lower()]
    assert len(mpl_entries) > 0, "Tarball does not contain any matplotlib files"


# ══════════════════════════════════════════════════════════════════════════
# 8. Self-containment — everything lives under /opt/py312
# ══════════════════════════════════════════════════════════════════════════

def test_openblas_installed_under_prefix():
    """OpenBLAS shared library must exist under /opt/py312/lib."""
    lib_dir = os.path.join(PREFIX, "lib")
    assert os.path.isdir(lib_dir), f"{lib_dir} directory does not exist"
    openblas_files = [
        f for f in os.listdir(lib_dir)
        if "openblas" in f.lower()
    ]
    assert len(openblas_files) > 0, (
        f"No OpenBLAS library found under {lib_dir}. "
        f"Files present: {os.listdir(lib_dir)[:30]}"
    )


def test_numpy_installed_under_prefix():
    """numpy must be installed under /opt/py312, not system site-packages."""
    result = run_python(
        "import numpy; print(numpy.__file__)"
    )
    assert result.returncode == 0, f"Failed to get numpy path: {result.stderr}"
    numpy_path = result.stdout.strip()
    assert numpy_path.startswith(PREFIX), (
        f"numpy is installed at '{numpy_path}', not under {PREFIX}"
    )


def test_scipy_installed_under_prefix():
    """scipy must be installed under /opt/py312, not system site-packages."""
    result = run_python(
        "import scipy; print(scipy.__file__)"
    )
    assert result.returncode == 0, f"Failed to get scipy path: {result.stderr}"
    scipy_path = result.stdout.strip()
    assert scipy_path.startswith(PREFIX), (
        f"scipy is installed at '{scipy_path}', not under {PREFIX}"
    )


def test_matplotlib_installed_under_prefix():
    """matplotlib must be installed under /opt/py312, not system site-packages."""
    result = run_python(
        "import matplotlib; print(matplotlib.__file__)"
    )
    assert result.returncode == 0, f"Failed to get matplotlib path: {result.stderr}"
    mpl_path = result.stdout.strip()
    assert mpl_path.startswith(PREFIX), (
        f"matplotlib is installed at '{mpl_path}', not under {PREFIX}"
    )


# ══════════════════════════════════════════════════════════════════════════
# 9. Functional correctness — libraries actually work, not just import
# ══════════════════════════════════════════════════════════════════════════

def test_numpy_basic_computation():
    """numpy must be able to perform basic array operations."""
    code = (
        "import numpy as np; "
        "a = np.array([1, 2, 3]); "
        "b = np.array([4, 5, 6]); "
        "print(int(np.dot(a, b)))"
    )
    result = run_python(code)
    assert result.returncode == 0, f"numpy computation failed: {result.stderr}"
    assert result.stdout.strip() == "32", (
        f"numpy dot product wrong: expected '32', got '{result.stdout.strip()}'"
    )


def test_scipy_basic_computation():
    """scipy must be able to perform a basic linear algebra operation."""
    code = (
        "import numpy as np; "
        "from scipy import linalg; "
        "A = np.array([[1, 2], [3, 4]]); "
        "det = linalg.det(A); "
        "print(round(det, 1))"
    )
    result = run_python(code)
    assert result.returncode == 0, f"scipy computation failed: {result.stderr}"
    assert result.stdout.strip() == "-2.0", (
        f"scipy determinant wrong: expected '-2.0', got '{result.stdout.strip()}'"
    )


def test_matplotlib_can_save_figure():
    """matplotlib must be able to create and save a figure (Agg backend)."""
    code = (
        "import matplotlib; matplotlib.use('Agg'); "
        "import matplotlib.pyplot as plt; "
        "fig, ax = plt.subplots(); "
        "ax.plot([1, 2, 3], [1, 4, 9]); "
        "fig.savefig('/tmp/test_mpl_output.png'); "
        "print('OK')"
    )
    result = run_python(code)
    assert result.returncode == 0, f"matplotlib figure save failed: {result.stderr}"
    assert result.stdout.strip() == "OK"
    assert os.path.isfile("/tmp/test_mpl_output.png"), (
        "matplotlib failed to produce /tmp/test_mpl_output.png"
    )
    assert is_valid_png("/tmp/test_mpl_output.png"), (
        "/tmp/test_mpl_output.png is not a valid PNG"
    )

