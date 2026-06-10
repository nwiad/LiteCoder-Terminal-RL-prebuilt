## Build Git from Source with Custom Configuration

Compile and install Git from source code with a custom configuration, installing it to `/opt/git-custom` with PCRE support and optimized build flags.

### Requirements

1. **Install build dependencies** needed for Git compilation (including PCRE library development headers).

2. **Download Git source code**: Obtain a stable release of Git source (version 2.40 or later). Extract it to `/app/git-source/`.

3. **Configure the build** with the following options:
   - Install prefix: `/opt/git-custom`
   - Enable PCRE2 (or PCRE) support for advanced `git grep` regex functionality

4. **Compile Git** using `make` with:
   - Optimization flag: `-O2`
   - Custom linker flags: `-Wl,-O1`

5. **Install Git** to `/opt/git-custom`. After installation, the following must exist:
   - Executable: `/opt/git-custom/bin/git`
   - The binary must be a working Git executable (not a symlink to system Git)

6. **Create a symbolic link**: Create `/usr/local/bin/git-custom` pointing to `/opt/git-custom/bin/git`.

7. **Verification report**: Write a JSON report to `/app/output.json` with the following structure:
   ```json
   {
     "git_version": "<output of /opt/git-custom/bin/git --version>",
     "install_prefix": "/opt/git-custom",
     "pcre_support": true,
     "binary_path": "/opt/git-custom/bin/git",
     "symlink_path": "/usr/local/bin/git-custom",
     "optimization_flags": "-O2",
     "linker_flags": "-Wl,-O1",
     "test_repo_status": "<output of git-custom init on a test repo>"
   }
   ```
   - `git_version`: The exact string output from running `/opt/git-custom/bin/git --version` (e.g., `"git version 2.47.0"`)
   - `pcre_support`: Boolean `true` if PCRE/PCRE2 is compiled in. Verify by checking that `/opt/git-custom/bin/git grep -P` does not return an error about missing PCRE support.
   - `test_repo_status`: Initialize a test repository at `/app/test-repo/` using the custom git binary and capture the init output string.

8. **Clean up**: Remove the downloaded source tarball and extracted source directory under `/app/git-source/` after successful installation. The `/app/git-source/` directory should not exist when the task is complete.

### Output

- `/app/output.json` — JSON verification report as specified above
- `/opt/git-custom/bin/git` — working custom-built Git binary
- `/usr/local/bin/git-custom` — symbolic link to the custom Git binary
- `/app/test-repo/` — initialized Git repository created with the custom binary
