## Build a Standalone Python 3.12 Environment with Scientific Libraries

Build Python 3.12 from source into an isolated prefix directory, bootstrap pip, build OpenBLAS from source, then build and install NumPy, SciPy, and matplotlib from source. Package the entire tree into a shippable tarball.

### Technical Requirements

- All compilation and installation must target the custom prefix `/opt/py312`. Nothing should be installed into system paths (`/usr`, `/usr/local`, etc.).
- Python version: 3.12.0 (built from the official CPython source tarball).
- OpenBLAS must be built from source and installed under `/opt/py312`.
- NumPy, SciPy, and matplotlib must be built from source (not installed from pre-built wheels) and linked against the locally built OpenBLAS.
- The final environment must be fully self-contained: all runtime dependencies live inside `/opt/py312`.

### Step-by-Step Requirements

1. Install system-level build dependencies needed to compile Python and the scientific stack (compilers, development headers, math libraries, image libraries, etc.).

2. Download the Python 3.12.0 source tarball from the official release page and verify its integrity using GPG.

3. Extract, configure (with optimizations enabled and `--prefix=/opt/py312`), compile, and install Python.

4. Bootstrap pip using the newly installed Python interpreter. Confirm the interpreter runs independently of any system Python.

5. Build OpenBLAS from source and install it under `/opt/py312`.

6. Build and install NumPy from source, linked against the local OpenBLAS.

7. Build and install SciPy from source, linked against the local OpenBLAS.

8. Build and install matplotlib from source (including its native dependencies such as libpng and freetype if not already available).

9. Run a smoke test using the custom Python interpreter that:
   - Imports `numpy`, `scipy`, and `matplotlib`.
   - Generates a sine-wave plot and saves it to `/opt/py312/smoke_test_output.png` (no GUI display).
   - Prints the following three lines to stdout (version strings will vary):
     ```
     numpy: <version>
     scipy: <version>
     matplotlib: <version>
     ```

10. Create a tarball of the entire `/opt/py312` directory tree at `/app/py312-scientific.tar.gz`.

### Verification Criteria

- `/opt/py312/bin/python3.12` exists and is executable.
- `/opt/py312/bin/python3.12 --version` outputs a string starting with `Python 3.12`.
- `/opt/py312/bin/pip3` exists and is executable.
- `/opt/py312/bin/python3.12 -c "import numpy; print(numpy.__version__)"` succeeds and prints a version string.
- `/opt/py312/bin/python3.12 -c "import scipy; print(scipy.__version__)"` succeeds and prints a version string.
- `/opt/py312/bin/python3.12 -c "import matplotlib; print(matplotlib.__version__)"` succeeds and prints a version string.
- `/opt/py312/smoke_test_output.png` exists and is a valid PNG file (size > 0 bytes).
- `/app/py312-scientific.tar.gz` exists, is a valid gzip-compressed tar archive, and contains the `opt/py312/bin/python3.12` entry.
