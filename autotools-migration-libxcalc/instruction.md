Convert the legacy "libxcalc" C library (located in `/app/libxcalc/`) from its monolithic Makefile-based build to the GNU Autotools build system (autoconf, automake, libtool) with pkg-config integration.

Run `python3 setup.py` first to generate the legacy source tree under `/app/libxcalc/`.

## Source Tree Layout (after setup)

```
libxcalc/
├── include/libxcalc/libxcalc.h
├── src/libxcalc.c
├── tests/test_xcalc.c
├── Makefile          (legacy, to be replaced)
├── README.md
├── CHANGELOG
└── LICENSE
```

## Requirements

### 1. `configure.ac`

Create `/app/libxcalc/configure.ac` with:
- `AC_INIT` using package name `libxcalc`, version `2.3.1`, and bug-report email `bugs@libxcalc.org`
- `AM_INIT_AUTOMAKE` to enable automake
- `LT_INIT` to enable libtool for shared/static library building
- `AC_PROG_CC` to detect the C compiler
- `AC_CONFIG_HEADERS([config.h])` for generated config header
- `AC_CONFIG_FILES` listing all `Makefile.am`-generated Makefiles (at minimum: `Makefile`, `src/Makefile`, `include/Makefile`)
- `AC_CHECK_LIB([m], [sin])` to check for the math library
- `AC_OUTPUT` at the end

### 2. Top-level `Makefile.am`

Create `/app/libxcalc/Makefile.am` with:
- `SUBDIRS` listing at least `src` and `include`
- `pkgconfigdir` variable set to `$(libdir)/pkgconfig`
- `pkgconfig_DATA` set to `libxcalc.pc`
- `EXTRA_DIST` including at least `README.md`, `CHANGELOG`, and `LICENSE`

### 3. `src/Makefile.am`

Create `/app/libxcalc/src/Makefile.am` with:
- `lib_LTLIBRARIES = libxcalc.la` to build the library via libtool
- `libxcalc_la_SOURCES` set to `libxcalc.c`
- `libxcalc_la_CPPFLAGS` including `-I$(top_srcdir)/include`
- `libxcalc_la_LDFLAGS` with `-version-info` using a libtool-compatible version triple (current:revision:age format)
- `libxcalc_la_LIBADD` including `-lm`

### 4. `include/Makefile.am`

Create `/app/libxcalc/include/Makefile.am` with:
- A public header installation rule that installs `libxcalc/libxcalc.h` into `$(includedir)/libxcalc/`
- Use `libxcalcincludedir` and `libxcalcinclude_HEADERS` (or equivalent nobase_ pattern) so the header is installed under the `libxcalc/` subdirectory

### 5. `libxcalc.pc.in` (pkg-config template)

Create `/app/libxcalc/libxcalc.pc.in` with:
- `prefix=@prefix@`
- `exec_prefix=@exec_prefix@`
- `libdir=@libdir@`
- `includedir=@includedir@`
- A `[libxcalc]` section name (the `Name:` field must be `libxcalc`)
- `Version: @PACKAGE_VERSION@`
- `Libs:` field containing at least `-L${libdir} -lxcalc`
- `Cflags:` field containing at least `-I${includedir}`

The `configure.ac` must list `libxcalc.pc` in `AC_CONFIG_FILES` so it is generated from `libxcalc.pc.in`.

### 6. Header Visibility Fix

The existing `libxcalc.h` uses `LIBXCALC_EXPORT` but never defines it. Add a definition so the library compiles. The macro must resolve to `__attribute__((visibility("default")))` when building with GCC (or compatible), and to nothing otherwise. This can be done by editing the header directly or via a compiler flag in `src/Makefile.am` — either approach is acceptable, as long as the source compiles.

### 7. Build Verification

After creating all Autotools files, the following command sequence must succeed without errors inside `/app/libxcalc/`:

```
autoreconf --install --force
./configure
make
```

- `make` must produce a libtool-managed shared library (`.la` file) under `src/` (e.g., `src/libxcalc.la`)
- `make install DESTDIR=/tmp/xcalc_install` must install:
  - The library into `DESTDIR`'s `lib/` path
  - The header into `DESTDIR`'s `include/libxcalc/` path
  - The `.pc` file into `DESTDIR`'s `lib/pkgconfig/` path

### Constraints

- Do not modify the existing C source logic in `src/libxcalc.c` (fixing the `LIBXCALC_EXPORT` macro is allowed)
- Do not modify the public API declared in `libxcalc.h` (adding the `LIBXCALC_EXPORT` macro definition is allowed)
- The legacy `Makefile` may be removed or left in place; it must not interfere with the Autotools build
- All generated Autotools files must be placed inside `/app/libxcalc/`
