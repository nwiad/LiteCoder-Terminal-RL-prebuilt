import os
import json
import subprocess

def test_result_json_exists():
    """Verify result.json exists"""
    assert os.path.exists("/app/result.json"), "result.json not found at /app/result.json"

def test_result_json_valid():
    """Verify result.json is valid JSON"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "result.json must contain a JSON object"

def test_result_json_required_fields():
    """Verify all required fields are present"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    required_fields = ["tcc_version", "tcc_path", "test_program_compiled", "test_output", "binary_size_bytes"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

def test_tcc_version_field():
    """Verify tcc_version is a non-empty string"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    assert isinstance(data["tcc_version"], str), "tcc_version must be a string"
    assert len(data["tcc_version"]) > 0, "tcc_version cannot be empty"
    assert "tcc" in data["tcc_version"].lower(), "tcc_version should contain 'tcc'"

def test_tcc_path_field():
    """Verify tcc_path points to an actual executable"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    tcc_path = data["tcc_path"]
    assert isinstance(tcc_path, str), "tcc_path must be a string"
    assert os.path.exists(tcc_path), f"tcc binary not found at {tcc_path}"
    assert os.path.isfile(tcc_path), f"tcc_path must point to a file, not a directory"
    assert os.access(tcc_path, os.X_OK), f"tcc binary at {tcc_path} is not executable"

def test_tcc_actually_works():
    """Verify tcc can actually compile and run programs"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    tcc_path = data["tcc_path"]

    # Try to run tcc -v to verify it's actually tcc
    result = subprocess.run([tcc_path, "-v"], capture_output=True, text=True)
    assert result.returncode == 0, "tcc -v failed to execute"

    # Verify the version output contains tcc-related info
    version_output = result.stdout + result.stderr
    assert "tcc" in version_output.lower(), "tcc -v output doesn't mention tcc"

def test_test_program_compiled_field():
    """Verify test_program_compiled is a boolean"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    assert isinstance(data["test_program_compiled"], bool), "test_program_compiled must be a boolean"
    assert data["test_program_compiled"] == True, "test_program_compiled should be true"

def test_hello_tcc_binary_exists():
    """Verify the compiled binary exists"""
    assert os.path.exists("/app/hello_tcc"), "Compiled binary /app/hello_tcc not found"
    assert os.path.isfile("/app/hello_tcc"), "/app/hello_tcc must be a file"
    assert os.access("/app/hello_tcc", os.X_OK), "/app/hello_tcc must be executable"

def test_hello_tcc_binary_not_empty():
    """Verify the binary is not empty or trivially small"""
    size = os.path.getsize("/app/hello_tcc")
    assert size > 100, f"Binary size {size} bytes is suspiciously small (likely empty or dummy)"

def test_test_output_field():
    """Verify test_output contains the expected output"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    test_output = data["test_output"]
    assert isinstance(test_output, str), "test_output must be a string"

    # Strip whitespace for comparison
    expected = "Hello from tcc!"
    actual = test_output.strip()
    assert actual == expected, f"Expected output '{expected}', got '{actual}'"

def test_hello_tcc_actually_runs():
    """Verify the compiled binary actually runs and produces correct output"""
    result = subprocess.run(["/app/hello_tcc"], capture_output=True, text=True)

    assert result.returncode == 0, f"hello_tcc exited with code {result.returncode}"
    assert result.stdout.strip() == "Hello from tcc!", f"Unexpected output: {result.stdout}"

def test_binary_size_bytes_field():
    """Verify binary_size_bytes is a positive integer"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    binary_size = data["binary_size_bytes"]
    assert isinstance(binary_size, int), "binary_size_bytes must be an integer"
    assert binary_size > 0, "binary_size_bytes must be positive"

def test_binary_size_matches_actual():
    """Verify binary_size_bytes matches the actual file size"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    reported_size = data["binary_size_bytes"]
    actual_size = os.path.getsize("/app/hello_tcc")

    assert reported_size == actual_size, f"Reported size {reported_size} doesn't match actual size {actual_size}"

def test_binary_size_reasonable():
    """Verify binary size is in a reasonable range for a simple C program"""
    with open("/app/result.json", "r") as f:
        data = json.load(f)

    size = data["binary_size_bytes"]
    # TCC produces very small binaries, typically 1KB-50KB for simple programs
    assert 100 < size < 1000000, f"Binary size {size} bytes is outside reasonable range (100 bytes - 1MB)"

def test_hello_c_source_exists():
    """Verify the source file was created"""
    assert os.path.exists("/app/hello.c"), "Source file /app/hello.c not found"

def test_hello_c_source_content():
    """Verify hello.c contains the expected program"""
    with open("/app/hello.c", "r") as f:
        content = f.read()

    # Check for key elements of the required program
    assert "#include <stdio.h>" in content, "hello.c missing stdio.h include"
    assert "int main()" in content, "hello.c missing main function"
    assert 'printf("Hello from tcc!\\n")' in content or "printf(\"Hello from tcc!\\n\")" in content, "hello.c missing correct printf statement"
    assert "return 0" in content, "hello.c missing return statement"
