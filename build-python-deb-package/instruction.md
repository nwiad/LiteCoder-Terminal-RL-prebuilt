## Task: Debian Package Builder for Custom Python Library

Create a Debian package (.deb) for a Python library named `fastcalc` (version 1.0.0) that includes both Python modules and a C extension for mathematical operations.

## Technical Requirements

- **Language**: Python 3.x with C extensions
- **Build System**: Debian packaging tools (dpkg-buildpackage, debhelper)
- **Target Platform**: Ubuntu/Debian systems
- **Package Name**: python3-fastcalc
- **Working Directory**: /app

## Package Specifications

### Library Structure
The `fastcalc` library must include:
- A Python module `fastcalc/__init__.py` with at least one function (e.g., `add`, `multiply`)
- A C extension module that compiles during installation
- A `setup.py` file configured for building both Python and C components

### Debian Package Requirements
Create a complete Debian package structure at `/app/fastcalc-1.0.0/` with:

1. **debian/control**: Package metadata including package name, version, maintainer, dependencies, and description
2. **debian/changelog**: Package changelog in proper Debian format
3. **debian/copyright**: Copyright and license information
4. **debian/rules**: Build rules for compiling and installing the package
5. **debian/compat**: Debhelper compatibility level

### Build Output
- Successfully build the package using standard Debian tools
- Generate a `.deb` file in `/app/` directory
- The package filename should follow Debian naming conventions (e.g., `python3-fastcalc_1.0.0-1_*.deb`)

### Verification Requirements
The built package must:
- Be installable on a Debian/Ubuntu system without errors
- Properly register Python modules in the system Python path
- Include all necessary dependencies in the control file
- Support clean installation and removal

## Deliverables

1. Complete source directory structure at `/app/fastcalc-1.0.0/`
2. All required Debian packaging files in `/app/fastcalc-1.0.0/debian/`
3. Built `.deb` package file in `/app/`
4. The package must pass `lintian` checks (Debian package quality checker) without critical errors
