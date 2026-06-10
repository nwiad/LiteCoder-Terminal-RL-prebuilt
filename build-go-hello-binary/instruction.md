Clone a specific commit of a Go repository, build its binary, and verify functionality by capturing its output.

## Technical Requirements

- **Language/Tools**: Go 1.20.x or higher, Git
- **Repository**: https://github.com/golang/example
- **Target Commit**: 5d32d93f9a38
- **Working Directory**: /app
- **Output File**: /app/output.txt

## Task Steps

1. Install Go 1.20.x or higher if not already available
2. Clone the repository `golang/example` from GitHub
3. Checkout the specific commit `5d32d93f9a38`
4. Navigate to the `hello` subdirectory within the cloned repository
5. Build the Go binary using `go build`
6. Execute the compiled binary and capture its output
7. Write the binary's output to `/app/output.txt`

## Output Specification

The file `/app/output.txt` must contain the exact output produced by running the `hello` binary.

## Success Criteria

- The repository is cloned and checked out at commit `5d32d93f9a38`
- The `hello` binary is successfully built from the `hello` directory
- The binary executes without errors
- The output is captured in `/app/output.txt`
