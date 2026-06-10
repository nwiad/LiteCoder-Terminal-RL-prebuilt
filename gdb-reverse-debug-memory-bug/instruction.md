## Advanced Debugging with GDB: Reverse Execution and Time-Travel

Build a C application that contains a specific memory corruption bug, debug it using GDB's advanced features (reverse execution, watchpoints), then produce a fixed version and a structured debugging report.

### Technical Requirements

- Language: C (compiled with `gcc`)
- Tools: GDB with reverse debugging support
- Working directory: `/app`

### Step 1: Create the Buggy Program

Create `/app/buggy.c` containing a C program that meets ALL of the following:

1. Defines a struct named `Record` with at least these fields:
   - `int id`
   - `char name[32]`
   - `double value`
2. Allocates a dynamic array of `Record` structs (at least 10 elements) using `malloc`.
3. Contains a loop that iterates over the array and populates each element.
4. Introduces a **heap buffer overflow bug**: during the loop, at least one write goes past the allocated array boundary (e.g., writing to index `N` when only indices `0..N-1` are valid).
5. After the loop, prints a summary line to stdout in the exact format:
   ```
   Processed <COUNT> records
   ```
   where `<COUNT>` is the number of records the loop intended to process (including the out-of-bounds write).
6. The program must compile without errors using:
   ```
   gcc -g -O0 -o buggy buggy.c
   ```

### Step 2: Create the Fixed Program

Create `/app/fixed.c` which is a corrected version of `buggy.c`:

1. The heap buffer overflow must be eliminated (all array accesses stay within bounds).
2. The `Record` struct definition must remain identical.
3. The program must still allocate a dynamic array of `Record` structs using `malloc` and populate them in a loop.
4. The program must print the same summary format to stdout:
   ```
   Processed <COUNT> records
   ```
   where `<COUNT>` is the number of records actually processed (all within bounds).
5. The program must free all dynamically allocated memory before exiting.
6. The program must compile without errors using:
   ```
   gcc -g -O0 -o fixed fixed.c
   ```
7. The program must exit with return code `0`.

### Step 3: Compile Both Programs

Run the following commands to produce the executables:

```
gcc -g -O0 -o /app/buggy /app/buggy.c
gcc -g -O0 -o /app/fixed /app/fixed.c
```

### Step 4: Create the Debugging Report

Create `/app/debug_report.txt` documenting the GDB debugging session. The report must contain ALL of the following sections and keywords (case-insensitive):

1. A section titled `BUG DESCRIPTION` that explains the memory corruption bug.
2. A section titled `GDB COMMANDS` that lists the GDB commands used during the debugging session. This section must include at least the following GDB commands (each on its own line, as they would be typed in GDB):
   - `reverse-continue` or `rc`
   - `watch` (with a memory expression)
   - `break` (with a location)
   - `run`
   - `record`
3. A section titled `ROOT CAUSE` that identifies the exact source file and line number where the out-of-bounds write occurs, in the format: `buggy.c:<LINE_NUMBER>`.
4. A section titled `FIX DESCRIPTION` that explains how the bug was fixed in `fixed.c`.

### Output Summary

| File | Description |
|---|---|
| `/app/buggy.c` | C source with heap buffer overflow bug |
| `/app/fixed.c` | Corrected C source with bug fixed |
| `/app/buggy` | Compiled buggy executable |
| `/app/fixed` | Compiled fixed executable |
| `/app/debug_report.txt` | GDB debugging session report |
