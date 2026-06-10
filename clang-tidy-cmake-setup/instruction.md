## Static Analysis with Clang-Tidy

Set up a C++ project with CMake that integrates Clang-Tidy for static analysis. The project must contain source files that initially have common C++ code quality issues, which you must then fix so the project builds cleanly with zero Clang-Tidy warnings.

### Technical Requirements

- Language: C++17
- Build system: CMake (minimum version 3.14)
- Static analysis tool: clang-tidy
- Working directory: /app

### Project Structure

Create the following project layout:

```
/app/
├── CMakeLists.txt
├── .clang-tidy
├── src/
│   ├── main.cpp
│   └── utils.cpp
└── include/
    └── utils.h
```

### CMakeLists.txt Requirements

- Set the project name to `static_analysis_demo`.
- Set the C++ standard to C++17.
- Enable `CMAKE_EXPORT_COMPILE_COMMANDS` to `ON`.
- Integrate clang-tidy via `CMAKE_CXX_CLANG_TIDY` so that clang-tidy runs automatically during the build.
- Define an executable target named `demo` that compiles `src/main.cpp` and `src/utils.cpp`.
- Add `include/` as an include directory for the target.

### .clang-tidy Configuration

Provide a `.clang-tidy` file at the project root (`/app/.clang-tidy`) that enables at least the following check categories:

- `bugprone-*`
- `modernize-*`
- `readability-*`

The `WarningsAsErrors` field must be set to `*` (treat all warnings as errors).

### Source File Requirements

**include/utils.h**: Declare a header file with a proper include guard (or `#pragma once`). It must declare:
- A function `int computeSum(int a, int b);`
- A function `std::string formatMessage(const std::string& name, int value);`

**src/utils.cpp**: Implement the two functions declared in `utils.h`.

**src/main.cpp**: A `main()` function that:
- Calls `computeSum` and `formatMessage` from `utils.h`.
- Prints results to standard output.
- Returns 0 on success.

### Build and Clean Analysis

The project must build successfully with CMake and clang-tidy enabled:

```
cd /app && mkdir -p build && cd build && cmake .. && cmake --build . 2>&1
```

The build output must contain zero clang-tidy warnings or errors. The resulting executable `/app/build/demo` must run and exit with code 0.
