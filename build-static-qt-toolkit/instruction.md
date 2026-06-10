## Build an Optimized Static Qt 6.7.1 Toolkit — Build Script and Configuration

Create a complete, production-ready shell script and supporting configuration to compile a fully static Qt 6.7.1 toolkit for Linux, with SQLite, OpenSSL, and commercial-grade optimization flags suitable for redistributable desktop apps.

### Technical Requirements

- Language: Bash (the main build script)
- Output files:
  - `/app/build_qt_static.sh` — The main build orchestration script (must be executable)
  - `/app/qt_build_config.json` — A JSON manifest describing the build configuration and expected outputs

### Script Requirements (`build_qt_static.sh`)

The script must be a valid, well-structured Bash script that performs the following steps in order. Each step must be clearly delimited with a comment header (e.g., `# Step 1: Install dependencies`).

1. **Install system dependencies** — Use `apt-get` to install all packages required for a static Qt 6.7.1 build (at minimum: `build-essential`, `cmake`, `ninja-build`, `python3`, `perl`, `libssl-dev`, `libsqlite3-dev`, `pkg-config`, `libfontconfig1-dev`, `libxcb*-dev`).

2. **Download Qt 6.7.1 source** — Download the official Qt 6.7.1 source tarball from `https://download.qt.io/official_releases/qt/6.7/6.7.1/single/qt-everywhere-src-6.7.1.tar.xz`. Verify the download using SHA-256 checksum. The expected SHA-256 hash must be stored in a variable named `QT_SHA256`.

3. **Configure Qt** — Invoke the Qt `configure` script with flags that satisfy ALL of the following:
   - Static build (`-static`)
   - Release mode (`-release`)
   - Prefix set to `/opt/qt-6.7.1-static`
   - OpenSSL linked statically (`-openssl-linked`)
   - SQLite enabled as a built-in plugin (`-sql-sqlite`)
   - Link-Time Optimization enabled (`-ltcflag` or equivalent CMake LTO option)
   - Size optimization (`-optimize-size`)
   - The following modules must be explicitly skipped: `qtwebengine`, `qt3d`, `qtquick3d`, `qtmultimedia`
   - Platform set to `linux-g++` or use the CMake generator `Ninja`

4. **Build** — Run the build using `cmake --build` or `ninja` with parallel jobs set to `$(nproc)`.

5. **Install** — Run `cmake --install` or equivalent to install into the prefix directory.

6. **Strip libraries** — Strip debug symbols from all `.a` files under the install prefix using `strip --strip-debug`.

7. **Smoke test** — Compile a minimal Qt Widgets application (inline or from a `.cpp` file) that:
   - Opens a `QSqlDatabase` with the SQLite driver
   - Creates a `QNetworkAccessManager` (to verify SSL linkage)
   - Prints "smoke-test-passed" to stdout on success

8. **Package** — Create a tarball named `qt-6.7.1-static-linux-x86_64.tar.xz` from the install prefix directory, placed at `/opt/qt-6.7.1-static-linux-x86_64.tar.xz`.

9. **Cleanup** — Remove the source and build directories to minimize disk usage.

The script must:
- Use `set -euo pipefail` at the top.
- Define variables for: `QT_VERSION="6.7.1"`, `QT_SHA256`, `QT_PREFIX="/opt/qt-6.7.1-static"`, `BUILD_DIR`, `SRC_DIR`.
- Exit with code 0 on success and non-zero on any failure.

### Configuration Manifest (`qt_build_config.json`)

A JSON file with the following exact top-level keys:

```json
{
  "qt_version": "6.7.1",
  "build_type": "static",
  "build_mode": "release",
  "install_prefix": "/opt/qt-6.7.1-static",
  "optimization": {
    "lto": true,
    "optimize_size": true,
    "strip_debug": true
  },
  "features": {
    "openssl": "linked",
    "sqlite": "built-in",
    "skipped_modules": ["qtwebengine", "qt3d", "qtquick3d", "qtmultimedia"]
  },
  "output_tarball": "qt-6.7.1-static-linux-x86_64.tar.xz",
  "smoke_test": true
}
```

All values must match the configuration used in the build script. The `skipped_modules` array must be sorted alphabetically and contain exactly the four modules listed above.
