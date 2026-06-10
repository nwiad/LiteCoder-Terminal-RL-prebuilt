"""
Tests for multi-language development environment setup task.

Validates:
- Script existence and executability (setup.sh, build.sh)
- Build artifacts (C++ binary, Java JAR, Python venv)
- Correct program output from each language
- Documentation file content and structure
- Tool installations (gcc, java, python3, cmake, mvn)
- Python venv dependencies (pytest, requests)
"""

import os
import stat
import subprocess
import glob as globmod

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run(cmd, timeout=30):
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ===========================================================================
# 1. Script existence and executability
# ===========================================================================

class TestScriptFiles:

    def test_setup_sh_exists(self):
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), "setup.sh must exist at /app/setup.sh"

    def test_build_sh_exists(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh must exist at /app/build.sh"

    def test_setup_sh_executable(self):
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), "setup.sh not found"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "setup.sh must be executable (user execute bit)"

    def test_build_sh_executable(self):
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh not found"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "build.sh must be executable (user execute bit)"

    def test_setup_sh_is_bash_script(self):
        """setup.sh should be a non-empty shell script."""
        path = os.path.join(APP_DIR, "setup.sh")
        assert os.path.isfile(path), "setup.sh not found"
        size = os.path.getsize(path)
        assert size > 50, f"setup.sh is suspiciously small ({size} bytes)"

    def test_build_sh_is_bash_script(self):
        """build.sh should be a non-empty shell script."""
        path = os.path.join(APP_DIR, "build.sh")
        assert os.path.isfile(path), "build.sh not found"
        size = os.path.getsize(path)
        assert size > 50, f"build.sh is suspiciously small ({size} bytes)"


# ===========================================================================
# 2. C++ build artifacts and output
# ===========================================================================

class TestCppProject:

    def test_cpp_executable_exists(self):
        path = os.path.join(APP_DIR, "cpp-project", "build", "hello_cpp")
        assert os.path.isfile(path), (
            "C++ executable must exist at /app/cpp-project/build/hello_cpp"
        )

    def test_cpp_executable_is_runnable(self):
        path = os.path.join(APP_DIR, "cpp-project", "build", "hello_cpp")
        assert os.path.isfile(path), "C++ executable not found"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, "hello_cpp must be executable"

    def test_cpp_output(self):
        path = os.path.join(APP_DIR, "cpp-project", "build", "hello_cpp")
        assert os.path.isfile(path), "C++ executable not found"
        rc, stdout, _ = _run(path)
        assert rc == 0, f"hello_cpp exited with code {rc}"
        assert stdout == "Hello from C++!", (
            f"Expected 'Hello from C++!' but got '{stdout}'"
        )

    def test_cpp_build_directory_exists(self):
        path = os.path.join(APP_DIR, "cpp-project", "build")
        assert os.path.isdir(path), (
            "Out-of-source build directory /app/cpp-project/build/ must exist"
        )

    def test_cmake_lists_exists(self):
        path = os.path.join(APP_DIR, "cpp-project", "CMakeLists.txt")
        assert os.path.isfile(path), "CMakeLists.txt must exist"


# ===========================================================================
# 3. Java build artifacts and output
# ===========================================================================

class TestJavaProject:

    def _find_jar(self):
        """Find the hello-java JAR file under target/."""
        pattern = os.path.join(APP_DIR, "java-project", "target", "hello-java*.jar")
        jars = globmod.glob(pattern)
        # Filter out sources/javadoc jars
        jars = [j for j in jars if "sources" not in j and "javadoc" not in j]
        return jars

    def test_java_jar_exists(self):
        jars = self._find_jar()
        assert len(jars) >= 1, (
            "A JAR file matching hello-java*.jar must exist under "
            "/app/java-project/target/"
        )

    def test_java_jar_output(self):
        jars = self._find_jar()
        assert len(jars) >= 1, "JAR not found"
        jar_path = jars[0]
        rc, stdout, stderr = _run(f"java -jar {jar_path}")
        assert rc == 0, f"java -jar exited with code {rc}: {stderr}"
        assert stdout == "Hello from Java!", (
            f"Expected 'Hello from Java!' but got '{stdout}'"
        )

    def test_pom_xml_exists(self):
        path = os.path.join(APP_DIR, "java-project", "pom.xml")
        assert os.path.isfile(path), "pom.xml must exist"

    def test_pom_xml_has_correct_artifact_id(self):
        path = os.path.join(APP_DIR, "java-project", "pom.xml")
        assert os.path.isfile(path), "pom.xml not found"
        with open(path, "r") as f:
            content = f.read()
        assert "hello-java" in content, (
            "pom.xml must contain artifactId 'hello-java'"
        )

    def test_java_target_directory_exists(self):
        path = os.path.join(APP_DIR, "java-project", "target")
        assert os.path.isdir(path), (
            "Maven target directory /app/java-project/target/ must exist"
        )


# ===========================================================================
# 4. Python project and venv
# ===========================================================================

