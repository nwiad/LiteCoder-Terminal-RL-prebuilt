import os
import subprocess
import sys

def test_wasm_file_exists():
    """Test that the hello.wasm file exists at the expected location."""
    wasm_path = "/app/hello.wasm"
    assert os.path.exists(wasm_path), f"Expected WASM file not found at {wasm_path}"
    print(f"✓ File exists at {wasm_path}")


def test_wasm_file_not_empty():
    """Test that the WASM file is not empty."""
    wasm_path = "/app/hello.wasm"
    file_size = os.path.getsize(wasm_path)
    assert file_size > 0, f"WASM file is empty (0 bytes)"
    assert file_size > 100, f"WASM file suspiciously small ({file_size} bytes), likely not a valid WASM binary"
    print(f"✓ File size: {file_size} bytes")


def test_wasm_magic_bytes():
    """Test that the file has valid WebAssembly magic bytes."""
    wasm_path = "/app/hello.wasm"
    with open(wasm_path, "rb") as f:
        magic = f.read(4)

    expected_magic = b'\x00asm'
    assert magic == expected_magic, f"Invalid WASM magic bytes. Expected {expected_magic.hex()}, got {magic.hex()}"
    print(f"✓ Valid WASM magic bytes: {magic.hex()}")


def test_wasmtime_execution():
    """Test that the WASM binary runs successfully with wasmtime."""
    wasm_path = "/app/hello.wasm"

    # Check if wasmtime is available, install if not
    try:
        subprocess.run(["wasmtime", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing wasmtime...")
        install_result = subprocess.run(
            ["curl", "https://wasmtime.dev/install.sh", "-sSf"],
            capture_output=True,
            text=True
        )
        if install_result.returncode == 0:
            subprocess.run(["sh", "-c", install_result.stdout], check=True)
            # Add to PATH
            os.environ["PATH"] = f"{os.path.expanduser('~/.wasmtime/bin')}:{os.environ.get('PATH', '')}"
        else:
            pytest.skip("Could not install wasmtime")

    result = subprocess.run(
        ["wasmtime", wasm_path],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"wasmtime execution failed with exit code {result.returncode}. stderr: {result.stderr}"
    assert result.stdout == "Hello, Wasm!\n", f"Expected 'Hello, Wasm!\\n', got '{result.stdout}'"
    print(f"✓ wasmtime execution successful: {repr(result.stdout)}")


def test_nodejs_wasi_execution():
    """Test that the WASM binary runs successfully with Node.js WASI."""
    wasm_path = "/app/hello.wasm"

    # Check if node is available
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try to find node in common locations
        node_paths = [
            "/root/.nvm/versions/node/v22.13.1/bin/node",
            "/usr/bin/node",
            "/usr/local/bin/node"
        ]
        node_cmd = None
        for path in node_paths:
            if os.path.exists(path):
                node_cmd = path
                break

        if not node_cmd:
            pytest.skip("Node.js not available")
    else:
        node_cmd = "node"

    # Node.js WASI execution command
    node_code = (
        "const{WASI}=require('wasi');"
        "const fs=require('fs');"
        "const wasi=new WASI();"
        "const importObject={wasi_snapshot_preview1:wasi.wasiImport};"
        f"WebAssembly.instantiate(fs.readFileSync('{wasm_path}'),importObject)"
        ".then(m=>{wasi.start(m.instance)})"
    )

    result = subprocess.run(
        [node_cmd, "--experimental-wasi-unstable-preview1", "-e", node_code],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Node.js WASI execution failed with exit code {result.returncode}. stderr: {result.stderr}"
    assert result.stdout == "Hello, Wasm!\n", f"Expected 'Hello, Wasm!\\n', got '{result.stdout}'"
    print(f"✓ Node.js WASI execution successful: {repr(result.stdout)}")


def test_wasm_is_statically_linked():
    """Test that the WASM binary doesn't have external module dependencies."""
    wasm_path = "/app/hello.wasm"

    # Use wasm-objdump if available to check imports
    try:
        result = subprocess.run(
            ["wasm-objdump", "-x", wasm_path],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Check that there are no module imports other than WASI
            lines = result.stdout.split('\n')
            for line in lines:
                if 'import' in line.lower() and 'module' in line.lower():
                    # WASI imports are expected (wasi_snapshot_preview1)
                    assert 'wasi' in line.lower(), f"Unexpected non-WASI import found: {line}"
            print("✓ WASM binary appears to be statically linked (only WASI imports)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # wasm-objdump not available, skip this detailed check
        # The execution tests above are sufficient to verify functionality
        print("✓ Skipping detailed import analysis (wasm-objdump not available)")


def test_output_format_exact():
    """Test that output format is exactly as specified with trailing newline."""
    wasm_path = "/app/hello.wasm"

    # Try wasmtime first
    try:
        subprocess.run(["wasmtime", "--version"], capture_output=True, check=True)
        result = subprocess.run(
            ["wasmtime", wasm_path],
            capture_output=True,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("wasmtime not available for output format test")

    # Check exact output
    assert result.stdout == "Hello, Wasm!\n", f"Output must be exactly 'Hello, Wasm!\\n' (with trailing newline)"
    assert not result.stdout.startswith('\n'), "Output should not have leading newline"
    assert result.stdout.endswith('\n'), "Output must have trailing newline"
    assert result.stdout.count('\n') == 1, "Output should have exactly one newline (at the end)"

    print(f"✓ Output format is exact: {repr(result.stdout)}")
