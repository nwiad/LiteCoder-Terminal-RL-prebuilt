## Task: Autotools-based Legacy C Library Modernization

Convert a legacy C library (`libmini`) from a handwritten Makefile to a modern autotools-based build system with proper packaging and installation support.

### Technical Requirements

- **Language**: C (C99 or later)
- **Build System**: GNU Autotools (autoconf, automake, libtool)
- **Working Directory**: /app
- **Input**: Existing C source files (*.c, *.h) and legacy Makefile in /app
- **Output**: Complete autotools build system that supports standard workflow

### Implementation Requirements

1. **Autotools Infrastructure**
   - Create `configure.ac` with library metadata (name: libmini, version: 1.0.0)
   - Create `Makefile.am` for building the library
   - Provide bootstrap/autogen script to generate configure

2. **Library Build Configuration**
   - Use libtool to build both shared and static libraries
   - Set library version info (current:revision:age format)
   - Install headers to appropriate include directory
   - Support standard targets: all, install, clean, distclean

3. **pkg-config Support**
   - Create `libmini.pc.in` template
   - Configure to install .pc file to pkgconfig directory
   - Include proper Libs and Cflags fields

4. **Platform Detection**
   - Detect standard C headers and functions in configure.ac
   - Handle platform-specific compilation requirements

5. **Testing Support**
   - Implement `make check` target
   - Include at least one test program that links against the library
   - Test program should verify basic library functionality

6. **Distribution Support**
   - Enable `make dist` to create release tarball
   - Tarball should be named libmini-1.0.0.tar.gz
   - Include all necessary files for rebuilding

### Expected Workflow

After implementation, the following sequence must work:
```
./bootstrap  # or ./autogen.sh
./configure --prefix=/usr/local
make
make check
make install
make dist
```

### Verification Requirements

After `make install`, the following must be present:
- Shared library with proper soname in lib directory
- Static library (.a) in lib directory
- Header files in include directory
- pkg-config file (libmini.pc) in pkgconfig directory

A downstream program must be able to compile using:
```
gcc program.c $(pkg-config --cflags --libs libmini) -o program
```
