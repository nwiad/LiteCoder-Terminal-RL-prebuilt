## Build and Install Git from Source

Clone the official Git source code repository, compile it from source, and install the resulting binary to `/usr/local/bin`.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based)
- **Source:** Clone from `https://github.com/git/git.git`
- **Clone location:** `/app/git-source`
- **Installation prefix:** `/usr/local` (binaries end up in `/usr/local/bin`)
- **Report file:** Write a JSON build report to `/app/build_report.json`

### Steps

1. Install all required build dependencies (e.g., compilers, libraries, development headers needed to compile Git from source including documentation tools).
2. Clone the official Git source repository into `/app/git-source`.
3. Inside the cloned repository, check out the latest stable release tag (a tag matching the pattern `v2.*` that is NOT a release candidate — i.e., no `-rc` suffix).
4. Configure and compile Git from source using `make` with the prefix set to `/usr/local`.
5. Install the compiled Git binary so that `/usr/local/bin/git` exists and is executable.
6. Generate `/app/build_report.json` with the following structure:

```json
{
  "source_dir": "/app/git-source",
  "git_tag": "<the exact tag checked out, e.g. v2.47.1>",
  "installed_binary": "/usr/local/bin/git",
  "installed_version": "<output of /usr/local/bin/git --version, e.g. git version 2.47.1>"
}
```

### Requirements for the Build Report

- `source_dir` must be the string `"/app/git-source"`.
- `git_tag` must start with `v2.` and must NOT contain `-rc`.
- `installed_binary` must be `"/usr/local/bin/git"`.
- `installed_version` must start with `"git version "` and contain a version number that matches the tag.

### Verification Criteria

- `/app/git-source` exists and is a Git repository containing the official Git source.
- `/app/git-source` is checked out at a stable release tag (no release candidates).
- `/usr/local/bin/git` exists, is executable, and reports a version newer than `2.25.1`.
- The version reported by `/usr/local/bin/git --version` corresponds to the checked-out tag.
- `/app/build_report.json` exists and is valid JSON conforming to the schema above.
