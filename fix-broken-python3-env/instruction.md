## Fix Broken System-Wide Python 3 Environment

A junior administrator accidentally removed critical Python 3 system packages, leaving the system in an inconsistent state. Python 3 is missing or non-functional, but some configuration files remain. Restore a fully functional system-wide Python 3 environment without damaging the system further.

### Requirements

1. **Restore Python 3 runtime**: The `python3` binary must be available on `PATH` and executable. Running `python3 --version` must return a valid Python 3.x version string (e.g., `Python 3.x.x`).

2. **Restore core Python packages**: The following packages must be installed and in a healthy state (no broken/missing dependencies):
   - `python3-minimal`
   - `python3`
   - `python3-apt`

3. **Fix apt package manager**: `apt` and `apt-get` must be fully functional again. The following commands must complete without errors:
   - `apt-get check` (verify no broken dependencies)
   - `dpkg --audit` (verify no partially installed packages)

4. **Verify Python 3 standard library**: Python 3's standard library modules must be accessible. The following imports must succeed when run via `python3 -c`:
   - `import sys`
   - `import os`
   - `import json`
   - `import subprocess`

5. **Verify system tool integration**: System tools that depend on Python 3 must work. Specifically:
   - `python3 -c "import apt"` must succeed (python3-apt integration)

6. **Write recovery report**: Write a plain-text file to `/app/recovery_report.txt` documenting:
   - Line 1: The Python 3 version restored (exact output of `python3 --version`)
   - Line 2: Number of packages that were reinstalled or fixed (integer)
   - Line 3 onward: One package name per line that was reinstalled or fixed (e.g., `python3-minimal`)

### Constraints

- Operating system: Debian/Ubuntu-based Linux
- Do not install Python from source; use the system package manager (`apt`/`dpkg`)
- Do not upgrade the system or install unrelated packages
- The file `/app/recovery_report.txt` must exist when the task is complete
