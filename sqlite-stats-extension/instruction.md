## Build a Custom SQLite Extension with Statistics Functions

Create a loadable SQLite extension in C that provides three aggregate statistical functions: `median`, `mode`, and `stdev` (standard deviation). The extension must be compiled as a shared library and be loadable into SQLite.

### Technical Requirements

- Language: C
- Build system: A `Makefile` at `/app/Makefile`
- Source file: `/app/stats_ext.c`
- Compiled output: `/app/stats_ext.so` (shared library)
- Test script: `/app/test_stats.sql`
- SQLite development headers and gcc must be used for compilation
- Running `make` in `/app` must produce `stats_ext.so` without errors

### Function Specifications

All three functions are **aggregate functions** that operate on a group of numeric values passed via SQL queries.

1. **`median(X)`** — Returns the median value of all non-NULL values in the group.
   - For an odd number of values, return the middle value.
   - For an even number of values, return the average of the two middle values.
   - Returns NULL if all inputs are NULL or the group is empty.

2. **`mode(X)`** — Returns the mode (most frequently occurring value) of all non-NULL values in the group.
   - If multiple values share the highest frequency, return the smallest among them.
   - Returns NULL if all inputs are NULL or the group is empty.

3. **`stdev(X)`** — Returns the **population** standard deviation of all non-NULL values in the group.
   - Population standard deviation: `sqrt(sum((xi - mean)^2) / N)`
   - Returns NULL if all inputs are NULL or the group is empty.
   - Returns `0.0` if only one non-NULL value exists.

### Numerical Precision

- All return values must be REAL (double-precision floating point).
- Results should be accurate to at least 6 decimal places.

### SQL Test Script (`/app/test_stats.sql`)

The test script must:
- Create a table named `test_data` with at least a column `value REAL`.
- Insert sample rows including at least one NULL value.
- Run queries that invoke `median(value)`, `mode(value)`, and `stdev(value)` on the table.
- The script must be executable via: `sqlite3 < test_stats.sql` (after loading the extension).

### Extension Entry Point

The shared library must export the standard SQLite extension entry point so it can be loaded with:
```sql
.load ./stats_ext
```

### Edge Case Handling

- NULL inputs must be silently ignored (not counted or included in calculations).
- If a group contains zero non-NULL values, all three functions must return NULL.
