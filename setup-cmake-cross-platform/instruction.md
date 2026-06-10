## Task: Auto-GUI C++ Build Environment Setup

Set up a cross-platform build environment for a C++ GUI framework named "Auto-GUI" that compiles on Linux (GCC), Windows (MinGW-w64), and macOS (Clang) using CMake.

**Technical Requirements:**
- CMake version: ≥ 3.25
- Target platforms: Linux (GCC), Windows (MinGW-w64), macOS (Clang)
- Build system: CMake with CMakePresets.json
- C++ standard: C++17 or higher

**Required Files:**

1. `/app/CMakeLists.txt` - Main CMake configuration file that:
   - Sets project name to "Auto-GUI"
   - Defines C++ standard requirement
   - Creates an executable target named "auto-gui"
   - Links necessary system libraries for GUI support

2. `/app/CMakePresets.json` - CMake presets configuration with at least three presets:
   - `linux-gcc` - Linux build using GCC
   - `windows-mingw` - Windows build using MinGW-w64
   - `macos-clang` - macOS build using Clang

3. `/app/src/main.cpp` - Minimal C++ source file with a main function

**Build Configuration Requirements:**

Each preset in CMakePresets.json must specify:
- `generator`: Appropriate build system (e.g., "Ninja", "Unix Makefiles")
- `binaryDir`: Build output directory (e.g., `${sourceDir}/build/${presetName}`)
- `cacheVariables`: Must include `CMAKE_BUILD_TYPE` and `CMAKE_CXX_COMPILER`

**Success Criteria:**

The build environment should allow running:
```
cmake --preset <preset-name>
cmake --build --preset <preset-name>
```

Where `<preset-name>` is one of: `linux-gcc`, `windows-mingw`, or `macos-clang`.
