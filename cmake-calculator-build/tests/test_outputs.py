import os
import subprocess
import pytest


def test_executable_exists():
    """Test that the calculator executable was built and exists at the correct path."""
    executable_path = "/app/build/calculator"
    assert os.path.exists(executable_path), f"Calculator executable not found at {executable_path}"
    assert os.path.isfile(executable_path), f"{executable_path} is not a file"
    assert os.access(executable_path, os.X_OK), f"{executable_path} is not executable"


def test_add_operation():
    """Test addition operation with various inputs."""
    executable_path = "/app/build/calculator"

    # Test basic addition
    result = subprocess.run([executable_path, "add", "5", "3"], capture_output=True, text=True)
    assert result.returncode == 0, f"Addition failed with exit code {result.returncode}"
    output = result.stdout.strip()
    assert output in ["8", "8.0", "8.00"], f"Expected 8, got {output}"

    # Test negative numbers
    result = subprocess.run([executable_path, "add", "-5", "3"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["-2", "-2.0", "-2.00"], f"Expected -2, got {output}"

    # Test decimals
    result = subprocess.run([executable_path, "add", "2.5", "3.7"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 6.2) < 0.01, f"Expected ~6.2, got {output}"


def test_subtract_operation():
    """Test subtraction operation with various inputs."""
    executable_path = "/app/build/calculator"

    # Test basic subtraction
    result = subprocess.run([executable_path, "subtract", "10", "3"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["7", "7.0", "7.00"], f"Expected 7, got {output}"

    # Test negative result
    result = subprocess.run([executable_path, "subtract", "3", "10"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["-7", "-7.0", "-7.00"], f"Expected -7, got {output}"

    # Test decimals
    result = subprocess.run([executable_path, "subtract", "5.5", "2.3"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 3.2) < 0.01, f"Expected ~3.2, got {output}"


def test_multiply_operation():
    """Test multiplication operation with various inputs."""
    executable_path = "/app/build/calculator"

    # Test basic multiplication
    result = subprocess.run([executable_path, "multiply", "4", "5"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["20", "20.0", "20.00"], f"Expected 20, got {output}"

    # Test with zero
    result = subprocess.run([executable_path, "multiply", "100", "0"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["0", "0.0", "0.00"], f"Expected 0, got {output}"

    # Test negative numbers
    result = subprocess.run([executable_path, "multiply", "-3", "4"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["-12", "-12.0", "-12.00"], f"Expected -12, got {output}"

    # Test decimals
    result = subprocess.run([executable_path, "multiply", "2.5", "4"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 10.0) < 0.01, f"Expected ~10, got {output}"


def test_divide_operation():
    """Test division operation with various inputs."""
    executable_path = "/app/build/calculator"

    # Test basic division
    result = subprocess.run([executable_path, "divide", "10", "2"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["5", "5.0", "5.00"], f"Expected 5, got {output}"

    # Test division with remainder
    result = subprocess.run([executable_path, "divide", "7", "2"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 3.5) < 0.01, f"Expected ~3.5, got {output}"

    # Test negative division
    result = subprocess.run([executable_path, "divide", "-10", "2"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    assert output in ["-5", "-5.0", "-5.00"], f"Expected -5, got {output}"


def test_division_by_zero():
    """Test that division by zero is handled with error."""
    executable_path = "/app/build/calculator"

    result = subprocess.run([executable_path, "divide", "10", "0"], capture_output=True, text=True)
    assert result.returncode != 0, "Division by zero should return non-zero exit code"
    assert "error" in result.stderr.lower() or "division" in result.stderr.lower(), \
        "Error message should mention division or error"


def test_invalid_operation():
    """Test that invalid operations are rejected."""
    executable_path = "/app/build/calculator"

    result = subprocess.run([executable_path, "power", "2", "3"], capture_output=True, text=True)
    assert result.returncode != 0, "Invalid operation should return non-zero exit code"

    result = subprocess.run([executable_path, "modulo", "10", "3"], capture_output=True, text=True)
    assert result.returncode != 0, "Invalid operation should return non-zero exit code"


def test_invalid_number_format():
    """Test that invalid number formats are handled gracefully."""
    executable_path = "/app/build/calculator"

    # Test with non-numeric input
    result = subprocess.run([executable_path, "add", "abc", "5"], capture_output=True, text=True)
    assert result.returncode != 0, "Invalid number format should return non-zero exit code"

    result = subprocess.run([executable_path, "add", "5", "xyz"], capture_output=True, text=True)
    assert result.returncode != 0, "Invalid number format should return non-zero exit code"


def test_incorrect_argument_count():
    """Test that incorrect number of arguments is handled."""
    executable_path = "/app/build/calculator"

    # Too few arguments
    result = subprocess.run([executable_path, "add", "5"], capture_output=True, text=True)
    assert result.returncode != 0, "Too few arguments should return non-zero exit code"

    # Too many arguments
    result = subprocess.run([executable_path, "add", "5", "3", "2"], capture_output=True, text=True)
    assert result.returncode != 0, "Too many arguments should return non-zero exit code"

    # No arguments
    result = subprocess.run([executable_path], capture_output=True, text=True)
    assert result.returncode != 0, "No arguments should return non-zero exit code"


def test_cmake_files_exist():
    """Test that CMakeLists.txt exists and is properly configured."""
    cmake_path = "/app/CMakeLists.txt"
    assert os.path.exists(cmake_path), f"CMakeLists.txt not found at {cmake_path}"

    with open(cmake_path, 'r') as f:
        content = f.read()

    # Check for required CMake directives
    assert "cmake_minimum_required" in content.lower(), "CMakeLists.txt missing cmake_minimum_required"
    assert "project" in content.lower(), "CMakeLists.txt missing project declaration"
    assert "add_executable" in content.lower(), "CMakeLists.txt missing add_executable"
    assert "calculator" in content.lower(), "CMakeLists.txt should reference calculator executable"


def test_source_files_exist():
    """Test that source and header files exist in correct directories."""
    src_dir = "/app/src"
    include_dir = "/app/include"

    assert os.path.exists(src_dir), f"Source directory not found at {src_dir}"
    assert os.path.isdir(src_dir), f"{src_dir} is not a directory"

    # Check that source directory is not empty
    src_files = [f for f in os.listdir(src_dir) if f.endswith(('.c', '.cpp', '.cc', '.cxx'))]
    assert len(src_files) > 0, "No source files found in /app/src/"

    # Check include directory exists (may be empty if headers are in src)
    assert os.path.exists(include_dir), f"Include directory not found at {include_dir}"


def test_build_directory_structure():
    """Test that build directory exists and contains expected files."""
    build_dir = "/app/build"
    assert os.path.exists(build_dir), f"Build directory not found at {build_dir}"
    assert os.path.isdir(build_dir), f"{build_dir} is not a directory"


def test_calculator_produces_consistent_results():
    """Test that calculator produces consistent results across multiple runs."""
    executable_path = "/app/build/calculator"

    # Run the same calculation multiple times
    results = []
    for _ in range(3):
        result = subprocess.run([executable_path, "multiply", "7", "8"], capture_output=True, text=True)
        assert result.returncode == 0
        results.append(result.stdout.strip())

    # All results should be the same
    assert len(set(results)) == 1, f"Calculator produced inconsistent results: {results}"

    # Verify the result is correct
    output_float = float(results[0])
    assert abs(output_float - 56.0) < 0.01, f"Expected 56, got {results[0]}"


def test_large_numbers():
    """Test calculator with large numbers."""
    executable_path = "/app/build/calculator"

    result = subprocess.run([executable_path, "multiply", "1000000", "1000"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 1000000000.0) < 1.0, f"Expected 1000000000, got {output}"


def test_very_small_decimals():
    """Test calculator with very small decimal numbers."""
    executable_path = "/app/build/calculator"

    result = subprocess.run([executable_path, "add", "0.001", "0.002"], capture_output=True, text=True)
    assert result.returncode == 0
    output = result.stdout.strip()
    output_float = float(output)
    assert abs(output_float - 0.003) < 0.0001, f"Expected ~0.003, got {output}"
