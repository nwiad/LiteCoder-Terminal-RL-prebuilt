import os
import json
import subprocess
import tempfile


def test_output_json_exists():
    """Verify output.json exists"""
    assert os.path.exists("/app/output.json"), "output.json not found at /app/output.json"


def test_output_json_structure():
    """Verify output.json has correct structure and required fields"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    required_fields = [
        "package_built",
        "package_name",
        "package_version",
        "package_file",
        "patch_applied",
        "repository_created",
        "repository_path"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify boolean fields
    assert isinstance(data["package_built"], bool), "package_built must be boolean"
    assert isinstance(data["patch_applied"], bool), "patch_applied must be boolean"
    assert isinstance(data["repository_created"], bool), "repository_created must be boolean"

    # Verify all success flags are true
    assert data["package_built"] is True, "package_built must be true"
    assert data["patch_applied"] is True, "patch_applied must be true"
    assert data["repository_created"] is True, "repository_created must be true"


def test_output_json_values():
    """Verify output.json contains correct values"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    # Verify package name
    assert data["package_name"] == "htop", f"Expected package_name 'htop', got '{data['package_name']}'"

    # Verify version format (should be 3.2.1-custom1 or similar)
    version = data["package_version"]
    assert "3.2.1" in version, f"Version must contain '3.2.1', got '{version}'"
    assert "custom" in version, f"Version must contain 'custom', got '{version}'"

    # Verify repository path
    assert data["repository_path"] == "/app/repo", f"Expected repository_path '/app/repo', got '{data['repository_path']}'"


def test_package_file_exists():
    """Verify the .deb package file exists"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]
    assert os.path.exists(package_file), f"Package file not found: {package_file}"

    # Verify it's a .deb file
    assert package_file.endswith(".deb"), f"Package file must be a .deb file: {package_file}"

    # Verify file is not empty
    file_size = os.path.getsize(package_file)
    assert file_size > 1000, f"Package file is too small ({file_size} bytes), likely invalid"


def test_package_is_valid_deb():
    """Verify the package is a valid Debian package"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]

    # Use dpkg-deb to verify package integrity
    result = subprocess.run(
        ["dpkg-deb", "--info", package_file],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Package is not a valid .deb file: {result.stderr}"

    # Verify package metadata contains htop
    assert "htop" in result.stdout.lower(), "Package info must contain 'htop'"


def test_package_contains_branding_file():
    """Verify the package contains the custom branding.conf file"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]

    # List package contents
    result = subprocess.run(
        ["dpkg-deb", "--contents", package_file],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed to list package contents: {result.stderr}"

    # Verify branding.conf is included
    assert "branding.conf" in result.stdout, "Package must contain branding.conf file"
    assert "etc/htop" in result.stdout, "branding.conf must be in /etc/htop directory"


def test_package_version_matches():
    """Verify package version in metadata matches output.json"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]
    expected_version = data["package_version"]

    # Get package version from dpkg-deb
    result = subprocess.run(
        ["dpkg-deb", "--field", package_file, "Version"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Failed to get package version: {result.stderr}"

    actual_version = result.stdout.strip()
    assert actual_version == expected_version, f"Version mismatch: expected '{expected_version}', got '{actual_version}'"


def test_patch_applied_verification():
    """Verify the custom patch was actually applied to the source"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]

    # Extract package to temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["dpkg-deb", "--extract", package_file, tmpdir],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Failed to extract package: {result.stderr}"

        # Verify branding.conf exists and has correct content
        branding_path = os.path.join(tmpdir, "etc/htop/branding.conf")
        assert os.path.exists(branding_path), "branding.conf not found in extracted package"

        with open(branding_path, "r") as f:
            content = f.read()

        # Verify branding content
        assert "Enterprise Corp" in content, "branding.conf must contain 'Enterprise Corp'"
        assert "company_name" in content, "branding.conf must contain 'company_name'"


def test_repository_structure():
    """Verify the repository has correct structure"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    repo_path = data["repository_path"]

    # Verify repository directory exists
    assert os.path.exists(repo_path), f"Repository directory not found: {repo_path}"
    assert os.path.isdir(repo_path), f"Repository path is not a directory: {repo_path}"

    # Verify Packages index exists
    packages_file = os.path.join(repo_path, "Packages")
    assert os.path.exists(packages_file), f"Packages index not found: {packages_file}"

    # Verify Packages file is not empty
    file_size = os.path.getsize(packages_file)
    assert file_size > 100, f"Packages index is too small ({file_size} bytes), likely invalid"


def test_repository_packages_index_content():
    """Verify Packages index contains correct package information"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    repo_path = data["repository_path"]
    packages_file = os.path.join(repo_path, "Packages")

    with open(packages_file, "r") as f:
        content = f.read()

    # Verify essential fields in Packages index
    assert "Package: htop" in content, "Packages index must contain 'Package: htop'"
    assert "Version:" in content, "Packages index must contain Version field"
    assert "Architecture:" in content, "Packages index must contain Architecture field"
    assert "Filename:" in content, "Packages index must contain Filename field"

    # Verify version is mentioned
    version = data["package_version"]
    assert version in content, f"Packages index must contain version '{version}'"


def test_repository_contains_package_file():
    """Verify the repository contains the .deb package"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    repo_path = data["repository_path"]

    # Find .deb files in repository
    deb_files = [f for f in os.listdir(repo_path) if f.endswith(".deb")]

    assert len(deb_files) > 0, "Repository must contain at least one .deb file"

    # Verify the package is htop
    htop_debs = [f for f in deb_files if "htop" in f.lower()]
    assert len(htop_debs) > 0, "Repository must contain htop .deb package"


def test_repository_packages_gz_exists():
    """Verify compressed Packages.gz exists"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    repo_path = data["repository_path"]
    packages_gz = os.path.join(repo_path, "Packages.gz")

    # Packages.gz is optional but commonly created
    # If it exists, verify it's valid
    if os.path.exists(packages_gz):
        file_size = os.path.getsize(packages_gz)
        assert file_size > 50, f"Packages.gz is too small ({file_size} bytes)"


def test_package_file_path_consistency():
    """Verify package_file path in output.json points to an actual file"""
    with open("/app/output.json", "r") as f:
        data = json.load(f)

    package_file = data["package_file"]

    # Verify path is absolute
    assert package_file.startswith("/"), f"package_file must be absolute path: {package_file}"

    # Verify filename contains version
    filename = os.path.basename(package_file)
    version = data["package_version"]

    # Extract version components
    version_base = version.split("-")[0]  # e.g., "3.2.1"
    assert version_base in filename, f"Filename must contain version '{version_base}': {filename}"
