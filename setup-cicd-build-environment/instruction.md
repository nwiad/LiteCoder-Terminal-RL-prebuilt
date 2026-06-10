## Task: Set Up a CI/CD Build Environment and Verify with a Java/Maven Project

Install and configure essential CI/CD build tools on this Ubuntu system, then demonstrate the environment works by building a sample Java/Maven project and producing a verification report.

### Technical Requirements

- **OS:** Ubuntu (current container)
- **Language/Tools to install:** Java JDK 11+, Apache Maven 3.6+, Node.js 16+, npm, Git, curl, wget, unzip
- **Output file:** `/app/environment_report.json`

### Steps

1. **Install system utilities:** Ensure `curl`, `wget`, `git`, `vim`, and `unzip` are installed and available on PATH.

2. **Install Java JDK 11+:** Install OpenJDK 11 (or newer). `java -version` and `javac -version` must work from the command line.

3. **Install Apache Maven 3.6+:** Install Maven so that `mvn -version` works and reports version 3.6.0 or higher.

4. **Install Node.js 16+ and npm:** Install Node.js (version 16 or above) and npm. Both `node --version` and `npm --version` must work.

5. **Create and build a sample Java/Maven project:** Create a minimal Maven project at `/app/sample-project/` with the following structure:
   - `/app/sample-project/pom.xml` — A valid Maven POM file with `groupId` = `com.example`, `artifactId` = `sample-app`, packaging = `jar`, and a dependency on JUnit 4.13+ for testing.
   - `/app/sample-project/src/main/java/com/example/App.java` — A simple Java class with a `public static String greet(String name)` method that returns `"Hello, <name>!"`.
   - `/app/sample-project/src/test/java/com/example/AppTest.java` — A JUnit test class with at least one test that verifies `App.greet("World")` returns `"Hello, World!"`.
   - Run `mvn clean package` inside `/app/sample-project/`. The build must succeed (exit code 0) and produce a JAR file under `/app/sample-project/target/`.

6. **Generate environment report:** Write a JSON file to `/app/environment_report.json` with the following structure:

```json
{
  "tools": {
    "java": "<output of java -version, first line>",
    "javac": "<output of javac -version>",
    "mvn": "<output of mvn -version, first line>",
    "node": "<output of node --version>",
    "npm": "<output of npm --version>",
    "git": "<output of git --version>",
    "curl": "<output of curl --version, first line>",
    "wget": "<output of wget --version, first line>"
  },
  "build": {
    "project_path": "/app/sample-project",
    "build_success": true,
    "jar_file": "<relative path to the generated JAR file under /app/sample-project/target/>"
  }
}
```

All values in `"tools"` must be non-empty strings. `"build_success"` must be `true`. `"jar_file"` must point to an existing `.jar` file (relative to `/app/sample-project/target/`, e.g., `"sample-app-1.0-SNAPSHOT.jar"`).

### Constraints

- All tools must be callable directly from the shell (i.e., on PATH).
- The Maven build (`mvn clean package`) must complete successfully with all tests passing.
- `/app/environment_report.json` must be valid JSON and parseable.
- Do not use Docker-in-Docker or start any background services (e.g., Jenkins). Focus on the build toolchain only.
