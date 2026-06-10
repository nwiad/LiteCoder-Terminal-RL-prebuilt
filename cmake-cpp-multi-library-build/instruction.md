## Build C++ Project with Modern CMake and Cross-Platform Toolchain

Configure and build a multi-library C++ project using modern CMake (3.20+), producing shared libraries, a main executable, install/export rules, a consumer project, and CPack packaging — all under `/app`.

### Project Structure

Create the following directory layout under `/app`:

```
/app/
├── CMakeLists.txt                  (root)
├── math_utils/
│   ├── CMakeLists.txt
│   ├── include/math_utils/
│   │   └── math_utils.h
│   └── src/
│       └── math_utils.cpp
├── string_utils/
│   ├── CMakeLists.txt
│   ├── include/string_utils/
│   │   └── string_utils.h
│   └── src/
│       └── string_utils.cpp
├── app/
│   ├── CMakeLists.txt
│   └── src/
│       └── main.cpp
├── consumer/
│   ├── CMakeLists.txt
│   └── main.cpp
└── .clang-tidy
```

### Technical Requirements

- Language: C++17 (`CMAKE_CXX_STANDARD 17`, with `CMAKE_CXX_STANDARD_REQUIRED ON`)
- Build system: CMake 3.20+ (`cmake_minimum_required(VERSION 3.20)`)
- Root project name: `Analytics`
- All builds performed on Linux (Ubuntu 22.04)

### Library Specifications

**MathUtils library** (`math_utils/`):
- Target name: `MathUtils`
- Built as a `SHARED` library
- Namespace for export: `MathUtils::MathUtils`
- Must expose at least two public functions declared in `math_utils.h`:
  - `int add(int a, int b);` — returns `a + b`
  - `int multiply(int a, int b);` — returns `a * b`

**StringUtils library** (`string_utils/`):
- Target name: `StringUtils`
- Built as a `SHARED` library
- Namespace for export: `StringUtils::StringUtils`
- Must expose at least two public functions declared in `string_utils.h`:
  - `std::string to_upper(const std::string& s);` — returns uppercase version of `s`
  - `std::string trim(const std::string& s);` — removes leading and trailing whitespace

### Main Application

- Target name: `analytics_app`
- Links against both `MathUtils` and `StringUtils`
- `main.cpp` must call at least one function from each library and print results to stdout
- The executable must return exit code 0 on success

### CMake Configuration Requirements

1. **Root CMakeLists.txt**:
   - Set `cmake_minimum_required(VERSION 3.20)`
   - `project(Analytics VERSION 1.0.0 LANGUAGES CXX)`
   - Enable `CMAKE_EXPORT_COMPILE_COMMANDS ON`
   - Set `CMAKE_POSITION_INDEPENDENT_CODE ON`
   - Use `add_subdirectory()` for each component

2. **Library CMakeLists.txt files**:
   - Use target-based commands (`target_include_directories`, `target_link_libraries`) with proper visibility (`PUBLIC`/`PRIVATE`)
   - Include `install(TARGETS ...)` and `install(EXPORT ...)` rules

3. **Install rules**:
   - Install prefix: `/app/install`
   - Headers installed to `include/`
   - Shared libraries installed to `lib/`
   - Executables installed to `bin/`
   - CMake export config installed to `lib/cmake/Analytics/`
   - The export set name must be `AnalyticsTargets`
   - Generate and install `AnalyticsConfig.cmake` (and optionally `AnalyticsConfigVersion.cmake`) so that `find_package(Analytics)` works from the install tree

### Build Instructions

Perform two out-of-source builds:

1. **Debug build**:
   ```
   cmake -S /app -B /app/build/Debug -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=/app/install
   cmake --build /app/build/Debug
   ```

2. **Release build + install**:
   ```
   cmake -S /app -B /app/build/Release -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/app/install
   cmake --build /app/build/Release
   cmake --install /app/build/Release
   ```

After install, the following paths must exist:
- `/app/install/bin/analytics_app`
- `/app/install/lib/libMathUtils.so`
- `/app/install/lib/libStringUtils.so`
- `/app/install/include/math_utils/math_utils.h`
- `/app/install/include/string_utils/string_utils.h`
- `/app/install/lib/cmake/Analytics/AnalyticsConfig.cmake`
- `/app/install/lib/cmake/Analytics/AnalyticsTargets.cmake`

The installed executable `/app/install/bin/analytics_app` must run successfully (exit code 0).

### Consumer Project

Create a standalone CMake project under `/app/consumer/` that:
- Uses `find_package(Analytics REQUIRED)`
- Links against `MathUtils::MathUtils` and `StringUtils::StringUtils`
- Target name: `consumer_app`
- Calls `add(2, 3)` from MathUtils and `to_upper("hello")` from StringUtils, printing results to stdout
- Build and run:
  ```
  cmake -S /app/consumer -B /app/build/consumer -DCMAKE_PREFIX_PATH=/app/install
  cmake --build /app/build/consumer
  ```
- `/app/build/consumer/consumer_app` must run successfully (exit code 0) and its stdout must contain `5` and `HELLO`.

### CPack Packaging

Add CPack configuration to the root `CMakeLists.txt`:
- `CPACK_GENERATOR` must include `TGZ` and `DEB`
- `CPACK_PACKAGE_NAME` set to `Analytics`
- Run from the Release build directory:
  ```
  cd /app/build/Release && cpack
  ```
- At least one `.tar.gz` file and one `.deb` file must be produced under `/app/build/Release/`.

### Static Analysis

- Provide a `/app/.clang-tidy` config file at the project root
- The config must enable at least the `modernize-*` and `readability-*` check groups
- `compile_commands.json` must be generated in each build directory (ensured by `CMAKE_EXPORT_COMPILE_COMMANDS ON`)
