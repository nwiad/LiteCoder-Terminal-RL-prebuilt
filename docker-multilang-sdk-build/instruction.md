## Containerized Multi-Language Build Environment

Set up a Docker-based build environment that compiles and packages C/C++, Java, and Python projects through automated Make targets into a distributable multi-language SDK.

### Scenario

You are the DevOps lead at a polyglot shop that ships a single SDK containing native extensions, Java libraries, and Python wheels. Your job is to containerize the entire build pipeline so any developer can produce a release tarball on any machine. Build the project scaffolding, Dockerfile, and Makefile from scratch.

### Project Structure

Create the following directory and file structure under `/app`:

```
/app/
├── Makefile
├── Dockerfile
├── c/
│   ├── src/
│   │   └── mathlib.c
│   └── include/
│       └── mathlib.h
├── java/
│   └── src/
│       └── com/
│           └── sdk/
│               └── StringUtils.java
├── python/
│   └── sdk/
│       ├── __init__.py
│       └── analytics.py
└── build/          (created during build, holds compiled artifacts)
```

### Technical Requirements

**Language/Tools:** GNU Make, Docker, C (gcc), Java (javac), Python 3

#### 1. C Library (`c/`)

- `c/include/mathlib.h` must declare at least two functions: `int add(int a, int b);` and `int multiply(int a, int b);`
- `c/src/mathlib.c` must implement these functions.

#### 2. Java Library (`java/`)

- `java/src/com/sdk/StringUtils.java` must define a public class `StringUtils` in package `com.sdk`.
- The class must contain at least one public static method: `public static String reverse(String input)`.

#### 3. Python Package (`python/`)

- `python/sdk/__init__.py` must exist (can be empty or contain version info).
- `python/sdk/analytics.py` must define at least one function: `def mean(numbers)` that computes the arithmetic mean of a list of numbers.

#### 4. Dockerfile

Create `/app/Dockerfile` as a multi-stage Docker build file with the following requirements:

- Use a base image that supports all three language toolchains (e.g., `ubuntu:22.04` or similar).
- Install build dependencies: `gcc`, `make`, `default-jdk`, `python3`, `python3-pip`.
- The Dockerfile must contain at least two stages (use `FROM ... AS ...` syntax). One stage for building and one for packaging.
- The build stage must copy the source trees and invoke `make all` to compile all artifacts.
- The final stage must produce `/output/sdk.tar.gz` containing all build artifacts.
- The Dockerfile must set `SOURCE_DATE_EPOCH=1700000000` as an environment variable to support reproducible builds.

#### 5. Makefile

Create `/app/Makefile` with the following targets:

- **`help`** (default target): Prints a list of all available targets with short descriptions. The output must contain the strings `build-c`, `build-java`, `build-python`, `all`, `sdk`, `repro`, `clean`, and `help`.
- **`build-c`**: Compiles the C source into a shared library `build/libmathlib.so` using `gcc -shared -fPIC`.
- **`build-java`**: Compiles the Java source into `build/java/com/sdk/StringUtils.class` using `javac`.
- **`build-python`**: Copies the Python package into `build/python/sdk/` and generates `build/python/sdk.whl` (can be a zip archive of the `sdk/` directory renamed to `.whl`).
- **`all`**: Depends on `build-c`, `build-java`, and `build-python`. Builds all three language artifacts.
- **`sdk`**: Depends on `all`. Packages the contents of `build/` into `sdk.tar.gz` at the project root using `tar` with `--sort=name --mtime="2023-11-14 00:00:00"` flags for reproducibility.
- **`repro`**: Runs the `sdk` target twice (into two temp files), computes SHA-256 checksums of both, compares them, and prints `REPRODUCIBLE: <sha256>` if they match or `NOT REPRODUCIBLE` if they differ. The output must contain the word `REPRODUCIBLE`.
- **`clean`**: Removes the `build/` directory and `sdk.tar.gz`.
- **`docker-build`**: Builds the Docker image with tag `sdk-builder`.
- **`docker-sdk`**: Runs the Docker container from `sdk-builder` image and copies `sdk.tar.gz` out to the project root.

All build targets must create the `build/` directory if it does not exist.

### Output

After running `make all`, the following artifacts must exist:
- `/app/build/libmathlib.so`
- `/app/build/java/com/sdk/StringUtils.class`
- `/app/build/python/sdk.whl`

After running `make sdk`, the following artifact must exist:
- `/app/sdk.tar.gz`

### Constraints

- The Makefile must use `.PHONY` declarations for all non-file targets.
- The Makefile must not use recursive make (no `$(MAKE)` calls to sub-makefiles).
- All file paths in the Makefile must be relative to the project root `/app`.
