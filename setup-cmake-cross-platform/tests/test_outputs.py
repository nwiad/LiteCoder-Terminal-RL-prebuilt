import os
import json
import subprocess

# Test runs from /app, files should be in /app
APP_DIR = "/app"

def test_cmakelists_exists():
    """Verify CMakeLists.txt file exists"""
    cmake_file = os.path.join(APP_DIR, "CMakeLists.txt")
    assert os.path.exists(cmake_file), "CMakeLists.txt does not exist in /app"
    assert os.path.isfile(cmake_file), "CMakeLists.txt is not a file"
    assert os.path.getsize(cmake_file) > 0, "CMakeLists.txt is empty"

def test_cmakepresets_exists():
    """Verify CMakePresets.json file exists"""
    presets_file = os.path.join(APP_DIR, "CMakePresets.json")
    assert os.path.exists(presets_file), "CMakePresets.json does not exist in /app"
    assert os.path.isfile(presets_file), "CMakePresets.json is not a file"
    assert os.path.getsize(presets_file) > 0, "CMakePresets.json is empty"

def test_main_cpp_exists():
    """Verify src/main.cpp file exists"""
    main_file = os.path.join(APP_DIR, "src", "main.cpp")
    assert os.path.exists(main_file), "src/main.cpp does not exist in /app/src"
    assert os.path.isfile(main_file), "src/main.cpp is not a file"
    assert os.path.getsize(main_file) > 0, "src/main.cpp is empty"

