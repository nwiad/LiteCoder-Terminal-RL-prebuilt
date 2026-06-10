## Task: Build Lua 5.4 from Source with Shared Library Support

Compile Lua 5.4 from its official source tarball with shared-library support enabled and install it to a custom prefix at /opt/lua54.

## Technical Requirements

- **Language/Tools:** Bash, Make, C compiler (gcc/clang)
- **Source:** Official Lua 5.4.7 tarball from https://www.lua.org/ftp/lua-5.4.7.tar.gz
- **Installation prefix:** /opt/lua54
- **Build type:** Shared library (not static)
- **Working directory:** /app

## Implementation Requirements

1. **Download and verify source:**
   - Download Lua 5.4.7 tarball to /app
   - Verify SHA-256 checksum matches official value from lua.org
   - Extract tarball in /app

2. **Configure build:**
   - Modify Makefile to set installation prefix to /opt/lua54
   - Enable shared library compilation (liblua.so on Linux, liblua.dylib on macOS)
   - Ensure interpreter links against shared library

3. **Build and test:**
   - Compile Lua interpreter, compiler, and shared library
   - Run upstream test suite to verify build
   - All tests must pass

4. **Install and verify:**
   - Install to /opt/lua54 with standard hierarchy: bin/, include/, lib/, man/, share/
   - Verify lua interpreter dynamically links to shared library (use ldd or otool)
   - Create test script at /app/hello.lua that prints "Hello from Lua 5.4!"
   - Execute test script using /opt/lua54/bin/lua to confirm installation works

## Expected Output Structure

```
/opt/lua54/
├── bin/
│   ├── lua
│   └── luac
├── include/
│   └── *.h files
├── lib/
│   └── liblua.so* (or liblua.dylib on macOS)
├── man/
│   └── man1/
└── share/
    └── lua/
```

## Validation Criteria

- /opt/lua54/bin/lua executable exists and runs
- Shared library exists in /opt/lua54/lib/
- lua interpreter dynamically links to the shared library (verified via ldd/otool)
- Test script /app/hello.lua executes successfully and produces expected output
- All upstream tests pass
