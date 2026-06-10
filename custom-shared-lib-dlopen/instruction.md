## Building and Using a Custom Shared Library with Dynamic Symbol Export Control

Create a custom C shared library with selectively exported symbols and a test program that dynamically loads it using `dlopen`/`dlsym`. The library simulates a plugin system where only designated functions are visible externally.

### Technical Requirements

- Language: C (C99 or later)
- Build system: CMake (minimum version 3.10)
- Platform: Linux (GCC)
- Working directory: `/app`

### File Structure

Create the following files under `/app`:

- `plugin_api.h` — Header file with symbol visibility macros and function declarations
- `plugin_lib.c` — Shared library source implementing public and private functions
- `CMakeLists.txt` — Build configuration for the shared library and test program
- `test_loader.c` — Test program that dynamically loads the library

### Shared Library Specifications

#### Symbol Visibility Macros (`plugin_api.h`)

Define two macros:
- `PLUGIN_EXPORT` — Marks a function as publicly visible (exported)
- `PLUGIN_LOCAL` — Marks a function as hidden (not exported)

#### Library Functions (`plugin_lib.c`)

Implement the following functions in the shared library (library target name: `plugin`):

**Exported (public) functions — must be visible in the dynamic symbol table:**
- `int plugin_init(void)` — Returns `1` to indicate successful initialization. Prints: `plugin_init: initialized`
- `int plugin_get_version(void)` — Returns the integer `2`. Prints: `plugin_get_version: 2`
- `const char* plugin_get_name(void)` — Returns the string `"sample_plugin"`. Prints: `plugin_get_name: sample_plugin`
- `int plugin_compute(int a, int b)` — Returns `a + b`. Prints: `plugin_compute: <result>` (where `<result>` is the sum)
- `void plugin_shutdown(void)` — Prints: `plugin_shutdown: done`

**Hidden (private) functions — must NOT be visible in the dynamic symbol table:**
- `int internal_helper(int x)` — Returns `x * 2`
- `void internal_log(const char* msg)` — Prints the message to stdout

The `plugin_compute` function must internally call `internal_helper` on the sum before returning (i.e., it returns `internal_helper(a + b)`, so the actual return value is `(a + b) * 2`).

#### CMake Build (`CMakeLists.txt`)

- Project name: `plugin_system`
- Build the shared library as target `plugin` (producing `libplugin.so`)
- Set default symbol visibility to hidden (`-fvisibility=hidden`)
- Build the test program as target `test_loader`, linking with `dl`
- Use `CMAKE_POSITION_INDEPENDENT_CODE ON` for the library

### Test Program (`test_loader.c`)

The test program must:

1. Accept one command-line argument: the path to the shared library (e.g., `./libplugin.so`). If no argument is provided, print `Usage: test_loader <library_path>` to stderr and exit with code `1`.

2. Use `dlopen` to load the library. On failure, print `Error: cannot load library: <dlerror message>` to stderr and exit with code `1`.

3. Use `dlsym` to look up and call each exported function in this order:
   - `plugin_init` — call it and print: `plugin_init returned: <value>`
   - `plugin_get_version` — call it and print: `plugin_get_version returned: <value>`
   - `plugin_get_name` — call it and print: `plugin_get_name returned: <value>`
   - `plugin_compute(3, 4)` — call with arguments 3 and 4, print: `plugin_compute returned: <value>`
   - `plugin_shutdown` — call it

4. Attempt to look up the hidden symbol `internal_helper` using `dlsym`. Since it should not be exported, print: `internal_helper: symbol not found (expected)` when `dlsym` returns NULL.

5. Call `dlclose` and exit with code `0` on success.

For any `dlsym` failure on an exported function, print `Error: cannot find symbol <name>: <dlerror message>` to stderr and exit with code `1`.

### Build and Run

The project must build successfully with:
```
cd /app && mkdir -p build && cd build && cmake .. && make
```

The test program must run successfully with:
```
cd /app/build && ./test_loader ./libplugin.so
```

### Symbol Verification

Running `nm -D /app/build/libplugin.so` on the built library must show:
- `plugin_init`, `plugin_get_version`, `plugin_get_name`, `plugin_compute`, and `plugin_shutdown` as defined (exported) symbols (symbol type `T`)
- `internal_helper` and `internal_log` must NOT appear in the dynamic symbol table output
