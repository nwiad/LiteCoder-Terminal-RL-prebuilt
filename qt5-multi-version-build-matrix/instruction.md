## Multi-Version Qt5 Build Matrix

Create a complete build system that compiles a minimal Qt5 demo application against three different Qt5 versions in parallel and packages each into a self-contained redistributable tarball for Linux x86_64.

### Technical Requirements

- Language/Tools: Bash scripting, Dockerfiles or shell-based build orchestration
- Target Qt5 versions: `5.12.12`, `5.15.2`, `5.15.10`
- All work is done under `/app`

### Deliverables

All output files must be placed under `/app/`.

1. **Demo Qt5 Project** (`/app/demo-app/`):
   - A minimal Qt5 C++ application with a `QMainWindow` and an About dialog.
   - Must include a `.pro` file (qmake project) at `/app/demo-app/demo-app.pro`.
   - The application must support a `--version` flag that prints a line matching the pattern `demo-app <version>` to stdout and exits with code 0.

2. **Build Script** (`/app/build.sh`):
   - A single executable Bash script that orchestrates the full build pipeline.
   - Must accept an optional argument: a single Qt version string (e.g., `5.15.2`). When no argument is given, it builds for all three versions.
   - For each Qt version, the script must:
     - Use a Qt5 installation rooted at `/opt/qt5-<VERSION>` (e.g., `/opt/qt5-5.12.12`).
     - Configure the environment (`PATH`, `LD_LIBRARY_PATH`, `QT_PLUGIN_PATH`) so the correct Qt prefix is used.
     - Compile the demo application.
     - Verify the compiled binary has no unresolved dynamic Qt dependencies (using `ldd` or equivalent), or that all required Qt shared libraries are bundled alongside it.
     - Package the result into a tarball.
   - The script must write a build log to `/app/build-log.json` upon completion.

3. **Build Log** (`/app/build-log.json`):
   A JSON file with the following structure:
   ```json
   {
     "builds": [
       {
         "qt_version": "5.12.12",
         "status": "success" | "failure",
         "qt_prefix": "/opt/qt5-5.12.12",
         "binary_path": "<path to compiled binary>",
         "tarball_path": "<path to output tarball>",
         "tarball_size_bytes": <integer>,
         "dynamic_qt_deps": ["<list of any remaining dynamic Qt .so dependencies, empty if static>"]
       }
     ],
     "total_tarball_size_bytes": <integer sum of all tarball sizes>
   }
   ```
   - Each entry in `builds` must correspond to one of the three Qt versions.
   - `status` must be either `"success"` or `"failure"`.
   - `tarball_size_bytes` must be the actual file size in bytes.
   - `total_tarball_size_bytes` must equal the sum of all individual `tarball_size_bytes` values.

4. **Tarballs** (under `/app/dist/`):
   - One tarball per Qt version, named exactly: `research-app-qt5-<VERSION>-linux-x86_64.tar.gz`
     - `/app/dist/research-app-qt5-5.12.12-linux-x86_64.tar.gz`
     - `/app/dist/research-app-qt5-5.15.2-linux-x86_64.tar.gz`
     - `/app/dist/research-app-qt5-5.15.10-linux-x86_64.tar.gz`
   - Each tarball, when extracted, must contain at minimum:
     - `bin/` — the compiled binary
     - `lib/` — bundled Qt shared libraries (if dynamically linked) or empty (if statically linked)
     - `plugins/` — Qt plugins directory (at minimum `platforms/`)
     - `run.sh` — a launch script at the tarball root that sets `LD_LIBRARY_PATH` and `QT_PLUGIN_PATH` relative to its own location before executing the binary
   - The three tarballs combined must total less than 300 MB.

5. **Launch Script** (`run.sh` inside each tarball):
   - Must be executable.
   - Must set `LD_LIBRARY_PATH` to the bundled `lib/` directory.
   - Must set `QT_PLUGIN_PATH` to the bundled `plugins/` directory.
   - Must forward all command-line arguments to the binary.
   - Running `./run.sh --version` must print the version string and exit 0.

### Constraints

- The build script must be idempotent — running it twice produces the same output.
- Intermediate build artifacts (object files, moc output) must not be included in the tarballs.
- The demo application `.pro` file must not hardcode absolute paths to any Qt installation.
