import os
import subprocess
import glob
import tempfile
import shutil


def test_deb_file_exists():
    """Test that a .deb file exists in /app/ directory."""
    deb_files = glob.glob("/app/*.deb")
    assert len(deb_files) > 0, "No .deb file found in /app/ directory"


def test_deb_file_naming_convention():
    """Test that the .deb file follows Debian naming conventions."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file matching 'python3-fastcalc_*.deb' found"

    # Check that the filename contains version information
    deb_file = deb_files[0]
    filename = os.path.basename(deb_file)
    assert "1.0.0" in filename, f"Version 1.0.0 not found in filename: {filename}"


def test_deb_file_not_empty():
    """Test that the .deb file is not empty or trivially small."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]
    file_size = os.path.getsize(deb_file)
    # A valid .deb with Python code and C extension should be at least 5KB
    assert file_size > 5000, f".deb file is too small ({file_size} bytes), likely empty or invalid"


def test_deb_package_structure():
    """Test that the .deb file has valid Debian package structure."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Use dpkg-deb to check package structure
    result = subprocess.run(
        ["dpkg-deb", "--info", deb_file],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"dpkg-deb --info failed: {result.stderr}"

    # Check for essential metadata
    info_output = result.stdout
    assert "Package: python3-fastcalc" in info_output, "Package name not found in metadata"
    assert "Version: 1.0.0" in info_output, "Version 1.0.0 not found in metadata"


def test_package_installation():
    """Test that the package can be installed without errors."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Install the package
    result = subprocess.run(
        ["dpkg", "-i", deb_file],
        capture_output=True,
        text=True
    )

    # Check if installation succeeded or if we need to fix dependencies
    if result.returncode != 0:
        # Try to fix dependencies
        subprocess.run(["apt-get", "install", "-f", "-y"], capture_output=True)

        # Retry installation
        result = subprocess.run(
            ["dpkg", "-i", deb_file],
            capture_output=True,
            text=True
        )

    assert result.returncode == 0, f"Package installation failed: {result.stderr}"


def test_python_module_importable():
    """Test that the fastcalc module can be imported after installation."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Ensure package is installed
    subprocess.run(["dpkg", "-i", deb_file], capture_output=True)
    subprocess.run(["apt-get", "install", "-f", "-y"], capture_output=True)

    # Test import
    result = subprocess.run(
        ["python3", "-c", "import fastcalc; print('SUCCESS')"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed to import fastcalc module: {result.stderr}"
    assert "SUCCESS" in result.stdout, "Import did not complete successfully"


def test_python_functions_work():
    """Test that the Python functions in fastcalc work correctly."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Ensure package is installed
    subprocess.run(["dpkg", "-i", deb_file], capture_output=True)
    subprocess.run(["apt-get", "install", "-f", "-y"], capture_output=True)

    # Test add function
    result = subprocess.run(
        ["python3", "-c", "import fastcalc; result = fastcalc.add(5, 3); assert result == 8, f'Expected 8, got {result}'; print('ADD_OK')"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"add() function failed: {result.stderr}"
    assert "ADD_OK" in result.stdout, "add() function did not return expected result"

    # Test multiply function
    result = subprocess.run(
        ["python3", "-c", "import fastcalc; result = fastcalc.multiply(4, 7); assert result == 28, f'Expected 28, got {result}'; print('MULTIPLY_OK')"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"multiply() function failed: {result.stderr}"
    assert "MULTIPLY_OK" in result.stdout, "multiply() function did not return expected result"


def test_c_extension_available():
    """Test that the C extension module is available and functional."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Ensure package is installed
    subprocess.run(["dpkg", "-i", deb_file], capture_output=True)
    subprocess.run(["apt-get", "install", "-f", "-y"], capture_output=True)

    # Test that fast_power function exists and works
    result = subprocess.run(
        ["python3", "-c", "import fastcalc; result = fastcalc.fast_power(2, 3); assert abs(result - 8.0) < 0.001, f'Expected 8.0, got {result}'; print('POWER_OK')"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"fast_power() function failed: {result.stderr}"
    assert "POWER_OK" in result.stdout, "fast_power() function did not return expected result"


def test_package_contents():
    """Test that the package contains expected files."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # List package contents
    result = subprocess.run(
        ["dpkg-deb", "--contents", deb_file],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed to list package contents: {result.stderr}"

    contents = result.stdout

    # Check for Python module files
    assert "fastcalc" in contents, "fastcalc module directory not found in package"
    assert "__init__.py" in contents, "__init__.py not found in package"

    # Check for compiled extension (should have .so file)
    assert ".so" in contents, "No compiled C extension (.so file) found in package"


def test_source_directory_structure():
    """Test that the source directory structure exists as specified."""
    source_dir = "/app/fastcalc-1.0.0"

    assert os.path.isdir(source_dir), f"Source directory {source_dir} does not exist"

    # Check for debian directory
    debian_dir = os.path.join(source_dir, "debian")
    assert os.path.isdir(debian_dir), f"debian directory not found at {debian_dir}"

    # Check for required debian files
    required_files = ["control", "changelog", "copyright", "rules", "compat"]
    for filename in required_files:
        filepath = os.path.join(debian_dir, filename)
        assert os.path.isfile(filepath), f"Required debian file not found: {filepath}"


def test_debian_control_file():
    """Test that debian/control has correct package information."""
    control_file = "/app/fastcalc-1.0.0/debian/control"

    if not os.path.isfile(control_file):
        # Skip if source directory was cleaned up
        return

    with open(control_file, 'r') as f:
        content = f.read()

    assert "Package: python3-fastcalc" in content, "Package name not found in control file"
    assert "python3" in content.lower(), "Python 3 dependency not mentioned in control file"


def test_package_removal():
    """Test that the package can be cleanly removed."""
    deb_files = glob.glob("/app/python3-fastcalc_*.deb")
    assert len(deb_files) > 0, "No .deb file found"

    deb_file = deb_files[0]

    # Ensure package is installed
    subprocess.run(["dpkg", "-i", deb_file], capture_output=True)
    subprocess.run(["apt-get", "install", "-f", "-y"], capture_output=True)

    # Remove the package
    result = subprocess.run(
        ["dpkg", "-r", "python3-fastcalc"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Package removal failed: {result.stderr}"

    # Verify module is no longer importable
    result = subprocess.run(
        ["python3", "-c", "import fastcalc"],
        capture_output=True,
        text=True
    )

    assert result.returncode != 0, "Module still importable after package removal"
