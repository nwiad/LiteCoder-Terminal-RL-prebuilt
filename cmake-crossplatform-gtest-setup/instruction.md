## Building a Cross-Platform CMake Project with Package Dependencies

Set up a cross-platform CMake build system that automatically fetches and compiles GoogleTest (v1.12.0), links it correctly, and compiles a simple unit test executable for both Linux and Windows (via MinGW cross-compiler) using a single `CMakeLists.txt` file.

### Project Structure

Create the following directory structure under `/app/`:

```
/app/
├── CMakeLists.txt
├── build.sh
├── mingw-toolchain.cmake
├── src/
│   └── mathlib.cpp
├── include/
│   └── mathlib.h
└── tests/
    └── test_mathlib.cpp
```

### Technical Requirements

- Language: C++ (C++14 or later standard)
- Build system: CMake 3.14 or later
- Testing framework: GoogleTest v1.12.0, fetched via CMake's `FetchContent` module
- Cross-compiler: MinGW-w64 (`x86_64-w64-mingw32-g++`)
- The project must define a CMake project named `MathLib`

### Library Specification (`src/mathlib.cpp` and `include/mathlib.h`)

Create a simple C++ library in a namespace called `mathlib` that provides at least the following functions:

- `int add(int a, int b)` — returns the sum of two integers
- `int subtract(int a, int b)` — returns the difference (a - b)
- `int multiply(int a, int b)` — returns the product of two integers
- `double divide(double a, double b)` — returns the quotient (a / b); throws `std::invalid_argument` if `b` is zero

The header file must use an include guard. The library must be built as a static library target named `mathlib`.

### Unit Tests (`tests/test_mathlib.cpp`)

Write GoogleTest-based unit tests that cover:

- Basic addition, subtraction, and multiplication with positive integers
- Operations involving zero
- Operations involving negative numbers
- Division by zero throws `std::invalid_argument`

The test executable target must be named `mathlib_tests`. Tests must be registered with `add_test()` via CMake's `enable_testing()` so they can be run with `ctest`.

### CMakeLists.txt Requirements

The single top-level `/app/CMakeLists.txt` must:

1. Set the minimum CMake version to 3.14 or later
2. Declare the project as `MathLib`
3. Use `FetchContent` to download GoogleTest at tag `release-1.12.0` from `https://github.com/google/googletest.git`
4. Build the static library target `mathlib` from sources in `src/` with headers in `include/`
5. Build the test executable `mathlib_tests` from `tests/test_mathlib.cpp`, linked against both `mathlib` and `GTest::gtest_main`
6. Call `enable_testing()` and register the test executable with `add_test()`

### MinGW Cross-Compilation Toolchain (`mingw-toolchain.cmake`)

Create a CMake toolchain file at `/app/mingw-toolchain.cmake` that:

- Sets `CMAKE_SYSTEM_NAME` to `Windows`
- Sets `CMAKE_C_COMPILER` to `x86_64-w64-mingw32-gcc`
- Sets `CMAKE_CXX_COMPILER` to `x86_64-w64-mingw32-g++`
- Configures `CMAKE_FIND_ROOT_PATH_MODE_PROGRAM` to `NEVER`
- Configures `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY` and `CMAKE_FIND_ROOT_PATH_MODE_INCLUDE` to `ONLY`

### Build Script (`build.sh`)

Create an executable bash script at `/app/build.sh` that automates both build configurations:

1. **Linux native build**: Configure and build in `/app/build-linux/`, then run tests via `ctest --test-dir /app/build-linux/`
2. **Windows cross-compilation build**: Configure and build in `/app/build-windows/` using the MinGW toolchain file (`-DCMAKE_TOOLCHAIN_FILE=../mingw-toolchain.cmake`)

The script must:
- Use `#!/bin/bash` shebang
- Exit on error (`set -e`)
- Print a clear message before each build step (e.g., "Building for Linux...", "Building for Windows...")
- Create the build directories if they don't exist

### Verification Criteria

- `cmake` configures successfully for the Linux build in `/app/build-linux/`
- `make` (or `cmake --build`) compiles the Linux build without errors
- `ctest` in the Linux build directory runs all tests and they pass
- `cmake` configures successfully for the Windows cross-compilation build in `/app/build-windows/` using the MinGW toolchain
- `make` (or `cmake --build`) compiles the Windows cross-compilation build without errors
- The Windows build produces a `mathlib_tests.exe` executable in `/app/build-windows/` (or a subdirectory thereof)
