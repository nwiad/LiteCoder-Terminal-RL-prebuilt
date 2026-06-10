## CMake Compiler Swap

Configure a C++ project to dynamically switch between GCC and Clang compilers using CMake presets and a custom Python script.

### Technical Requirements

- Language/Tools: C++, CMake (>= 3.21 for presets support), Python 3, GCC, Clang
- Working directory: `/app`
- Ensure GCC (`g++`), Clang (`clang++`), CMake, and `make` (or `ninja`) are installed

### Project Structure

Create the following files under `/app`:

```
/app/
├── CMakeLists.txt
├── CMakePresets.json
├── switch_compiler.py
├── src/
│   ├── mylib.cpp
│   └── mylib.h
└── app/
    └── main.cpp
```

### C++ Project

1. `src/mylib.h` and `src/mylib.cpp`: Define a library with at least one function `std::string get_compiler_info()` that returns a string identifying the compiler and version used at compile time (e.g., using `__GNUC__`, `__clang__`).
2. `app/main.cpp`: An executable that links against the library, calls `get_compiler_info()`, and prints the result to stdout in the format:
   ```
   Compiler: <compiler_name> <version>
   ```
   where `<compiler_name>` is either `GCC` or `Clang`.

### CMakeLists.txt

- Project name: `CompilerSwap`
- Build the library from `src/` as a static library named `mylib`.
- Build the executable from `app/main.cpp`, linked against `mylib`.
- The minimum required CMake version must be 3.21 or higher.

### CMakePresets.json

Create a `CMakePresets.json` at `/app/CMakePresets.json` with at least two configure presets:

- `gcc-release`: Uses GCC (`g++`) as the C++ compiler, build type `Release`, build directory `build/gcc-release`.
- `clang-release`: Uses Clang (`clang++`) as the C++ compiler, build type `Release`, build directory `build/clang-release`.

Each preset must explicitly set `CMAKE_CXX_COMPILER` to the appropriate compiler path or name.

### Python Script: switch_compiler.py

Create `/app/switch_compiler.py` that automates the build process:

- Usage: `python3 switch_compiler.py <preset_name>` where `<preset_name>` is one of the preset names defined in `CMakePresets.json` (e.g., `gcc-release` or `clang-release`).
- The script must:
  1. Run `cmake --preset <preset_name>` to configure the project.
  2. Run `cmake --build --preset <preset_name>` (or build from the preset's build directory) to compile.
  3. Run the resulting executable automatically after a successful build.
  4. Print a summary line to stdout: `Build completed with preset: <preset_name>`
  5. Exit with code 0 on success, non-zero on failure.
- If an invalid preset name is given, the script must print an error message containing the text `Invalid preset` to stderr and exit with a non-zero exit code.

### Build Outputs

- Building with `gcc-release` preset produces the executable at `build/gcc-release/app/main` (or a path under `build/gcc-release/`).
- Building with `clang-release` preset produces the executable at `build/clang-release/app/main` (or a path under `build/clang-release/`).
- Both executables must run successfully and print the `Compiler: ...` line identifying the correct compiler used.

### Verification

After setup, the following commands must succeed when run from `/app`:

```bash
python3 switch_compiler.py gcc-release
python3 switch_compiler.py clang-release
```

Each invocation must:
- Complete without errors (exit code 0)
- Produce a working executable in the respective build directory
- The gcc-release executable output must contain `GCC`
- The clang-release executable output must contain `Clang`
