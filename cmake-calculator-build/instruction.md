## Cross-Platform Dependency Resolver

Create a portable CMake build system for a command-line calculator C/C++ project that resolves dependencies and compiles across multiple platforms.

### Technical Requirements

- **Language**: C or C++ (C++11 or later if using C++)
- **Build System**: CMake 3.10 or later
- **Project Structure**: Source files should be in `/app/src/`, headers in `/app/include/`
- **Executable Name**: `calculator`
- **Build Directory**: `/app/build/`

### Project Specifications

**Calculator Functionality:**
The calculator executable must accept command-line arguments in the format:
```
./calculator <operation> <operand1> <operand2>
```

Supported operations: `add`, `subtract`, `multiply`, `divide`

**Example:**
```
./calculator add 5 3
Output: 8
```

### CMake Requirements

Your `CMakeLists.txt` at `/app/CMakeLists.txt` must:

1. Set minimum CMake version (3.10+)
2. Define project name and language
3. Specify C++ standard (if using C++) or C standard
4. Configure include directories properly
5. Add executable target linking all source files
6. Set compiler flags for warnings and optimization
7. Define build output directory as `/app/build/`

### File Structure

Expected project layout:
```
/app/
├── CMakeLists.txt
├── src/
│   └── [source files: .c or .cpp]
├── include/
│   └── [header files: .h or .hpp]
└── build/
    └── [generated build files and executable]
```

### Build Process

The build system must support:
```bash
cd /app
mkdir -p build
cd build
cmake ..
cmake --build .
```

After successful build, the executable `/app/build/calculator` must be runnable and produce correct arithmetic results for all supported operations.

### Error Handling

- Division by zero should output an error message and return non-zero exit code
- Invalid operations should output usage information
- Invalid number formats should be handled gracefully
