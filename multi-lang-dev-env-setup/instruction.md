## Multi-Language Development Environment Setup

Set up a reproducible multi-language development environment for C/C++, Java, and Python with sample projects, a unified build script, and setup documentation.

### Technical Requirements

- **Languages/Tools:** GCC/G++ (C++11 support), OpenJDK 11+, Python 3.8+, CMake, Maven, pip
- **Working directory:** `/app`

### Directory Structure

Create the following structure under `/app`:

```
/app/
├── setup.sh
├── build.sh
├── docs/
│   └── setup-guide.md
├── cpp-project/
│   ├── CMakeLists.txt
│   └── src/
│       └── main.cpp
├── java-project/
│   ├── pom.xml
│   └── src/main/java/com/example/
│       └── Main.java
└── python-project/
    ├── requirements.txt
    ├── venv/           (created by setup.sh)
    └── src/
        └── main.py
```

### Script Specifications

#### `setup.sh`

A bash script at `/app/setup.sh` that:

1. Installs and verifies GCC/G++ with C++11 support.
2. Installs and verifies OpenJDK 11+ and Maven.
3. Installs and verifies Python 3.8+ with pip.
4. Installs CMake.
5. Creates a Python virtual environment at `/app/python-project/venv/` and installs packages listed in `/app/python-project/requirements.txt` into it.
6. Exits with code `0` on success.

The script must be executable (`chmod +x`).

#### `build.sh`

A bash script at `/app/build.sh` that:

1. Builds the C++ project using CMake (out-of-source build in `/app/cpp-project/build/`), producing an executable at `/app/cpp-project/build/hello_cpp`.
2. Builds the Java project using Maven (`mvn package`), producing a JAR file under `/app/java-project/target/` (the JAR filename must contain `hello-java`).
3. Runs the Python script using the virtual environment's Python interpreter.
4. Exits with code `0` if all three builds/runs succeed.

The script must be executable (`chmod +x`).

### Sample Projects

#### C++ Project (`/app/cpp-project/`)

- `src/main.cpp`: A C++ program that prints exactly `Hello from C++!` to stdout (followed by a newline).
- `CMakeLists.txt`: Configures the project with C++11 standard, producing a target named `hello_cpp`.

#### Java Project (`/app/java-project/`)

- `src/main/java/com/example/Main.java`: A Java program in package `com.example` that prints exactly `Hello from Java!` to stdout (followed by a newline).
- `pom.xml`: A Maven POM with `groupId` = `com.example`, `artifactId` = `hello-java`, `version` = `1.0`. It must configure the `maven-jar-plugin` so the JAR's manifest specifies `com.example.Main` as the main class.

#### Python Project (`/app/python-project/`)

- `src/main.py`: A Python script that prints exactly `Hello from Python!` to stdout (followed by a newline).
- `requirements.txt`: Must include at least `pytest` and `requests` as dependencies.

### Documentation

Create `/app/docs/setup-guide.md` containing:

- A title line with `# Setup Guide`
- Sections covering: prerequisites, installation steps, build instructions, and project structure overview.
- The file must be at least 30 lines long.

### Execution

After running `setup.sh` then `build.sh` in sequence:

- `/app/cpp-project/build/hello_cpp` when executed prints: `Hello from C++!`
- `java -jar /app/java-project/target/hello-java*.jar` prints: `Hello from Java!`
- `/app/python-project/venv/bin/python /app/python-project/src/main.py` prints: `Hello from Python!`
