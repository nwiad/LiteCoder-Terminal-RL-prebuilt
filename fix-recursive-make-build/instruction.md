Fix the broken recursive make build system for a multi-module C project. The project has three modules (libcore, libutils, app) with broken Makefiles that cause "missing header" and "library not found" errors.

**Technical Requirements:**
- Language: C (compile with gcc)
- Build system: GNU Make (recursive make)
- Working directory: /app
- Final executable: /app/bin/app

**Project Structure:**
```
/app/
├── Makefile (top-level)
├── include/ (shared headers: core.h, utils.h)
├── libcore/ (Makefile, core.c) → builds lib/libcore.a
├── libutils/ (Makefile, utils.c) → builds lib/libutils.a
└── app/ (Makefile, main.c) → builds bin/app
```

**Build Requirements:**
1. Running `make` from /app must build all modules in correct dependency order
2. libcore must be built before libutils (libutils depends on libcore)
3. Both libraries must be built before app (app depends on both)
4. All modules must find headers in /app/include/
5. The app must link against both static libraries correctly

**Success Criteria:**
1. `make` command completes without errors
2. Executable /app/bin/app is created
3. Running `/app/bin/app` produces output and exits with code 0
4. Output must include "All tests completed successfully!"

**Current Issues:**
- Missing include paths preventing modules from finding shared headers
- Incorrect library linking order
- Top-level Makefile not exporting variables to sub-makes
- No explicit build dependencies between modules
