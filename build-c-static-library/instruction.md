## Minimal C Static Library Build

Create a minimal, installable C static library (`libminimal.a`) with a public header, a Makefile, and a pkg-config file. All work is done under `/app`.

### Project Structure

```
/app/
├── include/minimal/math.h
├── src/math.c
├── minimal.pc
├── Makefile
└── test.c
```

### Technical Requirements

- Language: C (compiled with `gcc`)
- Build system: GNU Make

### Public Header (`include/minimal/math.h`)

The header must declare the following four functions with exactly these signatures:

```c
int minimal_add(int a, int b);
int minimal_sub(int a, int b);
int minimal_mul(int a, int b);
int minimal_div(int a, int b);
```

The header must include a standard include guard using `MINIMAL_MATH_H`.

### Implementation (`src/math.c`)

Implement all four functions declared in the header. `minimal_div` must perform integer division and return `0` when the divisor `b` is `0`.

### Makefile

The Makefile must support the following variables (overridable from the command line):

- `PREFIX` — defaults to `/usr/local`
- `CC` — defaults to `gcc`
- `CFLAGS` — must include at least `-Wall` and `-I include`
- `AR` — defaults to `ar`

Required targets:

| Target | Behavior |
|---|---|
| `all` (default) | Compile `src/math.c` into an object file under `build/` and archive it into `build/libminimal.a` |
| `install` | Copy `build/libminimal.a` to `$(PREFIX)/lib/`, `include/minimal/math.h` to `$(PREFIX)/include/minimal/math.h`, and `minimal.pc` to `$(PREFIX)/lib/pkgconfig/minimal.pc` |
| `clean` | Remove the `build/` directory |

The `build/` directory must be created automatically by the `all` target if it does not exist.

### pkg-config File (`minimal.pc`)

The file `minimal.pc` must contain at least the following fields:

- `prefix` set to `/usr/local`
- `libdir` set to `${prefix}/lib`
- `includedir` set to `${prefix}/include`
- `Name` set to `minimal`
- `Libs` referencing `-L${libdir} -lminimal`
- `Cflags` referencing `-I${includedir}`

### Test Program (`test.c`)

Write a program `test.c` that:

1. Includes `<minimal/math.h>` and `<stdio.h>`.
2. Calls all four library functions with sample arguments.
3. Prints results to stdout, one per line, in the exact format:

```
add: <result>
sub: <result>
mul: <result>
div: <result>
```

For example, calling `minimal_add(3, 4)`, `minimal_sub(10, 3)`, `minimal_mul(2, 5)`, `minimal_div(9, 3)` must produce:

```
add: 7
sub: 7
mul: 10
div: 3
```

### Build & Verification Workflow

1. `make` — produces `build/libminimal.a`.
2. `make install PREFIX=/app/local` — installs library, header, and `.pc` file under `/app/local`.
3. Compile and run `test.c` using pkg-config against the installed library:

```
gcc test.c $(pkg-config --cflags --libs /app/local/lib/pkgconfig/minimal.pc) -o test_app
./test_app
```

The test program must compile without errors and produce correct output.
