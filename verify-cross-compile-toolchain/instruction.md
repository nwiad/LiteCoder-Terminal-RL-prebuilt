## Cross-Compilation Toolchain Verification Suite

Create an automated verification suite that validates compiler toolchains by compiling test programs, inspecting the resulting ELF binaries, and producing a structured JSON report. The suite must be driven by a configuration file describing the targets and be runnable with a single command.

### Technical Requirements

- Language: Bash (the main driver script) + C (test programs)
- Input: `/app/targets.json` — a JSON file describing toolchain targets to verify
- Output: `/app/report.json` — a structured verification report
- Main script: `/app/verify-toolchains.sh` (must be executable)
- The script must be fully non-interactive (no user prompts)

### Input Format (`/app/targets.json`)

A JSON array of target objects. Each target has:

| Field | Type | Description |
|---|---|---|
| `name` | string | Human-readable target name |
| `compiler` | string | Path or command name of the C compiler |
| `flags` | string | Compiler flags to pass |
| `expected_machine` | string | Expected ELF machine type substring (as shown by `readelf -h`, e.g. `"X86-64"`, `"386"`) |

Example:
```json
[
  {
    "name": "x86-64-native",
    "compiler": "gcc",
    "flags": "-march=x86-64 -O2",
    "expected_machine": "X86-64"
  }
]
```

### Test Program

The suite must create a minimal C test program (at `/app/test_program.c`) that:
- Contains at least one function besides `main`
- Returns 0 from `main`

### Verification Steps (per target)

For each target defined in `targets.json`, the script must perform these checks in order:

1. **Compiler existence check**: Verify the compiler command is found (e.g., via `which` or `command -v`).
2. **Compilation check**: Compile `test_program.c` with the specified flags to produce an ELF object or executable. The output binary for each target must be placed at `/app/build/<name>.out` (where `<name>` is the target's `name` field).
3. **ELF machine type check**: Use `readelf -h` on the produced binary and verify the `Machine:` line contains the `expected_machine` string.
4. **Disassembly check**: Use `objdump -d` on the produced binary and verify it contains at least one disassembled instruction.

Each check produces a `"pass"` or `"fail"` status.

### Output Format (`/app/report.json`)

A JSON object with the following structure:

```json
{
  "summary": {
    "total_targets": 1,
    "passed": 1,
    "failed": 0
  },
  "targets": [
    {
      "name": "x86-64-native",
      "compiler_found": "pass",
      "compilation": "pass",
      "elf_machine_check": "pass",
      "disassembly_check": "pass",
      "overall": "pass"
    }
  ]
}
```

Field details:
- `summary.total_targets`: number of targets in the input
- `summary.passed`: number of targets where `overall` is `"pass"`
- `summary.failed`: number of targets where `overall` is `"fail"`
- Each entry in `targets` has the target `name` and the four check results as `"pass"` or `"fail"`
- `overall` is `"pass"` only if all four checks are `"pass"`; otherwise `"fail"`

### Early-Abort Flag

When invoked as `./verify-toolchains.sh -e`, the script must stop processing further targets after the first target whose `overall` result is `"fail"`. Targets not evaluated due to early abort must still appear in the `targets` array with all check fields set to `"skip"` and `overall` set to `"skip"`. The summary counts must reflect only evaluated targets (`"skip"` targets count toward neither `passed` nor `failed`, but do count toward `total_targets`).

### Exit Code

- Exit `0` if all evaluated targets pass
- Exit `1` if any evaluated target fails