class TestPythonProject:

    def test_python_venv_exists(self):
        venv_path = os.path.join(APP_DIR, "python-project", "venv")
        assert os.path.isdir(venv_path), (
            "Python venv must exist at /app/python-project/venv/"
        )

    def test_python_venv_has_python(self):
        python_path = os.path.join(
            APP_DIR, "python-project", "venv", "bin", "python"
        )
        assert os.path.exists(python_path), (
            "venv must contain bin/python"
        )

    def test_python_script_output(self):
        python_path = os.path.join(
            APP_DIR, "python-project", "venv", "bin", "python"
        )
        script_path = os.path.join(APP_DIR, "python-project", "src", "main.py")
        assert os.path.exists(python_path), "venv python not found"
        assert os.path.isfile(script_path), "main.py not found"
        rc, stdout, stderr = _run(f"{python_path} {script_path}")
        assert rc == 0, f"Python script exited with code {rc}: {stderr}"
        assert stdout == "Hello from Python!", (
            f"Expected 'Hello from Python!' but got '{stdout}'"
        )

    def test_venv_has_pytest(self):
        """pytest must be installed in the venv."""
        pip_path = os.path.join(
            APP_DIR, "python-project", "venv", "bin", "pip"
        )
        if not os.path.exists(pip_path):
            # Try pip3
            pip_path = os.path.join(
                APP_DIR, "python-project", "venv", "bin", "pip3"
            )
        assert os.path.exists(pip_path), "pip not found in venv"
        rc, stdout, _ = _run(f"{pip_path} show pytest")
        assert rc == 0, "pytest is not installed in the Python venv"

    def test_venv_has_requests(self):
        """requests must be installed in the venv."""
        pip_path = os.path.join(
            APP_DIR, "python-project", "venv", "bin", "pip"
        )
        if not os.path.exists(pip_path):
            pip_path = os.path.join(
                APP_DIR, "python-project", "venv", "bin", "pip3"
            )
        assert os.path.exists(pip_path), "pip not found in venv"
        rc, stdout, _ = _run(f"{pip_path} show requests")
        assert rc == 0, "requests is not installed in the Python venv"

    def test_requirements_txt_exists(self):
        path = os.path.join(APP_DIR, "python-project", "requirements.txt")
        assert os.path.isfile(path), "requirements.txt must exist"

    def test_requirements_txt_content(self):
        path = os.path.join(APP_DIR, "python-project", "requirements.txt")
        assert os.path.isfile(path), "requirements.txt not found"
        with open(path, "r") as f:
            content = f.read().lower()
        assert "pytest" in content, "requirements.txt must list pytest"
        assert "requests" in content, "requirements.txt must list requests"


# ===========================================================================
# 5. Documentation
# ===========================================================================

class TestDocumentation:

    DOC_PATH = os.path.join(APP_DIR, "docs", "setup-guide.md")

    def test_setup_guide_exists(self):
        assert os.path.isfile(self.DOC_PATH), (
            "docs/setup-guide.md must exist at /app/docs/setup-guide.md"
        )

    def test_setup_guide_not_empty(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        size = os.path.getsize(self.DOC_PATH)
        assert size > 100, (
            f"setup-guide.md is suspiciously small ({size} bytes)"
        )

    def test_setup_guide_has_title(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            content = f.read()
        # Title must be "# Setup Guide" (allow leading/trailing whitespace)
        lines = [line.strip() for line in content.splitlines()]
        assert any(
            line == "# Setup Guide" for line in lines
        ), "setup-guide.md must contain a title line '# Setup Guide'"

    def test_setup_guide_minimum_length(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 30, (
            f"setup-guide.md must be at least 30 lines, got {len(lines)}"
        )

    def test_setup_guide_has_prerequisites_section(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        assert "prerequisite" in content, (
            "setup-guide.md must contain a prerequisites section"
        )

    def test_setup_guide_has_installation_section(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        assert "install" in content, (
            "setup-guide.md must contain an installation steps section"
        )

    def test_setup_guide_has_build_section(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        assert "build" in content, (
            "setup-guide.md must contain a build instructions section"
        )

    def test_setup_guide_has_project_structure_section(self):
        assert os.path.isfile(self.DOC_PATH), "setup-guide.md not found"
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        # Accept "project structure" or "structure overview"
        assert "structure" in content, (
            "setup-guide.md must contain a project structure overview section"
        )


# ===========================================================================
# 6. Tool installations are available
# ===========================================================================

class TestToolInstallations:

    def test_gcc_available(self):
        rc, stdout, _ = _run("gcc --version")
        assert rc == 0, "gcc must be installed and available on PATH"

    def test_gpp_available(self):
        rc, stdout, _ = _run("g++ --version")
        assert rc == 0, "g++ must be installed and available on PATH"

    def test_java_available(self):
        rc, stdout, _ = _run("java -version")
        assert rc == 0, "java must be installed and available on PATH"

    def test_javac_available(self):
        rc, stdout, _ = _run("javac -version")
        assert rc == 0, "javac must be installed and available on PATH"

    def test_python3_available(self):
        rc, stdout, _ = _run("python3 --version")
        assert rc == 0, "python3 must be installed and available on PATH"

    def test_cmake_available(self):
        rc, stdout, _ = _run("cmake --version")
        assert rc == 0, "cmake must be installed and available on PATH"

    def test_mvn_available(self):
        rc, stdout, _ = _run("mvn --version")
        assert rc == 0, "mvn (Maven) must be installed and available on PATH"


# ===========================================================================
# 7. Source files integrity
# ===========================================================================

class TestSourceFiles:

    def test_cpp_main_exists(self):
        path = os.path.join(APP_DIR, "cpp-project", "src", "main.cpp")
        assert os.path.isfile(path), "cpp-project/src/main.cpp must exist"

    def test_java_main_exists(self):
        path = os.path.join(
            APP_DIR, "java-project", "src", "main", "java",
            "com", "example", "Main.java"
        )
        assert os.path.isfile(path), (
            "java-project/src/main/java/com/example/Main.java must exist"
        )

    def test_python_main_exists(self):
        path = os.path.join(APP_DIR, "python-project", "src", "main.py")
        assert os.path.isfile(path), "python-project/src/main.py must exist"
