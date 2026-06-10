Build MySQL 8.4.2 LTS from source with jemalloc as the memory allocator for improved performance in write-heavy workloads.

## Technical Requirements

- Operating System: Linux (Ubuntu/Debian-based or RHEL/CentOS-based)
- MySQL Version: 8.4.2 LTS (source tarball)
- Memory Allocator: jemalloc (latest stable version)
- Build Tools: cmake 3.x, gcc/g++, make
- Required Libraries: OpenSSL development headers, ncurses, libtirpc

## Build Specifications

**MySQL Configuration:**
- Install prefix: `/app/mysql`
- Build type: Release
- Enable jemalloc linking via `-DWITH_JEMALLOC=ON` or appropriate linker flags
- Disable unnecessary features to speed up build (e.g., `-DWITH_UNIT_TESTS=OFF`)

**jemalloc Configuration:**
- Install prefix: `/app/jemalloc`
- Build as shared library
- Ensure library is in system library path or use `LD_LIBRARY_PATH`

## Verification Requirements

After successful build, the following must be verifiable:

1. **Binary Linkage Check:**
   - The `mysqld` binary at `/app/mysql/bin/mysqld` must be dynamically linked against jemalloc
   - Verify using `ldd` command showing jemalloc library dependency

2. **Build Artifacts:**
   - Create deployment package: `/app/mysql-8.4.2-jemalloc.tar.gz`
   - Package must contain the compiled MySQL installation from `/app/mysql`

3. **Runtime Verification:**
   - MySQL server must start successfully with jemalloc active
   - Verify jemalloc is loaded by checking process memory maps or environment

## Output Files

- `/app/mysql/bin/mysqld` - Main MySQL server binary
- `/app/mysql-8.4.2-jemalloc.tar.gz` - Deployment package
- `/app/build_verification.txt` - Text file containing output of `ldd /app/mysql/bin/mysqld` showing jemalloc linkage

## Success Criteria

- MySQL 8.4.2 compiles without errors
- `mysqld` binary is linked against jemalloc (confirmed via `ldd`)
- Server starts and accepts connections
- Deployment tarball is created and contains all necessary binaries
