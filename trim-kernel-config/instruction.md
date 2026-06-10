## Reproducible Kernel Config Builder

Create a tool that deterministically processes a Linux kernel configuration file into a trimmed, minimal version while maintaining bootability guarantees.

**Technical Requirements:**
- Language: Bash script or Python 3.x
- Input file: `/app/input_config` (kernel configuration in standard Linux .config format)
- Output file: `/app/output_config` (trimmed configuration)
- Metadata file: `/app/metadata.json` (statistics and verification data)

**Input Specification:**

The input file `/app/input_config` contains a Linux kernel configuration with:
- Comment lines starting with `#`
- Configuration entries in format `CONFIG_SYMBOL=value` where value can be `y`, `m`, `n`, or quoted strings
- Blank lines for readability

Example excerpt:
```
# CONFIG_LOCALVERSION is not set
CONFIG_KERNEL_GZIP=y
CONFIG_DEFAULT_HOSTNAME="(none)"
CONFIG_SWAP=y
# CONFIG_SYSVIPC is not set
```

**Output Requirements:**

1. **Trimmed Configuration** (`/app/output_config`):
   - Valid Linux kernel .config format
   - Reduced set of CONFIG symbols while maintaining essential options
   - Deterministic output (same input always produces identical output)
   - Preserve all `=y` symbols that are hardware-critical or boot-essential
   - Remove redundant or default-value symbols

2. **Metadata File** (`/app/metadata.json`):
   ```json
   {
     "original_size_bytes": <integer>,
     "trimmed_size_bytes": <integer>,
     "original_symbol_count": <integer>,
     "trimmed_symbol_count": <integer>,
     "symbols_removed": <integer>,
     "deterministic_hash": "<sha256 hash of output_config>"
   }
   ```

**Processing Requirements:**

- Parse CONFIG symbols and their values correctly
- Identify essential symbols (those set to `y` or `m` in original config)
- Remove symbols that are:
  - Set to default values
  - Dependencies that can be auto-selected
  - Redundant given other enabled options
- Preserve symbols that are:
  - Explicitly enabled (`=y` or `=m`)
  - Required for hardware support
  - Boot-critical options
- Maintain valid .config syntax in output
- Generate deterministic output (sort symbols alphabetically if needed)

**Edge Cases:**

- Handle symbols with string values (e.g., `CONFIG_LOCALVERSION="-custom"`)
- Preserve tristate symbols (`y`/`m`/`n`) correctly
- Handle comment-only lines and blank lines
- Deal with symbols that have dependencies on other symbols
