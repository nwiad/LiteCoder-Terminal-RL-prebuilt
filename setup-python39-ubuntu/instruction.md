## Task: Build a Python 3.9+ Development Environment

Set up a complete Python 3.9+ development environment on Ubuntu 20.04 by compiling from source and configuring system-wide tools for multi-user access.

## Technical Requirements

- Target system: Ubuntu 20.04
- Python version: 3.9.x (latest stable release in 3.9 series)
- Installation prefix: `/opt/python3.9`
- Shared virtual environment: `/opt/venv/dev`
- All tools must be accessible system-wide without manual activation

## Implementation Requirements

1. **Python Installation**
   - Compile Python 3.9.x from source with optimizations enabled
   - Use altinstall to avoid overwriting system Python
   - Install to `/opt/python3.9`
   - Verify checksum of downloaded source tarball before extraction

2. **System-wide Access**
   - Create symlinks in `/usr/local/bin` for `python3.9` and `pip3.9`
   - Ensure commands are available to all users without PATH modifications

3. **Virtual Environment Setup**
   - Install `virtualenv` package globally
   - Create shared virtual environment at `/opt/venv/dev`
   - Install these packages in the shared venv: `pytest`, `black`, `flake8`, `ipython`

4. **Auto-activation Configuration**
   - Create activation script in `/etc/profile.d/` to expose the shared venv tools
   - Tools must be available in new login shells without manual activation

5. **Cleanup**
   - Remove build artifacts and temporary files
   - Keep installation footprint minimal

## Verification Requirements

Create a verification script at `/app/verify_setup.sh` that validates:

1. `python3.9 --version` returns Python 3.9.x
2. `pip3.9 --version` executes successfully
3. `virtualenv --version` executes successfully
4. All tools are accessible: `pytest --version`, `black --version`, `flake8 --version`, `ipython --version`
5. Commands work for non-root users

The script must exit with code 0 if all checks pass, non-zero otherwise.

## Output Requirements

Generate a summary report at `/app/setup_report.json` with:

```json
{
  "python_version": "3.9.x",
  "install_location": "/opt/python3.9",
  "shared_venv": "/opt/venv/dev",
  "installed_tools": ["pytest", "black", "flake8", "ipython", "virtualenv"],
  "disk_usage_mb": <total size in MB>,
  "verification_passed": true
}
```

## Edge Cases

- Handle existing Python installations without conflicts
- Ensure proper permissions for multi-user access
- Verify all symlinks point to correct executables
- Handle missing build dependencies gracefully
