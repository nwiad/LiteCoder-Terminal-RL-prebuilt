import os
import subprocess
import platform


def test_installation_directory_structure():
    """Verify /opt/lua54 exists with required subdirectories."""
    base_path = "/opt/lua54"

    assert os.path.exists(base_path), f"Installation directory {base_path} does not exist"
    assert os.path.isdir(base_path), f"{base_path} is not a directory"

    # Check required subdirectories
    required_dirs = ["bin", "include", "lib"]
    for subdir in required_dirs:
        dir_path = os.path.join(base_path, subdir)
        assert os.path.exists(dir_path), f"Required directory {dir_path} does not exist"
        assert os.path.isdir(dir_path), f"{dir_path} is not a directory"


def test_lua_binary_exists_and_executable():
    """Verify lua binary exists and is executable."""
    lua_bin = "/opt/lua54/bin/lua"

    assert os.path.exists(lua_bin), f"Lua binary {lua_bin} does not exist"
    assert os.path.isfile(lua_bin), f"{lua_bin} is not a file"
    assert os.access(lua_bin, os.X_OK), f"{lua_bin} is not executable"

    # Verify it's not an empty file
    assert os.path.getsize(lua_bin) > 0, f"{lua_bin} is empty"


def test_luac_binary_exists_and_executable():
    """Verify luac binary exists and is executable."""
    luac_bin = "/opt/lua54/bin/luac"

    assert os.path.exists(luac_bin), f"Luac binary {luac_bin} does not exist"
    assert os.path.isfile(luac_bin), f"{luac_bin} is not a file"
    assert os.access(luac_bin, os.X_OK), f"{luac_bin} is not executable"

    # Verify it's not an empty file
    assert os.path.getsize(luac_bin) > 0, f"{luac_bin} is empty"


def test_shared_library_exists():
    """Verify shared library exists in /opt/lua54/lib/."""
    lib_dir = "/opt/lua54/lib"

    # Detect platform to check for correct shared library
    system = platform.system()

    if system == "Darwin":
        # macOS uses .dylib
        shared_lib = os.path.join(lib_dir, "liblua.dylib")
        assert os.path.exists(shared_lib), f"Shared library {shared_lib} does not exist on macOS"
    else:
        # Linux uses .so
        shared_lib = os.path.join(lib_dir, "liblua.so")
        assert os.path.exists(shared_lib), f"Shared library {shared_lib} does not exist on Linux"

    assert os.path.isfile(shared_lib), f"{shared_lib} is not a file"
    assert os.path.getsize(shared_lib) > 0, f"{shared_lib} is empty"


def test_lua_dynamically_links_to_shared_library():
    """Verify lua interpreter dynamically links to the shared library."""
    lua_bin = "/opt/lua54/bin/lua"
    system = platform.system()

    if system == "Darwin":
        # Use otool on macOS
        result = subprocess.run(
            ["otool", "-L", lua_bin],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"otool command failed: {result.stderr}"
        assert "liblua.dylib" in result.stdout, \
            f"lua binary does not dynamically link to liblua.dylib. Output: {result.stdout}"
    else:
        # Use ldd on Linux
        result = subprocess.run(
            ["ldd", lua_bin],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"ldd command failed: {result.stderr}"
        assert "liblua.so" in result.stdout, \
            f"lua binary does not dynamically link to liblua.so. Output: {result.stdout}"


def test_lua_version_is_5_4():
    """Verify Lua version is 5.4.x."""
    lua_bin = "/opt/lua54/bin/lua"

    # Set library path for execution
    env = os.environ.copy()
    system = platform.system()

    if system == "Darwin":
        env["DYLD_LIBRARY_PATH"] = "/opt/lua54/lib"
    else:
        env["LD_LIBRARY_PATH"] = "/opt/lua54/lib"

    result = subprocess.run(
        [lua_bin, "-v"],
        capture_output=True,
        text=True,
        env=env
    )

    assert result.returncode == 0, f"lua -v command failed: {result.stderr}"

    # Check version output contains "Lua 5.4"
    output = result.stdout + result.stderr  # Version might be in stderr
    assert "Lua 5.4" in output, f"Expected Lua 5.4.x, got: {output}"


def test_hello_lua_script_exists():
    """Verify /app/hello.lua test script exists."""
    hello_script = "/app/hello.lua"

    assert os.path.exists(hello_script), f"Test script {hello_script} does not exist"
    assert os.path.isfile(hello_script), f"{hello_script} is not a file"
    assert os.path.getsize(hello_script) > 0, f"{hello_script} is empty"


def test_hello_lua_script_produces_correct_output():
    """Verify /app/hello.lua executes and produces expected output."""
    lua_bin = "/opt/lua54/bin/lua"
    hello_script = "/app/hello.lua"

    # Set library path for execution
    env = os.environ.copy()
    system = platform.system()

    if system == "Darwin":
        env["DYLD_LIBRARY_PATH"] = "/opt/lua54/lib"
    else:
        env["LD_LIBRARY_PATH"] = "/opt/lua54/lib"

    result = subprocess.run(
        [lua_bin, hello_script],
        capture_output=True,
        text=True,
        env=env
    )

    assert result.returncode == 0, f"Execution of {hello_script} failed: {result.stderr}"

    # Check output matches expected
    expected_output = "Hello from Lua 5.4!"
    actual_output = result.stdout.strip()

    assert actual_output == expected_output, \
        f"Expected output '{expected_output}', got '{actual_output}'"


def test_lua_can_execute_basic_code():
    """Verify lua can execute basic Lua code (not hardcoded)."""
    lua_bin = "/opt/lua54/bin/lua"

    # Set library path for execution
    env = os.environ.copy()
    system = platform.system()

    if system == "Darwin":
        env["DYLD_LIBRARY_PATH"] = "/opt/lua54/lib"
    else:
        env["LD_LIBRARY_PATH"] = "/opt/lua54/lib"

    # Test with a simple arithmetic operation
    test_code = "print(2 + 2)"
    result = subprocess.run(
        [lua_bin, "-e", test_code],
        capture_output=True,
        text=True,
        env=env
    )

    assert result.returncode == 0, f"Execution of test code failed: {result.stderr}"
    assert result.stdout.strip() == "4", \
        f"Expected '4', got '{result.stdout.strip()}' - Lua may not be functioning correctly"


def test_lua_header_files_exist():
    """Verify Lua header files are installed."""
    include_dir = "/opt/lua54/include"

    # Check for key header files
    required_headers = ["lua.h", "lualib.h", "lauxlib.h"]

    for header in required_headers:
        header_path = os.path.join(include_dir, header)
        assert os.path.exists(header_path), f"Header file {header_path} does not exist"
        assert os.path.isfile(header_path), f"{header_path} is not a file"
        assert os.path.getsize(header_path) > 0, f"{header_path} is empty"


def test_shared_library_is_not_static():
    """Verify the library is actually shared, not static."""
    lib_dir = "/opt/lua54/lib"
    system = platform.system()

    if system == "Darwin":
        shared_lib = os.path.join(lib_dir, "liblua.dylib")
    else:
        shared_lib = os.path.join(lib_dir, "liblua.so")

    # Check file type to ensure it's a shared library
    result = subprocess.run(
        ["file", shared_lib],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"file command failed: {result.stderr}"

    # Shared libraries should contain "shared" or "dynamically linked"
    output_lower = result.stdout.lower()
    assert "shared" in output_lower or "dynamic" in output_lower, \
        f"Library does not appear to be a shared library. file output: {result.stdout}"
