## Cross-Platform Static Library Migration with CMake & pkg-config

Port a C++ library project to Linux, producing both shared and static library targets using CMake and pkg-config. The project must depend on `libpng`, `zlib`, and `libjpeg`, and include a working build script and a C example that links against the static library.

### Technical Requirements

- Language: C++ (library source), C (example program)
- Build system: CMake (minimum version 3.10)
- Dependency discovery: pkg-config
- Platform: Linux (Ubuntu)
- All project files live under `/app/`

### Project Structure

Create the following files under `/app/`:

```
/app/
├── CMakeLists.txt
├── build.sh
├── example.c
├── include/
│   └── mysdk/
│       └── mysdk.h
└── src/
    └── mysdk.cpp
```

### File Specifications

#### 1. `CMakeLists.txt`

- Set `cmake_minimum_required` to at least version 3.10.
- Define a project named `mysdk`.
- Use `pkg_check_modules` (from `PkgConfig`) to find `libpng`, `zlib`, and `libjpeg`.
- Define two library targets from the same source (`src/mysdk.cpp`):
  - `mysdk_shared` — a SHARED library with output name `mysdk` (i.e., produces `libmysdk.so`).
  - `mysdk_static` — a STATIC library with output name `mysdk` (i.e., produces `libmysdk.a`).
- Both targets must include the `include/` directory as a public include path.
- Both targets must link against the dependencies found via pkg-config.
- Provide an `install` rule that installs headers, the shared library, and the static library.

#### 2. `src/mysdk.cpp` and `include/mysdk/mysdk.h`

- The header `mysdk.h` must declare at least one C-linkage function (i.e., wrapped in `extern "C"`) so that `example.c` can call it. The function must be named `mysdk_info` with signature:
  ```c
  const char* mysdk_info(void);
  ```
- `mysdk.cpp` must `#include` headers from all three dependencies (`png.h`, `zlib.h`, `jpeglib.h`) and implement `mysdk_info`. The function must return a string that contains the runtime version identifiers of all three libraries (png, zlib, jpeg). The exact format is up to you, but the returned string must contain the substrings `png`, `zlib` (or `deflate`), and `jpeg` (or `libjpeg`) in some form.

#### 3. `build.sh`

- Must be executable (`chmod +x`).
- Must use `pkg-config` to verify that `libpng`, `zlib`, and `libjpeg` are available before invoking CMake. If any dependency is missing, the script must exit with a non-zero status and print an error message to stderr.
- Must perform an out-of-source build in a directory named `build/` (i.e., `/app/build/`).
- Must invoke `cmake` to configure and then build the project.
- After a successful build, both `/app/build/libmysdk.so` (or `libmysdk.so.*`) and `/app/build/libmysdk.a` must exist.

#### 4. `example.c`

- Must `#include "mysdk/mysdk.h"`.
- Must contain a `main` function that calls `mysdk_info()`, prints the returned string to stdout, and exits with return code 0.
- Must be compilable and linkable against the static library `libmysdk.a` and its transitive dependencies to produce a working executable.

### Build & Verification

Running the following sequence from `/app/` must succeed:

1. `bash build.sh` — exits with code 0 and produces both `libmysdk.a` and `libmysdk.so` (or versioned variant) inside `/app/build/`.
2. Compiling the example against the static library (e.g., using gcc with the static archive and pkg-config flags) must produce a runnable executable.
3. Running the compiled example must print a string containing version information for png, zlib, and jpeg, and exit with code 0.

### Constraints

- Do not hardcode library paths; always discover them via pkg-config or CMake's PkgConfig module.
- The static archive `libmysdk.a` must have no unresolved symbols from the project's own source (transitive dependency symbols are acceptable).
- `build.sh` must be a POSIX-compatible shell script (use `#!/bin/bash` or `#!/bin/sh`).
