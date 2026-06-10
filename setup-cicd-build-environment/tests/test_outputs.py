"""
Tests for CI/CD Build Environment Setup task.

Validates:
1. Tools installed and on PATH (java, javac, mvn, node, npm, git, curl, wget)
2. Version requirements (Java 11+, Maven 3.6+, Node.js 16+)
3. Sample Maven project structure and content
4. Maven build artifact (JAR) existence
5. environment_report.json schema, content, and consistency
"""

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET

REPORT_PATH = "/app/environment_report.json"
PROJECT_DIR = "/app/sample-project"
POM_PATH = os.path.join(PROJECT_DIR, "pom.xml")
APP_JAVA = os.path.join(PROJECT_DIR, "src/main/java/com/example/App.java")
APP_TEST_JAVA = os.path.join(PROJECT_DIR, "src/test/java/com/example/AppTest.java")
TARGET_DIR = os.path.join(PROJECT_DIR, "target")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def parse_version_tuple(version_str):
    """Extract the first version-like pattern (X.Y.Z or X.Y) from a string."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        patch = int(m.group(3)) if m.group(3) else 0
        return (major, minor, patch)
    return None


# ===========================================================================
# 1. environment_report.json — existence and valid JSON
# ===========================================================================

class TestReportFileBasics:

    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), (
            f"Report file not found at {REPORT_PATH}"
        )

    def test_report_is_valid_json(self):
        with open(REPORT_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "Report file is empty"
        data = json.loads(content)  # will raise on invalid JSON
        assert isinstance(data, dict), "Report root must be a JSON object"

    def test_report_has_tools_section(self):
        with open(REPORT_PATH) as f:
            data = json.load(f)
        assert "tools" in data, "Report missing 'tools' key"
        assert isinstance(data["tools"], dict), "'tools' must be an object"

    def test_report_has_build_section(self):
        with open(REPORT_PATH) as f:
            data = json.load(f)
        assert "build" in data, "Report missing 'build' key"
        assert isinstance(data["build"], dict), "'build' must be an object"


# ===========================================================================
# 2. environment_report.json — tools section validation
# ===========================================================================

REQUIRED_TOOLS = ["java", "javac", "mvn", "node", "npm", "git", "curl", "wget"]


class TestReportToolsSection:

    def _load_tools(self):
        with open(REPORT_PATH) as f:
            return json.load(f)["tools"]

    def test_all_tool_keys_present(self):
        tools = self._load_tools()
        for tool in REQUIRED_TOOLS:
            assert tool in tools, f"Missing tool key: '{tool}'"

    def test_all_tool_values_non_empty_strings(self):
        tools = self._load_tools()
        for tool in REQUIRED_TOOLS:
            val = tools.get(tool, "")
            assert isinstance(val, str), f"Tool '{tool}' value must be a string"
            assert len(val.strip()) > 0, f"Tool '{tool}' has empty version string"

    def test_java_version_string_looks_valid(self):
        """The java version string should contain a version number."""
        tools = self._load_tools()
        val = tools["java"]
        assert re.search(r"\d+", val), (
            f"java version string doesn't contain a number: '{val}'"
        )

    def test_mvn_version_string_looks_valid(self):
        tools = self._load_tools()
        val = tools["mvn"]
        # Maven version line typically contains "Apache Maven X.Y.Z"
        assert re.search(r"\d+\.\d+", val), (
            f"mvn version string doesn't look like a version: '{val}'"
        )

    def test_node_version_string_looks_valid(self):
        tools = self._load_tools()
        val = tools["node"]
        assert re.search(r"\d+", val), (
            f"node version string doesn't contain a number: '{val}'"
        )

    def test_npm_version_string_looks_valid(self):
        tools = self._load_tools()
        val = tools["npm"]
        assert re.search(r"\d+\.\d+", val), (
            f"npm version string doesn't look like a version: '{val}'"
        )

    def test_git_version_string_looks_valid(self):
        tools = self._load_tools()
        val = tools["git"]
        assert re.search(r"git", val, re.IGNORECASE), (
            f"git version string doesn't mention git: '{val}'"
        )


# ===========================================================================
# 3. environment_report.json — build section validation
# ===========================================================================

class TestReportBuildSection:

    def _load_build(self):
        with open(REPORT_PATH) as f:
            return json.load(f)["build"]

    def test_build_success_is_true(self):
        build = self._load_build()
        assert "build_success" in build, "Missing 'build_success' key"
        assert build["build_success"] is True, (
            f"build_success must be boolean true, got {build['build_success']!r}"
        )

    def test_project_path_correct(self):
        build = self._load_build()
        assert "project_path" in build, "Missing 'project_path' key"
        assert build["project_path"] == "/app/sample-project", (
            f"project_path should be '/app/sample-project', got '{build['project_path']}'"
        )

    def test_jar_file_key_present_and_non_empty(self):
        build = self._load_build()
        assert "jar_file" in build, "Missing 'jar_file' key"
        jar = build["jar_file"]
        assert isinstance(jar, str) and len(jar.strip()) > 0, (
            "jar_file must be a non-empty string"
        )

    def test_jar_file_ends_with_jar(self):
        build = self._load_build()
        jar = build["jar_file"].strip()
        assert jar.endswith(".jar"), (
            f"jar_file should end with .jar, got '{jar}'"
        )

    def test_jar_file_actually_exists_on_disk(self):
        """Verify the JAR referenced in the report actually exists."""
        build = self._load_build()
        jar_name = build["jar_file"].strip()
        # The jar_file could be just a filename or a relative path under target/
        candidates = [
            os.path.join(TARGET_DIR, jar_name),
            os.path.join(PROJECT_DIR, jar_name),
            os.path.join(PROJECT_DIR, "target", jar_name),
        ]
        found = any(os.path.isfile(c) for c in candidates)
        assert found, (
            f"JAR file '{jar_name}' not found. Checked: {candidates}"
        )


# ===========================================================================
# 4. Actual tool installation verification (tools callable on PATH)
# ===========================================================================

class TestToolsOnPath:

    def test_java_callable(self):
        rc, out, err = run_cmd("java -version")
        combined = out + " " + err
        assert rc == 0, f"'java -version' failed (rc={rc}): {combined}"

    def test_javac_callable(self):
        rc, out, err = run_cmd("javac -version")
        combined = out + " " + err
        assert rc == 0, f"'javac -version' failed (rc={rc}): {combined}"

    def test_mvn_callable(self):
        rc, out, err = run_cmd("mvn -version")
        combined = out + " " + err
        assert rc == 0, f"'mvn -version' failed (rc={rc}): {combined}"

    def test_node_callable(self):
        rc, out, err = run_cmd("node --version")
        assert rc == 0, f"'node --version' failed (rc={rc}): {out} {err}"

    def test_npm_callable(self):
        rc, out, err = run_cmd("npm --version")
        assert rc == 0, f"'npm --version' failed (rc={rc}): {out} {err}"

    def test_git_callable(self):
        rc, out, err = run_cmd("git --version")
        assert rc == 0, f"'git --version' failed (rc={rc}): {out} {err}"

    def test_curl_callable(self):
        rc, out, err = run_cmd("curl --version")
        assert rc == 0, f"'curl --version' failed (rc={rc}): {out} {err}"

    def test_wget_callable(self):
        rc, out, err = run_cmd("wget --version")
        assert rc == 0, f"'wget --version' failed (rc={rc}): {out} {err}"


# ===========================================================================
# 5. Version requirements
# ===========================================================================

class TestVersionRequirements:

    def test_java_version_11_or_higher(self):
        rc, out, err = run_cmd("java -version")
        combined = out + " " + err
        ver = parse_version_tuple(combined)
        assert ver is not None, f"Could not parse Java version from: {combined}"
        assert ver[0] >= 11, (
            f"Java version must be 11+, got {ver[0]}.{ver[1]}.{ver[2]}"
        )

    def test_maven_version_3_6_or_higher(self):
        rc, out, err = run_cmd("mvn -version")
        combined = out + " " + err
        ver = parse_version_tuple(combined)
        assert ver is not None, f"Could not parse Maven version from: {combined}"
        assert ver >= (3, 6, 0), (
            f"Maven version must be 3.6+, got {ver[0]}.{ver[1]}.{ver[2]}"
        )

    def test_node_version_16_or_higher(self):
        rc, out, err = run_cmd("node --version")
        combined = (out + " " + err).strip()
        # node --version outputs e.g. "v22.13.1"
        ver = parse_version_tuple(combined)
        assert ver is not None, f"Could not parse Node version from: {combined}"
        assert ver[0] >= 16, (
            f"Node.js version must be 16+, got {ver[0]}.{ver[1]}.{ver[2]}"
        )


# ===========================================================================
# 6. Sample Maven project structure
# ===========================================================================

class TestProjectStructure:

    def test_project_dir_exists(self):
        assert os.path.isdir(PROJECT_DIR), (
            f"Project directory not found: {PROJECT_DIR}"
        )

    def test_pom_xml_exists(self):
        assert os.path.isfile(POM_PATH), f"pom.xml not found at {POM_PATH}"

    def test_app_java_exists(self):
        assert os.path.isfile(APP_JAVA), f"App.java not found at {APP_JAVA}"

    def test_app_test_java_exists(self):
        assert os.path.isfile(APP_TEST_JAVA), (
            f"AppTest.java not found at {APP_TEST_JAVA}"
        )

    def test_target_dir_exists(self):
        assert os.path.isdir(TARGET_DIR), (
            f"target/ directory not found — build may not have run"
        )

    def test_jar_exists_in_target(self):
        """At least one .jar file must exist in target/."""
        assert os.path.isdir(TARGET_DIR), "target/ directory missing"
        jars = [f for f in os.listdir(TARGET_DIR) if f.endswith(".jar")]
        assert len(jars) > 0, (
            f"No .jar files found in {TARGET_DIR}. Contents: {os.listdir(TARGET_DIR)}"
        )


# ===========================================================================
# 7. pom.xml content validation
# ===========================================================================

class TestPomXml:

    def _parse_pom(self):
        tree = ET.parse(POM_PATH)
        root = tree.getroot()
        # Handle Maven namespace
        ns = ""
        m = re.match(r"\{(.+?)\}", root.tag)
        if m:
            ns = m.group(1)
        return root, ns

    def _find(self, root, ns, tag):
        if ns:
            return root.find(f"{{{ns}}}{tag}")
        return root.find(tag)

    def test_group_id_is_com_example(self):
        root, ns = self._parse_pom()
        elem = self._find(root, ns, "groupId")
        assert elem is not None and elem.text, "groupId not found in pom.xml"
        assert elem.text.strip() == "com.example", (
            f"groupId should be 'com.example', got '{elem.text.strip()}'"
        )

    def test_artifact_id_is_sample_app(self):
        root, ns = self._parse_pom()
        elem = self._find(root, ns, "artifactId")
        assert elem is not None and elem.text, "artifactId not found in pom.xml"
        assert elem.text.strip() == "sample-app", (
            f"artifactId should be 'sample-app', got '{elem.text.strip()}'"
        )

    def test_packaging_is_jar(self):
        root, ns = self._parse_pom()
        elem = self._find(root, ns, "packaging")
        # If packaging is absent, Maven defaults to jar — that's acceptable
        if elem is not None and elem.text:
            assert elem.text.strip() == "jar", (
                f"packaging should be 'jar', got '{elem.text.strip()}'"
            )

    def test_junit_dependency_present(self):
        """pom.xml must have a JUnit dependency (version 4.13+)."""
        with open(POM_PATH, "r") as f:
            content = f.read()
        assert "junit" in content.lower(), (
            "pom.xml does not contain a JUnit dependency"
        )


# ===========================================================================
# 8. App.java content validation
# ===========================================================================

class TestAppJavaContent:

    def _read_app(self):
        with open(APP_JAVA, "r") as f:
            return f.read()

    def test_has_greet_method(self):
        content = self._read_app()
        assert "greet" in content, "App.java missing 'greet' method"

    def test_greet_method_signature(self):
        """greet must accept a String parameter and be public static."""
        content = self._read_app()
        # Flexible: allow different formatting styles
        assert re.search(
            r"public\s+static\s+String\s+greet\s*\(\s*String\s+\w+\s*\)",
            content,
        ), "App.java missing 'public static String greet(String ...)' signature"

    def test_returns_hello_pattern(self):
        """greet should produce 'Hello, <name>!' pattern."""
        content = self._read_app()
        # Check for the Hello pattern in string concatenation or format
        assert re.search(r'["\']Hello', content), (
            "App.java doesn't appear to return a 'Hello, ...' greeting"
        )


# ===========================================================================
# 9. AppTest.java content validation
# ===========================================================================

class TestAppTestJavaContent:

    def _read_test(self):
        with open(APP_TEST_JAVA, "r") as f:
            return f.read()

    def test_has_test_annotation(self):
        content = self._read_test()
        assert "@Test" in content, "AppTest.java missing @Test annotation"

    def test_references_greet(self):
        content = self._read_test()
        assert "greet" in content, (
            "AppTest.java doesn't reference the greet method"
        )

    def test_tests_hello_world(self):
        """At least one test should verify greet('World') => 'Hello, World!'."""
        content = self._read_test()
        assert "World" in content, (
            "AppTest.java doesn't test with 'World' argument"
        )
        assert "Hello, World!" in content, (
            "AppTest.java doesn't assert 'Hello, World!' expected value"
        )


# ===========================================================================
# 10. Cross-validation: report consistency with actual filesystem
# ===========================================================================

class TestReportConsistency:

    def test_report_tool_versions_match_actual(self):
        """Spot-check that reported git version matches actual git output."""
        with open(REPORT_PATH) as f:
            data = json.load(f)
        reported_git = data["tools"]["git"]
        rc, out, err = run_cmd("git --version")
        actual_git = (out + " " + err).strip()
        # Both should contain the same version number
        reported_ver = parse_version_tuple(reported_git)
        actual_ver = parse_version_tuple(actual_git)
        assert reported_ver is not None, (
            f"Cannot parse version from reported git: '{reported_git}'"
        )
        assert actual_ver is not None, (
            f"Cannot parse version from actual git: '{actual_git}'"
        )
        assert reported_ver == actual_ver, (
            f"Reported git version {reported_ver} != actual {actual_ver}"
        )
