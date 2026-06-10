import os
import subprocess
import tempfile


def test_output_file_exists():
    """Test that the output file exists at the expected location."""
    assert os.path.exists("/app/output.txt"), "Output file /app/output.txt does not exist"


def test_output_file_not_empty():
    """Test that the output file is not empty."""
    assert os.path.getsize("/app/output.txt") > 0, "Output file /app/output.txt is empty"


def test_output_content_matches_expected():
    """
    Test that the output matches what the hello binary actually produces.

    This test verifies the agent didn't just write dummy text, but actually:
    1. Cloned the correct repository
    2. Checked out the specific commit 5d32d93f9a38
    3. Built and executed the hello binary
    """
    with open("/app/output.txt", "r") as f:
        actual_output = f.read().strip()

    # The hello program at commit 5d32d93f9a38 outputs "Hello, world."
    # We verify this by building it ourselves in a temp directory
    expected_output = "Hello, world."

    assert actual_output == expected_output, (
        f"Output content mismatch.\n"
        f"Expected: '{expected_output}'\n"
        f"Got: '{actual_output}'"
    )


def test_output_is_not_dummy_text():
    """
    Test that the output is not common dummy text that a lazy agent might write.

    This catches attempts to hardcode output without actually running the binary.
    """
    with open("/app/output.txt", "r") as f:
        content = f.read().strip()

    # List of dummy texts a lazy agent might use
    dummy_texts = [
        "Hello World",
        "Hello, World",
        "hello world",
        "test",
        "dummy",
        "placeholder",
        "",
    ]

    # The content should not be any of these dummy texts
    # (Note: "Hello, world." with period is the actual correct output)
    assert content not in dummy_texts, (
        f"Output appears to be dummy text: '{content}'"
    )


def test_verify_actual_binary_execution():
    """
    Verify the output by independently building and running the binary.

    This is the strongest test - we clone, checkout, build, and run ourselves
    to verify the agent's output matches reality.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone the repository
        subprocess.run(
            ["git", "clone", "https://github.com/golang/example.git", tmpdir],
            check=True,
            capture_output=True
        )

        # Checkout the specific commit
        subprocess.run(
            ["git", "checkout", "5d32d93f9a38"],
            cwd=tmpdir,
            check=True,
            capture_output=True
        )

        # Build the hello binary
        hello_dir = os.path.join(tmpdir, "hello")
        subprocess.run(
            ["go", "build"],
            cwd=hello_dir,
            check=True,
            capture_output=True
        )

        # Run the binary and capture output
        result = subprocess.run(
            ["./hello"],
            cwd=hello_dir,
            check=True,
            capture_output=True,
            text=True
        )

        expected_output = result.stdout.strip()

        # Compare with the agent's output
        with open("/app/output.txt", "r") as f:
            actual_output = f.read().strip()

        assert actual_output == expected_output, (
            f"Output does not match independently verified binary execution.\n"
            f"Expected: '{expected_output}'\n"
            f"Got: '{actual_output}'"
        )


def test_output_format_is_plain_text():
    """Test that the output is plain text without extra formatting."""
    with open("/app/output.txt", "r") as f:
        content = f.read()

    # Should not contain HTML, JSON, or other structured formats
    assert not content.strip().startswith("<"), "Output should not be HTML"
    assert not content.strip().startswith("{"), "Output should not be JSON"
    assert not content.strip().startswith("["), "Output should not be JSON array"


def test_repository_was_cloned():
    """
    Verify that the repository was actually cloned (not just output faked).

    This checks for evidence that the agent performed the actual task steps.
    """
    # Check if the example directory exists (evidence of cloning)
    example_dir = "/app/example"
    assert os.path.exists(example_dir), (
        "Repository does not appear to have been cloned to /app/example"
    )

    # Check if it's a git repository
    git_dir = os.path.join(example_dir, ".git")
    assert os.path.exists(git_dir), (
        "Cloned directory is not a git repository"
    )


def test_correct_commit_was_checked_out():
    """
    Verify that the specific commit 5d32d93f9a38 was checked out.

    This ensures the agent didn't just clone the repo but actually
    checked out the required commit.
    """
    example_dir = "/app/example"

    if os.path.exists(example_dir):
        # Get the current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=example_dir,
            capture_output=True,
            text=True,
            check=True
        )

        current_commit = result.stdout.strip()

        # The commit should start with 5d32d93f9a38
        assert current_commit.startswith("5d32d93f9a38"), (
            f"Wrong commit checked out. Expected commit starting with 5d32d93f9a38, "
            f"got {current_commit}"
        )


def test_binary_was_built():
    """
    Verify that the hello binary was actually built.

    This checks for the compiled binary in the expected location.
    """
    hello_binary = "/app/example/hello/hello"

    # The binary should exist
    assert os.path.exists(hello_binary), (
        "Hello binary was not built at /app/example/hello/hello"
    )

    # The binary should be executable
    assert os.access(hello_binary, os.X_OK), (
        "Hello binary exists but is not executable"
    )
