## LLVM 17 Debug Build with Address Sanitizer & Custom Pass

Build a debug-enabled LLVM/Clang 17 toolchain with Address Sanitizer (ASan) support and a loadable custom LLVM pass, then package the result.

### Environment

- The LLVM 17 source tarball is already present at `/root/llvm-project-17.0.6.src.tar.xz`.
- A demo LLVM pass source file is at `/app/demo_pass/DemoPrintPass.cpp`. This pass prints every function name it encounters during compilation (printing to stderr in the format `DemoPass: <function_name>` for each function).
- A corresponding CMakeLists.txt for the demo pass is at `/app/demo_pass/CMakeLists.txt`.

### Requirements

1. **Install build dependencies** required for building LLVM (cmake, ninja-build, python3, zlib, etc.).

2. **Unpack** the LLVM 17 source tarball from `/root/llvm-project-17.0.6.src.tar.xz`.

3. **Configure and build** LLVM/Clang with CMake using the following settings:
   - Build type: `Debug`
   - Install prefix: `/opt/llvm17-asan`
   - `LLVM_ENABLE_ASSERTIONS=ON`
   - `LLVM_USE_SANITIZER=Address` (ASan enabled for the compiler itself)
   - `LLVM_ENABLE_RTTI=ON`
   - `LLVM_ENABLE_EH=ON`
   - `BUILD_SHARED_LIBS=ON`
   - `LLVM_EXPERIMENTAL_TARGETS_TO_BUILD=WebAssembly`
   - `LLVM_ENABLE_PROJECTS` must include at least `clang` and `compiler-rt`
   - Generator: Ninja

4. **Install** the built toolchain into `/opt/llvm17-asan` using ninja.

5. **Build the demo LLVM pass** from `/app/demo_pass/` as a shared object (`.so` file). Place the resulting shared object at `/opt/llvm17-asan/lib/DemoPrintPass.so`.

6. **Sanity-check compilation**: Write a minimal C++ test program to `/app/test_program.cpp` that contains at least two functions (including `main`). Compile it using the newly built `/opt/llvm17-asan/bin/clang++` with ASan enabled (`-fsanitize=address`) and produce the binary at `/app/test_program`.

7. **Verify ASan is active**: Run `/app/test_program` and confirm Address Sanitizer is linked. The output of `ldd /app/test_program` or `nm -D /app/test_program` should reference ASan-related symbols, or running with `ASAN_OPTIONS=help=1` should produce ASan help output on stderr.

8. **Verify the demo pass**: Compile `/app/test_program.cpp` using the new clang++ while loading the demo pass via `-fplugin=/opt/llvm17-asan/lib/DemoPrintPass.so` (or the appropriate `-fpass-plugin` flag). Redirect stderr to `/app/demo_pass_output.txt`. This file must contain lines matching the pattern `DemoPass: <function_name>` for each function in the test program.

9. **Package**: Create a compressed archive of the entire `/opt/llvm17-asan` install tree at `/root/llvm17-asan.tar.xz` using `tar -cJf`.

### Output Artifacts

| Artifact | Path |
|---|---|
| Installed toolchain | `/opt/llvm17-asan/` |
| clang++ binary | `/opt/llvm17-asan/bin/clang++` |
| Demo pass shared object | `/opt/llvm17-asan/lib/DemoPrintPass.so` |
| Test C++ source | `/app/test_program.cpp` |
| Compiled test binary | `/app/test_program` |
| Demo pass output log | `/app/demo_pass_output.txt` |
| Final archive | `/root/llvm17-asan.tar.xz` |

### Verification Criteria

- `/opt/llvm17-asan/bin/clang++` exists and is executable.
- `/opt/llvm17-asan/bin/clang++ --version` outputs a string containing `clang version 17`.
- `BUILD_SHARED_LIBS` was used: `/opt/llvm17-asan/lib/` contains `.so` shared library files.
- `/opt/llvm17-asan/lib/DemoPrintPass.so` exists and is a valid shared object.
- `/app/test_program` exists, is executable, and was compiled with ASan (references to `asan` appear in its linked libraries or symbols).
- `/app/demo_pass_output.txt` contains at least two lines matching the pattern `DemoPass: ` (one per function in the test program, including `main`).
- `/root/llvm17-asan.tar.xz` exists and is a valid xz-compressed tar archive containing the toolchain.
- The CMake cache at the build directory contains `LLVM_ENABLE_ASSERTIONS:BOOL=ON`, `LLVM_USE_SANITIZER:STRING=Address`, `LLVM_ENABLE_RTTI:BOOL=ON`, `LLVM_ENABLE_EH:BOOL=ON`, and `CMAKE_BUILD_TYPE:STRING=Debug`.
