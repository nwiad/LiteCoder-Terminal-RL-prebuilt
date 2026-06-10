## Build System Compatibility Fix

Fix compatibility issues in a mixed C/C++ codebase so it compiles cleanly with both GCC and Clang using a CMake build system.

### Technical Requirements

- Language: C11 / C++17
- Build system: CMake (minimum version 3.10)
- Compilers: Must compile with both GCC and Clang
- Working directory: /app

### Project Structure

The project at /app must contain the following source files and a CMakeLists.txt:

```
/app/
├── CMakeLists.txt
├── include/
│   ├── mathutils.h
│   ├── strutils.h
│   └── config.h
├── src/
│   ├── main.c
│   ├── mathutils.c
│   └── strutils.cpp
└── build/          (created during build)
```

### Source File Specifications

**include/config.h** — Project-wide configuration header. Defines a version string macro `PROJECT_VERSION` as `"1.0.0"` and an integer macro `MAX_BUFFER_SIZE` as `1024`.

**include/mathutils.h** — Header for C math utilities. Declares:
- `int factorial(int n);`
- `double safe_divide(double numerator, double denominator, int *error_flag);`

**include/strutils.h** — Header for C++ string utilities. Declares (with proper `extern "C"` linkage for C interop):
- `int count_words(const char *str);`
- `int is_palindrome(const char *str);`

**src/mathutils.c** — C source implementing:
- `factorial(n)`: returns factorial of n. Returns -1 for negative input. `factorial(0)` returns 1.
- `safe_divide(numerator, denominator, error_flag)`: returns `numerator / denominator`. If denominator is 0.0, sets `*error_flag = 1` and returns 0.0. Otherwise sets `*error_flag = 0`.

**src/strutils.cpp** — C++ source implementing:
- `count_words(str)`: returns the number of whitespace-separated words. Returns 0 for NULL or empty string.
- `is_palindrome(str)`: returns 1 if the string is a case-insensitive palindrome (ignoring spaces), 0 otherwise. Returns 0 for NULL or empty string.

**src/main.c** — C main program that:
1. Prints `Project Version: <PROJECT_VERSION>` to stdout.
2. Prints `factorial(5) = 120` (calling the factorial function).
3. Prints `safe_divide(10.0, 3.0) = <result>` with result formatted to 4 decimal places.
4. Prints `safe_divide(1.0, 0.0) = error` when division by zero is detected.
5. Prints `count_words("hello world test") = 3` (calling the count_words function).
6. Prints `is_palindrome("racecar") = 1` (calling the is_palindrome function).
7. Returns 0 on success.

### CMakeLists.txt Requirements

- Project name: `compat_project`
- Set C standard to C11 and C++ standard to C++17, both required (not optional)
- Enable strict warnings: `-Wall -Wextra -Wpedantic` for both C and C++ targets
- Build a single executable named `compat_project` from all sources in `src/`
- Add `include/` to the include path
- The CMake configuration must work without modification for both GCC and Clang toolchains

### Build & Output Verification

The project must:

1. Configure and build cleanly from `/app/build` using:
   ```
   cd /app/build && cmake .. && cmake --build .
   ```
2. Produce zero warnings and zero errors with both GCC and Clang.
3. The built executable `/app/build/compat_project` must run and produce this exact output:
   ```
   Project Version: 1.0.0
   factorial(5) = 120
   safe_divide(10.0, 3.0) = 3.3333
   safe_divide(1.0, 0.0) = error
   count_words("hello world test") = 3
   is_palindrome("racecar") = 1
   ```
