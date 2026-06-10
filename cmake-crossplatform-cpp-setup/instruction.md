## Cross-Platform C/C++ Development Environment Setup with CMake

Set up a cross-platform C/C++ build system using modern CMake practices, including toolchain files for cross-compilation targets, a sample library/executable project, a unified build script, and automated testing.

### Technical Requirements

- Language: C++17
- Build system: CMake (minimum version 3.16)
- All project files must be created under `/app/`

### Project Structure

Create the following files and directories:

```
/app/
├── CMakeLists.txt              # Root CMake configuration
├── cmake/
│   ├── toolchain-linux.cmake   # Linux native toolchain file
│   ├── toolchain-mingw64.cmake # Windows cross-compilation toolchain file (MinGW-w64)
│   └── toolchain-macos.cmake   # macOS cross-compilation toolchain file (osxcross)
├── src/
│   ├── CMakeLists.txt          # Source subdirectory CMake config
│   ├── mathlib.h               # Library header
│   ├── mathlib.cpp             # Library implementation
│   └── main.cpp                # Executable using the library
├── tests/
│   ├── CMakeLists.txt          # Test subdirectory CMake config
│   └── test_mathlib.cpp        # Unit tests for the library
├── build.sh                    # Unified build script
└── report.json                 # Build summary report
```

### Library Specification (`mathlib`)

The library `mathlib` must be built as a static library named `mathlib` and expose the following functions in a `mathlib` namespace:

1. `int factorial(int n)` — Returns the factorial of n. Returns 1 for n=0. Returns -1 for negative input.
2. `double average(const std::vector<double>& values)` — Returns the arithmetic mean. Returns 0.0 for an empty vector.
3. `bool is_prime(int n)` — Returns true if n is a prime number, false otherwise. Numbers less than 2 are not prime.
4. `std::string to_upper(const std::string& input)` — Returns the input string converted to uppercase ASCII.

All functions must be declared in `mathlib.h` and implemented in `mathlib.cpp`.

### Executable (`main`)

`main.cpp` must produce an executable named `mathapp` that:
- Prints `factorial(5)=120` to stdout
- Prints `average=3` for the input values {1.0, 2.0, 3.0, 4.0, 5.0} (printed as an integer-truncated value)
- Prints `is_prime(7)=true`
- Prints `to_upper=HELLO WORLD` for input `"hello world"`
- Each output on its own line, exactly in the format shown above

### CMake Configuration

The root `CMakeLists.txt` must:
- Set `cmake_minimum_required` to VERSION 3.16
- Set the project name to `CrossPlatformDemo` with language CXX
- Set the C++ standard to 17 and make it required (`CMAKE_CXX_STANDARD_REQUIRED ON`)
- Add `src` and `tests` as subdirectories
- Enable testing via `enable_testing()`

The `src/CMakeLists.txt` must:
- Build `mathlib` as a STATIC library from `mathlib.cpp`
- Build `mathapp` executable from `main.cpp`, linked against `mathlib`

The `tests/CMakeLists.txt` must:
- Build a `test_mathlib` executable from `test_mathlib.cpp`, linked against `mathlib`
- Register it as a CTest test with `add_test(NAME test_mathlib COMMAND test_mathlib)`

### Toolchain Files

Each toolchain file in `cmake/` must set at minimum:
- `CMAKE_SYSTEM_NAME` (Linux, Windows, or Darwin respectively)
- `CMAKE_C_COMPILER` and `CMAKE_CXX_COMPILER` to appropriate compiler paths
- `CMAKE_FIND_ROOT_PATH_MODE_PROGRAM`, `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY`, and `CMAKE_FIND_ROOT_PATH_MODE_INCLUDE`

The `toolchain-mingw64.cmake` must set `CMAKE_SYSTEM_NAME` to `Windows` and use compiler names containing `w64-mingw32`.
The `toolchain-macos.cmake` must set `CMAKE_SYSTEM_NAME` to `Darwin`.
The `toolchain-linux.cmake` must set `CMAKE_SYSTEM_NAME` to `Linux`.

### Unit Tests (`test_mathlib.cpp`)

The test executable must test all four library functions and return exit code 0 if all tests pass, non-zero otherwise. It must not depend on any external testing framework — use simple assert-style checks with `<cassert>` or manual comparison with return codes.

### Build Script (`build.sh`)

`build.sh` must be an executable Bash script that accepts a target platform as its first argument: `linux`, `windows`, or `macos`.

Behavior:
- For `linux`: configure and build the project natively in `/app/build/linux/` using the linux toolchain file, then run `ctest` in that build directory.
- For `windows`: configure the project in `/app/build/windows/` using the mingw64 toolchain file (build may fail if cross-compiler is not installed — that is acceptable).
- For `macos`: configure the project in `/app/build/macos/` using the macos toolchain file (build may fail if cross-compiler is not installed — that is acceptable).
- If no argument or an invalid argument is given, print `Usage: build.sh <linux|windows|macos>` to stderr and exit with code 1.
- The script must exit with code 0 on successful build (for linux target on a Linux host).

### Build Report (`report.json`)

Create `/app/report.json` with the following JSON structure:

```json
{
  "project_name": "CrossPlatformDemo",
  "cmake_minimum_version": "3.16",
  "cpp_standard": 17,
  "targets": {
    "library": "mathlib",
    "executable": "mathapp",
    "test": "test_mathlib"
  },
  "platforms": ["linux", "windows", "macos"],
  "toolchain_files": {
    "linux": "cmake/toolchain-linux.cmake",
    "windows": "cmake/toolchain-mingw64.cmake",
    "macos": "cmake/toolchain-macos.cmake"
  }
}
```
