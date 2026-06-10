## Static Analysis Engine Setup

Set up a fully-featured Clang/LLVM static-analysis toolchain (version 17.x) so that `clang`, `clang++`, `scan-build`, `clang-tidy`, and LibTooling headers are available system-wide, then produce a verification report.

### Requirements

1. **Install the Clang 17 toolchain** with all static-analysis components:
   - `clang-17` and `clang++-17` compilers
   - `clang-tidy-17` (linter / static analyser)
   - `clang-tools-17` (includes `scan-build`)
   - `libclang-17-dev` (LibTooling headers and libraries)
   - `lld-17` (linker)
   - Set up alternatives or symlinks so that bare commands `clang`, `clang++`, `clang-tidy`, `scan-build`, and `lld` resolve to the version-17 binaries.

2. **Create a test C++ source file** at `/app/test_sample.cpp` with the following exact content:

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3, 4, 5};
    int sum = 0;
    for (auto i = 0; i < v.size(); i++) {
        sum += v[i];
    }
    std::cout << "Sum: " << sum << std::endl;
    return 0;
}
```

3. **Compile the test file** using `clang++` and produce a binary at `/app/test_sample_bin`. The binary must execute successfully and print `Sum: 15` to stdout.

4. **Run `clang-tidy`** on `/app/test_sample.cpp` and save the raw output (stdout and stderr combined) to `/app/clang_tidy_output.txt`.

5. **Generate a JSON verification report** at `/app/output.json` with the following structure:

```json
{
  "clang_version": "<full version string from `clang --version`, first line only>",
  "clang_tidy_version": "<full version string from `clang-tidy --version`, first line only>",
  "scan_build_available": true,
  "lld_available": true,
  "libclang_header_exists": true,
  "test_compile_success": true,
  "test_run_output": "Sum: 15",
  "clang_tidy_ran": true
}
```

Field specifications:
- `clang_version`: string — the first line of output from `clang --version`.
- `clang_tidy_version`: string — the first line of output from `clang-tidy --version`.
- `scan_build_available`: boolean — `true` if `scan-build` is found in PATH (i.e., `which scan-build` succeeds).
- `lld_available`: boolean — `true` if `lld` (or `ld.lld`) is found in PATH.
- `libclang_header_exists`: boolean — `true` if the file `/usr/lib/llvm-17/include/clang-c/Index.h` exists.
- `test_compile_success`: boolean — `true` if `/app/test_sample_bin` was produced and is executable.
- `test_run_output`: string — the exact stdout from running `/app/test_sample_bin`, trimmed of trailing newline.
- `clang_tidy_ran`: boolean — `true` if `/app/clang_tidy_output.txt` exists and is non-empty.

### Expected Output Files

| Path | Description |
|---|---|
| `/app/test_sample.cpp` | C++ test source file (exact content as above) |
| `/app/test_sample_bin` | Compiled executable binary |
| `/app/clang_tidy_output.txt` | Raw clang-tidy output |
| `/app/output.json` | JSON verification report |

### Constraints

- Use the official LLVM apt repository or system packages to obtain Clang 17. Building from source is not required.
- All version strings must contain `17`.
- The JSON report must be valid JSON with the exact keys listed above.
- The working directory is `/app`.