def test_cmakepresets_valid_json():
    """Verify CMakePresets.json is valid JSON"""
    presets_file = os.path.join(APP_DIR, "CMakePresets.json")
    with open(presets_file, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"CMakePresets.json is not valid JSON: {e}"

    assert isinstance(data, dict), "CMakePresets.json root must be an object"

def test_cmakepresets_has_required_presets():
    """Verify CMakePresets.json contains all three required presets"""
    presets_file = os.path.join(APP_DIR, "CMakePresets.json")
    with open(presets_file, 'r') as f:
        data = json.load(f)

    assert "configurePresets" in data, "CMakePresets.json missing 'configurePresets' field"
    configure_presets = data["configurePresets"]
    assert isinstance(configure_presets, list), "configurePresets must be a list"

    preset_names = [p.get("name") for p in configure_presets]
    required_presets = ["linux-gcc", "windows-mingw", "macos-clang"]

    for required in required_presets:
        assert required in preset_names, f"Missing required preset: {required}"

def test_cmakepresets_preset_structure():
    """Verify each preset has required fields"""
    presets_file = os.path.join(APP_DIR, "CMakePresets.json")
    with open(presets_file, 'r') as f:
        data = json.load(f)

    configure_presets = data["configurePresets"]
    required_preset_names = ["linux-gcc", "windows-mingw", "macos-clang"]

    for preset in configure_presets:
        if preset.get("name") in required_preset_names:
            name = preset.get("name")

            # Check generator field exists
            assert "generator" in preset, f"Preset '{name}' missing 'generator' field"
            assert isinstance(preset["generator"], str), f"Preset '{name}' generator must be a string"
            assert len(preset["generator"]) > 0, f"Preset '{name}' generator cannot be empty"

            # Check binaryDir field exists
            assert "binaryDir" in preset, f"Preset '{name}' missing 'binaryDir' field"
            assert isinstance(preset["binaryDir"], str), f"Preset '{name}' binaryDir must be a string"
            assert len(preset["binaryDir"]) > 0, f"Preset '{name}' binaryDir cannot be empty"

            # Check cacheVariables field exists
            assert "cacheVariables" in preset, f"Preset '{name}' missing 'cacheVariables' field"
            cache_vars = preset["cacheVariables"]
            assert isinstance(cache_vars, dict), f"Preset '{name}' cacheVariables must be an object"

            # Check required cache variables
            assert "CMAKE_BUILD_TYPE" in cache_vars, f"Preset '{name}' missing CMAKE_BUILD_TYPE in cacheVariables"
            assert "CMAKE_CXX_COMPILER" in cache_vars, f"Preset '{name}' missing CMAKE_CXX_COMPILER in cacheVariables"

def test_cmakepresets_has_build_presets():
    """Verify CMakePresets.json contains buildPresets"""
    presets_file = os.path.join(APP_DIR, "CMakePresets.json")
    with open(presets_file, 'r') as f:
        data = json.load(f)

    # buildPresets are optional but recommended for the task
    # If they exist, verify they reference valid configurePresets
    if "buildPresets" in data:
        build_presets = data["buildPresets"]
        assert isinstance(build_presets, list), "buildPresets must be a list"

        configure_preset_names = [p.get("name") for p in data.get("configurePresets", [])]

        for build_preset in build_presets:
            if "configurePreset" in build_preset:
                config_ref = build_preset["configurePreset"]
                assert config_ref in configure_preset_names, \
                    f"buildPreset references non-existent configurePreset: {config_ref}"

def test_cmakelists_project_name():
    """Verify CMakeLists.txt contains correct project name"""
    cmake_file = os.path.join(APP_DIR, "CMakeLists.txt")
    with open(cmake_file, 'r') as f:
        content = f.read()

    # Check for project(Auto-GUI) - allow variations in whitespace
    assert "project" in content.lower(), "CMakeLists.txt missing project() command"
    assert "auto-gui" in content.lower(), "CMakeLists.txt project name must be 'Auto-GUI'"

def test_cmakelists_cmake_minimum_required():
    """Verify CMakeLists.txt specifies minimum CMake version"""
    cmake_file = os.path.join(APP_DIR, "CMakeLists.txt")
    with open(cmake_file, 'r') as f:
        content = f.read()

    assert "cmake_minimum_required" in content.lower(), \
        "CMakeLists.txt missing cmake_minimum_required() command"

    # Check for version 3.25 or higher
    assert "3.25" in content or "3.26" in content or "3.27" in content or "3.28" in content or "3.29" in content or "3.30" in content, \
        "CMakeLists.txt must require CMake version >= 3.25"

def test_cmakelists_cpp_standard():
    """Verify CMakeLists.txt sets C++ standard"""
    cmake_file = os.path.join(APP_DIR, "CMakeLists.txt")
    with open(cmake_file, 'r') as f:
        content = f.read()

    # Check for C++ standard setting (C++17 or higher)
    assert "CMAKE_CXX_STANDARD" in content, \
        "CMakeLists.txt must set CMAKE_CXX_STANDARD"

    # Verify it's at least C++17
    has_valid_standard = any(std in content for std in ["17", "20", "23"])
    assert has_valid_standard, "CMakeLists.txt must set C++ standard to 17 or higher"

def test_cmakelists_executable_target():
    """Verify CMakeLists.txt creates executable target named 'auto-gui'"""
    cmake_file = os.path.join(APP_DIR, "CMakeLists.txt")
    with open(cmake_file, 'r') as f:
        content = f.read()

    assert "add_executable" in content.lower(), \
        "CMakeLists.txt missing add_executable() command"
    assert "auto-gui" in content.lower(), \
        "CMakeLists.txt must create executable target named 'auto-gui'"

def test_main_cpp_has_main_function():
    """Verify src/main.cpp contains a main function"""
    main_file = os.path.join(APP_DIR, "src", "main.cpp")
    with open(main_file, 'r') as f:
        content = f.read()

    # Check for main function - allow various formats
    assert "int main" in content or "int  main" in content, \
        "src/main.cpp must contain a main function"

    # Check for basic C++ structure
    assert "{" in content and "}" in content, \
        "src/main.cpp must have valid C++ function structure"

def test_cmake_configure_linux_gcc():
    """Verify cmake can configure the project with linux-gcc preset"""
    # Change to /app directory
    os.chdir(APP_DIR)

    # Try to configure with linux-gcc preset
    result = subprocess.run(
        ["cmake", "--preset", "linux-gcc"],
        capture_output=True,
        text=True
    )

    # Check if configuration succeeded
    assert result.returncode == 0, \
        f"CMake configuration failed for linux-gcc preset.\nStdout: {result.stdout}\nStderr: {result.stderr}"

    # Verify build directory was created
    build_dir = os.path.join(APP_DIR, "build", "linux-gcc")
    assert os.path.exists(build_dir), \
        f"Build directory not created at expected location: {build_dir}"

def test_cmake_build_linux_gcc():
    """Verify cmake can build the project with linux-gcc preset"""
    # Change to /app directory
    os.chdir(APP_DIR)

    # First configure (in case previous test was skipped)
    subprocess.run(
        ["cmake", "--preset", "linux-gcc"],
        capture_output=True,
        text=True
    )

    # Try to build with linux-gcc preset
    result = subprocess.run(
        ["cmake", "--build", "--preset", "linux-gcc"],
        capture_output=True,
        text=True
    )

    # Check if build succeeded
    assert result.returncode == 0, \
        f"CMake build failed for linux-gcc preset.\nStdout: {result.stdout}\nStderr: {result.stderr}"

    # Verify executable was created (might be in build/linux-gcc or build/linux-gcc/bin)
    build_dir = os.path.join(APP_DIR, "build", "linux-gcc")
    executable_found = False

    for root, dirs, files in os.walk(build_dir):
        if "auto-gui" in files:
            executable_found = True
            break

    assert executable_found, \
        f"Executable 'auto-gui' not found in build directory: {build_dir}"
