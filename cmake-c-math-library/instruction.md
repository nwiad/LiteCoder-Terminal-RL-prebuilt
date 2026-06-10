## Cross-Platform C Library Build System

Create a portable CMake build system for a C math library called **libquickmath** that supports both shared and static library builds, proper header installation, and package config integration.

### Technical Requirements

- Language: C (C99 or later)
- Build system: CMake (minimum version 3.10)
- Working directory: `/app`

### Project Directory Structure

Create the following layout under `/app`:

```
/app/
├── CMakeLists.txt
├── include/
│   └── quickmath/
│       └── quickmath.h
├── src/
│   └── quickmath.c
├── examples/
│   └── main.c
└── cmake/
    └── quickmath-config.cmake.in
```

### Library API

The public header `/app/include/quickmath/quickmath.h` must:

1. Define an export/import macro named `QUICKMATH_API` that:
   - On Windows: expands to `__declspec(dllexport)` when building the library (when `QUICKMATH_EXPORTS` is defined), and `__declspec(dllimport)` when consuming it.
   - On non-Windows (or when building statically): expands to nothing.
2. Declare exactly these four functions with `QUICKMATH_API`:
   - `double quickmath_add(double a, double b);`
   - `double quickmath_subtract(double a, double b);`
   - `double quickmath_multiply(double a, double b);`
   - `double quickmath_divide(double a, double b, int *error);`

For `quickmath_divide`: if `b` is `0.0`, set `*error` to `1` and return `0.0`. Otherwise set `*error` to `0` and return the result.

### Library Implementation

`/app/src/quickmath.c` must implement all four functions as declared in the header.

### CMake Configuration

`/app/CMakeLists.txt` must:

1. Set the minimum CMake version to `3.10` and define the project named `quickmath` with language `C`.
2. Provide a CMake option named `BUILD_SHARED_LIBS` (default `ON`) to toggle between shared and static library builds.
3. Provide a CMake option named `QUICKMATH_BUILD_EXAMPLES` (default `ON`) to toggle building the example program.
4. Create a library target named `quickmath` from the source files.
5. When building as a shared library, define `QUICKMATH_EXPORTS` as a compile definition on the target (private).
6. Set the target's public include directories so that:
   - During build: `${CMAKE_CURRENT_SOURCE_DIR}/include`
   - After install: `include`
7. Define install rules:
   - The library to `lib/`
   - The header directory `include/quickmath/` to `include/`
   - Export the target set named `quickmathTargets`
8. Configure and install a package config file from `cmake/quickmath-config.cmake.in` to `lib/cmake/quickmath/`.
9. When `QUICKMATH_BUILD_EXAMPLES` is `ON`, build an executable target named `quickmath_example` from `examples/main.c` and link it against the `quickmath` library.

### Package Config Template

`/app/cmake/quickmath-config.cmake.in` must use `@PACKAGE_INIT@` and include the exported targets file `quickmathTargets.cmake` from the same directory.

### Example Program

`/app/examples/main.c` must:

1. Include `quickmath/quickmath.h`.
2. Demonstrate calling all four library functions.
3. Print results to stdout, with each operation result on its own line.
4. Demonstrate the divide-by-zero error handling case.

### Build Verification

The project must successfully configure and build with the following commands from a build directory:

```
mkdir -p /app/build && cd /app/build
cmake .. -DCMAKE_INSTALL_PREFIX=/app/install
make
```

And install with:

```
cd /app/build && make install
```

After installation, the following files must exist:
- `/app/install/lib/libquickmath.so` (shared build) or `/app/install/lib/libquickmath.a` (static build)
- `/app/install/include/quickmath/quickmath.h`
- `/app/install/lib/cmake/quickmath/quickmath-config.cmake`

The example program `/app/build/quickmath_example` must run and exit with code `0`.
