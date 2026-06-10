## Building LLDB from Source with Python Bindings and Code Signing

Create a complete set of build automation scripts for building LLDB from the LLVM project source on Ubuntu 22.04, with Python bindings enabled and code signing configured for debugging system processes.

### Technical Requirements

- Language: Bash (scripts), CMake (configuration)
- All output files must be placed under `/app/`

### Deliverables

You must produce the following files:

1. `/app/install_deps.sh` — A Bash script that installs all system dependencies and build tools required for compiling LLVM/LLDB with Python bindings on Ubuntu 22.04. Requirements:
   - Must start with `#!/bin/bash` and use `set -e`
   - Must use `apt-get` to install packages
   - Must include at minimum: `cmake`, `ninja-build`, `python3-dev`, `swig`, `libxml2-dev`, `libedit-dev`, `libncurses5-dev`, `clang`, `g++`
   - Must run `apt-get update` before installing

2. `/app/build_lldb.sh` — A Bash script that clones the LLVM repository and builds LLDB. Requirements:
   - Must start with `#!/bin/bash` and use `set -e`
   - Must clone from `https://github.com/llvm/llvm-project.git` with `--depth 1`
   - Must create a build directory and invoke `cmake` with at least the following settings:
     - Generator: Ninja (`-G Ninja`)
     - Build type: Release
     - `LLVM_ENABLE_PROJECTS` must include `clang;lldb`
     - `LLDB_ENABLE_PYTHON` set to `ON`
     - `LLDB_ENABLE_LIBEDIT` set to `ON`
     - `LLDB_ENABLE_CURSES` set to `ON`
   - Must invoke the build step using `ninja` or `cmake --build`
   - Must invoke an install step using `ninja install` or `cmake --install`

3. `/app/codesign_setup.sh` — A Bash script that creates a self-signed certificate and signs the LLDB binary. Requirements:
   - Must start with `#!/bin/bash` and use `set -e`
   - Must generate a certificate or signing key using `openssl`
   - Must contain a command that signs a binary (e.g., using `codesign`, `sbsign`, or `gpg --sign` or similar signing mechanism)
   - Must reference the `lldb` binary path for signing

4. `/app/verify_install.sh` — A Bash script that verifies the LLDB installation and Python bindings. Requirements:
   - Must start with `#!/bin/bash` and use `set -e`
   - Must check that the `lldb` binary exists and is executable (e.g., `lldb --version`)
   - Must verify Python bindings by running a Python command that imports `lldb` (e.g., `python3 -c "import lldb; ..."`)

5. `/app/test_debug.sh` — A Bash script that compiles a sample C++ program and tests debugging it with LLDB. Requirements:
   - Must start with `#!/bin/bash` and use `set -e`
   - Must contain or create a sample C++ source file (inline via heredoc or a separate `.cpp` file)
   - The C++ code must include a `main` function and at least one variable assignment
   - Must compile the C++ file with debug symbols (`-g` flag)
   - Must invoke `lldb` in batch/non-interactive mode to run a debugging session on the compiled binary (e.g., using `--batch`, `-o`, or `-s` flags)

6. `/app/lldb_api_script.py` — A Python script that uses the LLDB Python API. Requirements:
   - Must import `lldb`
   - Must call `lldb.SBDebugger.Create()` to create a debugger instance
   - Must create a target from an executable (using `CreateTarget` or `CreateTargetWithFileAndArch`)
   - Must set at least one breakpoint (using `BreakpointCreateByName` or `BreakpointCreateByLocation`)
   - Must print or output information about the debugger, target, or breakpoint
   - Must call `lldb.SBDebugger.Destroy()` to clean up the debugger instance

All `.sh` files must be executable (have execute permissions).
