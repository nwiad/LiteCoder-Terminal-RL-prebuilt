Build a custom Debian package from upstream source with custom configuration files and patches, then set up a local package repository.

## Technical Requirements

- Platform: Debian-based Linux system
- Package: htop system monitor
- Tools: dpkg-dev, debhelper, devscripts, apt-utils
- Input: Upstream htop source (download from official repository)
- Output: `/app/output.json` containing build verification results

## Task Requirements

1. **Package Building:**
   - Download htop upstream source (version 3.2.1 or later)
   - Create debian/ directory structure with required packaging files
   - Apply a custom patch file that modifies the source code
   - Include custom configuration with company branding in the package
   - Build a .deb package file

2. **Repository Setup:**
   - Create a local APT repository structure in `/app/repo/`
   - Generate Packages index file
   - Make the repository installable via apt

3. **Verification Output:**
   - Create `/app/output.json` with the following structure:
   ```json
   {
     "package_built": true,
     "package_name": "htop",
     "package_version": "3.2.1-custom1",
     "package_file": "/app/htop_3.2.1-custom1_amd64.deb",
     "patch_applied": true,
     "repository_created": true,
     "repository_path": "/app/repo"
   }
   ```

## Success Criteria

- A valid .deb package file exists
- The package contains custom modifications (patch and configuration)
- A functional local APT repository is created at `/app/repo/`
- The repository contains a valid Packages index file
- `/app/output.json` accurately reflects the build status
