## Building and Using a Custom Static Library with CMake

Create a C math utilities static library using CMake, build it, and link it into a separate test application. The entire project lives under `/app`.

### Project Structure

```
/app/
├── mathlib/
│   ├── CMakeLists.txt
│   ├── include/
│   │   └── mathutils.h
│   └── src/
│       └── mathutils.c
├── app/
│   ├── CMakeLists.txt
│   └── main.c
└── CMakeLists.txt          (top-level)
```

### Technical Requirements

- Language: C (C99 or later)
- Build system: CMake (minimum version 3.10)
- The library must be built as a static library (`.a` file)
- The top-level `CMakeLists.txt` must define the project name as `MathProject` and add both `mathlib` and `app` as subdirectories

### Library Specification (`mathlib`)

The header file `mathlib/include/mathutils.h` must declare the following four functions:

- `double math_add(double a, double b)` — returns `a + b`
- `double math_subtract(double a, double b)` — returns `a - b`
- `double math_multiply(double a, double b)` — returns `a * b`
- `double math_divide(double a, double b, int *error)` — returns `a / b`. If `b` is `0.0`, set `*error` to `1` and return `0.0`. Otherwise set `*error` to `0`.

The implementation goes in `mathlib/src/mathutils.c`.

The `mathlib/CMakeLists.txt` must:
- Create a static library target named `mathutils`
- Expose `mathlib/include` as a public include directory so consumers can use `#include "mathutils.h"`

### Test Application Specification (`app`)

`app/main.c` must:
1. Call all four library functions with the following test values and print results to stdout:
   - `math_add(10.5, 3.2)`
   - `math_subtract(10.5, 3.2)`
   - `math_multiply(4.0, 2.5)`
   - `math_divide(10.0, 3.0, &error)`
   - `math_divide(10.0, 0.0, &error)`
2. Print each result on its own line in the exact format:
   ```
   add: 13.700000
   subtract: 7.300000
   multiply: 10.000000
   divide: 3.333333
   divide_by_zero_error: 1
   ```
   Use `printf` with `%f` default formatting (6 decimal places) for numeric results. The divide-by-zero line prints the integer error flag.
3. Return exit code `0`.

The `app/CMakeLists.txt` must:
- Create an executable target named `math_app`
- Link against the `mathutils` static library target

### Build and Run

After all source files are in place, build the project from a `build` directory:

```
mkdir -p /app/build && cd /app/build && cmake .. && make
```

The built artifacts must include:
- A static library file at a path matching `/app/build/mathlib/libmathutils.a`
- An executable at a path matching `/app/build/app/math_app`

Run the application:
```
/app/build/app/math_app
```

The output must exactly match the five lines specified above.
