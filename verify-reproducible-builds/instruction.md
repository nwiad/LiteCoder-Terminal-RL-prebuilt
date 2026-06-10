## Reproducible Build Verification Tool

Create a command-line tool that verifies reproducible builds by comparing compilation outputs between different environments and generates a detailed comparison report.

**Technical Requirements:**
- Language: Python 3.x
- Input: Configuration file at `/app/config.json`
- Output: Comparison report at `/app/report.json`

**Input Specification:**

The configuration file `/app/config.json` contains:
```json
{
  "source_dir": "/app/source",
  "build_configs": [
    {
      "name": "env1",
      "compiler": "gcc",
      "version": "9.4.0",
      "flags": "-O2 -Wall"
    },
    {
      "name": "env2",
      "compiler": "gcc",
      "version": "11.2.0",
      "flags": "-O2 -Wall"
    }
  ],
  "output_binary": "libsample.so"
}
```

**Output Specification:**

Generate `/app/report.json` with the following structure:
```json
{
  "reproducible": true,
  "builds": [
    {
      "name": "env1",
      "binary_path": "/app/builds/env1/libsample.so",
      "sha256": "abc123...",
      "size_bytes": 12345,
      "build_success": true
    },
    {
      "name": "env2",
      "binary_path": "/app/builds/env2/libsample.so",
      "sha256": "abc123...",
      "size_bytes": 12345,
      "build_success": true
    }
  ],
  "comparison": {
    "all_hashes_match": true,
    "all_sizes_match": true,
    "differences": []
  }
}
```

**Requirements:**

1. Read build configuration from `/app/config.json`
2. For each build configuration, compile the source code in `/app/source` using the specified compiler and flags
3. Store build outputs in `/app/builds/{config_name}/`
4. Calculate SHA256 hash and file size for each compiled binary
5. Compare all build outputs and determine if builds are reproducible (all hashes match)
6. Generate detailed report at `/app/report.json` with build results and comparison data
7. Set `reproducible` to `true` only if all builds succeeded and all binary hashes match
8. If hashes don't match, populate `differences` array with mismatched build names

**Error Handling:**

- If a build fails, set `build_success` to `false` for that build and set overall `reproducible` to `false`
- If `/app/config.json` is missing or invalid, exit with error code 1
- If source directory doesn't exist, exit with error code 1
