import os
import subprocess
import struct

def test_executable_exists():
    """Test that the executable file exists at the expected location."""
    assert os.path.exists("/app/bin/app"), "Executable /app/bin/app does not exist"

def test_executable_is_file():
    """Test that /app/bin/app is a regular file, not a directory."""
    assert os.path.isfile("/app/bin/app"), "/app/bin/app is not a regular file"

def test_executable_not_empty():
    """Test that the executable is not an empty file."""
    size = os.path.getsize("/app/bin/app")
    assert size > 0, "Executable /app/bin/app is empty"

def test_executable_is_elf_binary():
    """Test that the executable is a valid ELF binary (not a text file or script)."""
    with open("/app/bin/app", "rb") as f:
        magic = f.read(4)
    # ELF magic number: 0x7f 'E' 'L' 'F'
    assert magic == b'\x7fELF', f"Executable is not a valid ELF binary (magic: {magic.hex()})"

def test_executable_is_executable():
    """Test that the file has executable permissions."""
    assert os.access("/app/bin/app", os.X_OK), "Executable /app/bin/app is not executable"

def test_libcore_exists():
    """Test that libcore.a static library exists."""
    assert os.path.exists("/app/lib/libcore.a"), "Static library /app/lib/libcore.a does not exist"

def test_libcore_not_empty():
    """Test that libcore.a is not an empty file."""
    size = os.path.getsize("/app/lib/libcore.a")
    assert size > 0, "Static library /app/lib/libcore.a is empty"

def test_libcore_is_archive():
    """Test that libcore.a is a valid ar archive."""
    with open("/app/lib/libcore.a", "rb") as f:
        magic = f.read(8)
    # ar archive magic: "!<arch>\n"
    assert magic == b'!<arch>\n', f"libcore.a is not a valid ar archive (magic: {magic})"

def test_libutils_exists():
    """Test that libutils.a static library exists."""
    assert os.path.exists("/app/lib/libutils.a"), "Static library /app/lib/libutils.a does not exist"

def test_libutils_not_empty():
    """Test that libutils.a is not an empty file."""
    size = os.path.getsize("/app/lib/libutils.a")
    assert size > 0, "Static library /app/lib/libutils.a is empty"

def test_libutils_is_archive():
    """Test that libutils.a is a valid ar archive."""
    with open("/app/lib/libutils.a", "rb") as f:
        magic = f.read(8)
    # ar archive magic: "!<arch>\n"
    assert magic == b'!<arch>\n', f"libutils.a is not a valid ar archive (magic: {magic})"

def test_executable_runs_successfully():
    """Test that the executable runs and exits with code 0."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    assert result.returncode == 0, f"Executable exited with code {result.returncode}, expected 0"

def test_executable_output_contains_success_message():
    """Test that the executable output contains the required success message."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    output = result.stdout
    assert "All tests completed successfully!" in output, \
        f"Output does not contain 'All tests completed successfully!'. Got: {output}"

def test_executable_output_contains_starting_message():
    """Test that the executable output contains the starting message."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    output = result.stdout
    assert "Starting application..." in output, \
        f"Output does not contain 'Starting application...'. Got: {output}"

def test_executable_output_contains_core_init():
    """Test that the executable output shows core module initialization."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    output = result.stdout
    assert "Core module initialized" in output, \
        f"Output does not contain 'Core module initialized'. Got: {output}"

def test_executable_output_contains_utils_init():
    """Test that the executable output shows utils module initialization."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    output = result.stdout
    assert "Utils module initialized" in output, \
        f"Output does not contain 'Utils module initialized'. Got: {output}"

def test_executable_output_contains_calculation_result():
    """Test that the executable output contains the calculation result."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    output = result.stdout
    # The calculation should be: core_process(10) + 5 = (10 * 2) + 5 = 25
    assert "Calculation result: 25" in output, \
        f"Output does not contain 'Calculation result: 25'. Got: {output}"

def test_executable_links_against_libcore():
    """Test that the executable actually links against libcore symbols."""
    # Use ldd or nm to verify the executable contains symbols from libcore
    result = subprocess.run(
        ["nm", "/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    # Check for core_init or core_process symbols
    assert "core_init" in result.stdout or "core_process" in result.stdout, \
        "Executable does not contain symbols from libcore"

def test_executable_links_against_libutils():
    """Test that the executable actually links against libutils symbols."""
    # Use nm to verify the executable contains symbols from libutils
    result = subprocess.run(
        ["nm", "/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    # Check for utils_init or utils_calculate symbols
    assert "utils_init" in result.stdout or "utils_calculate" in result.stdout, \
        "Executable does not contain symbols from libutils"

def test_executable_size_reasonable():
    """Test that the executable has a reasonable size (not just a dummy file)."""
    size = os.path.getsize("/app/bin/app")
    # A properly compiled C executable should be at least 8KB
    assert size >= 8192, f"Executable size ({size} bytes) is too small, likely a dummy file"

def test_no_stderr_output():
    """Test that the executable runs without errors on stderr."""
    result = subprocess.run(
        ["/app/bin/app"],
        capture_output=True,
        text=True,
        timeout=5
    )
    # Allow empty stderr or only whitespace
    stderr = result.stderr.strip()
    assert stderr == "", f"Executable produced stderr output: {stderr}"
