## Fix Broken Build System and Achieve Clean Compilation

You inherited a legacy C/C++ project located in `/app/project/`. The project has a broken build system using both Make and CMake. It contains multiple source files, hardcoded paths, outdated configurations, and various compilation issues. Your goal is to fix all build issues so the project compiles cleanly and produces working executables.

### Project Structure

The project is located at `/app/project/` and contains:
- A top-level `CMakeLists.txt`
- A `Makefile`
- Source files in `src/` (C and C++ files)
- Header files in `include/`
- A utility library in `lib/`

### Technical Requirements

- Language: C/C++ (compiled with `gcc`/`g++`)
- Build system: CMake (minimum version 3.10) as the primary build system
- The project must build successfully using:
  ```
  cd /app/project/build && cmake .. && make
  ```
- All necessary build tools and dependencies must be installed (cmake, gcc, g++, make, and any required libraries)

### Build Success Criteria

1. Running `cd /app/project/build && cmake ..` must complete with exit code 0.
2. Running `make` inside `/app/project/build/` must complete with exit code 0 and produce no compilation errors.
3. The build must produce the following executables:
   - `/app/project/build/mathtools` — a math utilities program
   - `/app/project/build/textproc` — a text processing program
4. `/app/project/build/mathtools` must run without crashing and exit with code 0 when invoked with no arguments.
5. `/app/project/build/textproc` must run without crashing and exit with code 0 when invoked with no arguments.
6. Running `/app/project/build/mathtools --version` must print a line containing the string `mathtools 1.0`.
7. Running `/app/project/build/textproc --version` must print a line containing the string `textproc 1.0`.

### Known Issues to Fix

The project has the following categories of problems that must be diagnosed and resolved:
- The `CMakeLists.txt` contains syntax errors and references to nonexistent paths
- Hardcoded absolute paths in source files and build configuration that do not exist on this system
- Missing `#include` directives in source files
- Mismatched function signatures between headers and implementations
- The `Makefile` references incorrect compiler flags and targets
- The `build/` directory may not exist and must be created
- Some source files use deprecated or invalid C/C++ syntax that modern compilers reject

### Output

After all fixes are applied, the directory `/app/project/build/` must contain the two executables listed above, built from the corrected source tree. No other output files are required.
