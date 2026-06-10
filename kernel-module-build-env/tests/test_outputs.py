"""
Tests for the Linux Kernel Module Build Environment task.
Validates all 5 required artifacts under /app without running Docker or compiling.
"""

import os
import re
import tarfile
import gzip
import subprocess

BASE = "/app"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def read_text(path):
    """Read a file and return its text content, or None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", errors="replace") as f:
        return f.read()


def assert_file_exists(path):
    assert os.path.isfile(path), f"Expected file not found: {path}"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All five required artifacts must exist."""

    def test_dockerfile_exists(self):
        assert_file_exists(os.path.join(BASE, "Dockerfile"))

    def test_tarball_exists(self):
        assert_file_exists(os.path.join(BASE, "vendor-tarball", "acme-kernel-5.10.tar.gz"))

    def test_hello_c_exists(self):
        assert_file_exists(os.path.join(BASE, "module-src", "hello.c"))

    def test_module_makefile_exists(self):
        assert_file_exists(os.path.join(BASE, "module-src", "Makefile"))

    def test_readme_exists(self):
        assert_file_exists(os.path.join(BASE, "README.md"))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DOCKERFILE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDockerfile:
    """Validate Dockerfile content against all instruction requirements."""

    def _content(self):
        return read_text(os.path.join(BASE, "Dockerfile"))

    # --- Base image ---
    def test_base_image_debian_or_ubuntu(self):
        c = self._content()
        assert c is not None, "Dockerfile missing"
        # Must have a FROM with ubuntu or debian, and a pinned tag (not :latest, not bare)
        from_lines = re.findall(r"(?i)^FROM\s+(\S+)", c, re.MULTILINE)
        assert len(from_lines) > 0, "No FROM directive found"
        base = from_lines[0].lower()
        assert ("ubuntu" in base or "debian" in base), \
            f"Base image must be ubuntu or debian, got: {base}"

    def test_base_image_pinned(self):
        c = self._content()
        assert c is not None
        from_lines = re.findall(r"(?i)^FROM\s+(\S+)", c, re.MULTILINE)
        base = from_lines[0]
        # Must have a colon with a tag that is NOT 'latest'
        assert ":" in base, f"Base image tag not pinned (no colon): {base}"
        tag = base.split(":")[-1]
        assert tag.lower() != "latest", "Base image must not use :latest"

    # --- Required packages ---
    def test_required_packages(self):
        c = self._content()
        assert c is not None
        required = ["build-essential", "bc", "kmod", "flex", "bison", "libssl-dev", "libelf-dev"]
        for pkg in required:
            assert pkg in c, f"Dockerfile must install package: {pkg}"

    # --- Tarball extraction to /opt/acme-510 ---
    def test_tarball_extraction(self):
        c = self._content()
        assert c is not None
        assert "/opt/acme-510" in c, "Dockerfile must extract tarball to /opt/acme-510"

    # --- Symlink creation ---
    def test_symlink_current(self):
        c = self._content()
        assert c is not None
        # Must create /opt/acme-510/current symlink
        assert re.search(r"/opt/acme-510/current", c), \
            "Dockerfile must create symlink /opt/acme-510/current"
        # Should use ln -s or ln -sf
        assert re.search(r"ln\s+-s", c), \
            "Dockerfile must use 'ln -s' to create the symlink"

    # --- Kernel preparation order ---
    def test_kernel_prep_order(self):
        c = self._content()
        assert c is not None
        # All three commands must appear
        assert "mrproper" in c, "Dockerfile must run 'make mrproper'"
        assert "defconfig" in c, "Dockerfile must run 'make defconfig'"
        assert "modules_prepare" in c, "Dockerfile must run 'make modules_prepare'"
        # Order: mrproper before defconfig before modules_prepare
        pos_mrproper = c.index("mrproper")
        pos_defconfig = c.index("defconfig")
        pos_modules_prepare = c.index("modules_prepare")
        assert pos_mrproper < pos_defconfig < pos_modules_prepare, \
            "Kernel prep must be in order: mrproper → defconfig → modules_prepare"

    # --- Module build with KDIR ---
    def test_module_build_kdir(self):
        c = self._content()
        assert c is not None
        assert "KDIR" in c, "Dockerfile must build module using KDIR"

    # --- Copy .ko to /artifacts ---
    def test_artifacts_copy(self):
        c = self._content()
        assert c is not None
        assert "/artifacts" in c, "Dockerfile must copy .ko to /artifacts"
        # Must reference .ko files
        assert ".ko" in c, "Dockerfile must reference .ko files"

    # --- insmod step ---
    def test_insmod_step(self):
        c = self._content()
        assert c is not None
        assert "insmod" in c, "Dockerfile must contain an insmod step"

    # --- Labels ---
    def test_label_maintainer(self):
        c = self._content()
        assert c is not None
        assert re.search(r"(?i)LABEL\s+.*maintainer", c), \
            "Dockerfile must have LABEL maintainer"

    def test_label_build_command(self):
        c = self._content()
        assert c is not None
        assert re.search(r"(?i)LABEL\s+.*build\.command", c), \
            "Dockerfile must have LABEL build.command"

    # --- Fail-fast ---
    def test_fail_fast(self):
        c = self._content()
        assert c is not None
        # set -e must appear in RUN commands
        assert "set -e" in c, "Dockerfile must use 'set -e' for fail-fast"

    # --- Non-interactive ---
    def test_non_interactive(self):
        c = self._content()
        assert c is not None
        # apt-get install must use -y
        install_lines = re.findall(r"apt-get\s+install\s+(.+?)(?:\\|\n|$)", c)
        for line in install_lines:
            assert "-y" in line, f"apt-get install must use -y flag: {line}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. VENDOR TARBALL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestVendorTarball:
    """Validate the vendor kernel tarball structure and content."""

    TARBALL = os.path.join(BASE, "vendor-tarball", "acme-kernel-5.10.tar.gz")

    def test_is_valid_gzip(self):
        """Must be a real gzip file, not just renamed."""
        assert_file_exists(self.TARBALL)
        with open(self.TARBALL, "rb") as f:
            magic = f.read(2)
        assert magic == b"\x1f\x8b", "Tarball is not a valid gzip file"

    def test_is_valid_tar(self):
        """Must be a valid tar archive."""
        assert_file_exists(self.TARBALL)
        assert tarfile.is_tarfile(self.TARBALL), "File is not a valid tar archive"

    def test_extracts_to_linux_510(self):
        """Top-level directory must be linux-5.10/."""
        assert_file_exists(self.TARBALL)
        with tarfile.open(self.TARBALL, "r:gz") as tf:
            names = tf.getnames()
        # All entries should start with linux-5.10/
        top_dirs = set()
        for n in names:
            parts = n.split("/")
            top_dirs.add(parts[0])
        assert "linux-5.10" in top_dirs, \
            f"Tarball must extract to linux-5.10/, found top-level: {top_dirs}"

    def test_kernel_makefile_version(self):
        """linux-5.10/Makefile must have VERSION = 5 and PATCHLEVEL = 10."""
        assert_file_exists(self.TARBALL)
        with tarfile.open(self.TARBALL, "r:gz") as tf:
            # Find the top-level Makefile
            makefile_content = None
            for member in tf.getmembers():
                # Match linux-5.10/Makefile (not in subdirectories)
                if re.match(r"^linux-5\.10/Makefile$", member.name):
                    f = tf.extractfile(member)
                    if f:
                        makefile_content = f.read().decode("utf-8", errors="replace")
                    break
            assert makefile_content is not None, \
                "linux-5.10/Makefile not found in tarball"
            assert re.search(r"VERSION\s*=\s*5", makefile_content), \
                "Kernel Makefile must contain 'VERSION = 5'"
            assert re.search(r"PATCHLEVEL\s*=\s*10", makefile_content), \
                "Kernel Makefile must contain 'PATCHLEVEL = 10'"

    def test_scripts_directory(self):
        """linux-5.10/scripts/ directory must exist."""
        assert_file_exists(self.TARBALL)
        with tarfile.open(self.TARBALL, "r:gz") as tf:
            names = tf.getnames()
        has_scripts = any(
            re.match(r"^linux-5\.10/scripts(/|$)", n) for n in names
        )
        assert has_scripts, "Tarball must contain linux-5.10/scripts/ directory"

    def test_kconfig_or_kbuild(self):
        """Must contain a Kconfig or Kbuild file."""
        assert_file_exists(self.TARBALL)
        with tarfile.open(self.TARBALL, "r:gz") as tf:
            names = tf.getnames()
        has_kconfig = any(
            re.match(r"^linux-5\.10/Kconfig$", n) for n in names
        )
        has_kbuild = any(
            re.match(r"^linux-5\.10/Kbuild$", n) for n in names
        )
        assert has_kconfig or has_kbuild, \
            "Tarball must contain linux-5.10/Kconfig or linux-5.10/Kbuild"

    def test_tarball_not_empty(self):
        """Tarball must have meaningful content (not just empty dirs)."""
        assert_file_exists(self.TARBALL)
        with tarfile.open(self.TARBALL, "r:gz") as tf:
            members = tf.getmembers()
        # Should have at least a few files (Makefile, scripts/, Kconfig/Kbuild)
        assert len(members) >= 3, \
            f"Tarball has too few entries ({len(members)}), expected at least 3"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HELLO.C VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestHelloC:
    """Validate the kernel module source file."""

    PATH = os.path.join(BASE, "module-src", "hello.c")

    def _content(self):
        return read_text(self.PATH)

    def test_not_empty(self):
        c = self._content()
        assert c is not None, "hello.c missing"
        assert len(c.strip()) > 50, "hello.c appears to be empty or trivially small"

    def test_includes_module_h(self):
        c = self._content()
        assert c is not None
        assert re.search(r"#include\s*<linux/module\.h>", c), \
            "hello.c must include <linux/module.h>"

    def test_includes_init_h(self):
        c = self._content()
        assert c is not None
        assert re.search(r"#include\s*<linux/init\.h>", c), \
            "hello.c must include <linux/init.h>"

    def test_module_init_macro(self):
        c = self._content()
        assert c is not None
        assert re.search(r"module_init\s*\(", c), \
            "hello.c must use module_init() macro"

    def test_module_exit_macro(self):
        c = self._content()
        assert c is not None
        assert re.search(r"module_exit\s*\(", c), \
            "hello.c must use module_exit() macro"

    def test_module_license(self):
        c = self._content()
        assert c is not None
        assert re.search(r"MODULE_LICENSE\s*\(", c), \
            "hello.c must contain MODULE_LICENSE() declaration"

    def test_printk_hello_acme(self):
        c = self._content()
        assert c is not None
        # printk with "hello acme" (case-insensitive for the message)
        assert re.search(r"printk\s*\(", c), \
            "hello.c must call printk"
        assert re.search(r"hello\s+acme", c, re.IGNORECASE), \
            "hello.c printk message must contain 'hello acme'"

    def test_has_init_function(self):
        """Must define an actual init function body (not just the macro)."""
        c = self._content()
        assert c is not None
        # Should have __init annotation or a function that's passed to module_init
        assert re.search(r"__init\s+\w+", c) or re.search(r"static\s+int\s+\w+", c), \
            "hello.c must define an init function"

    def test_has_exit_function(self):
        """Must define an actual exit function body."""
        c = self._content()
        assert c is not None
        assert re.search(r"__exit\s+\w+", c) or re.search(r"static\s+void\s+\w+", c), \
            "hello.c must define an exit function"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MODULE MAKEFILE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestModuleMakefile:
    """Validate the kbuild Makefile for the out-of-tree module."""

    PATH = os.path.join(BASE, "module-src", "Makefile")

    def _content(self):
        return read_text(self.PATH)

    def test_not_empty(self):
        c = self._content()
        assert c is not None, "module-src/Makefile missing"
        assert len(c.strip()) > 10, "Makefile appears empty"

    def test_kdir_from_environment(self):
        """Must accept KDIR from environment with ?= or conditional default."""
        c = self._content()
        assert c is not None
        # KDIR ?= or KDIR := or KDIR = with /opt/acme-510/current
        assert re.search(r"KDIR\s*\?=", c), \
            "Makefile must use 'KDIR ?=' to accept KDIR from environment"
        assert "/opt/acme-510/current" in c, \
            "Makefile KDIR default must point to /opt/acme-510/current"

    def test_no_hardcoded_home_paths(self):
        """Must NOT contain hardcoded home directory paths."""
        c = self._content()
        assert c is not None
        # Check for ~ or /home/ or ~/projects
        assert not re.search(r"~/", c), \
            "Makefile must not contain '~/' home directory references"
        assert not re.search(r"/home/", c), \
            "Makefile must not contain '/home/' paths"

    def test_kbuild_pattern(self):
        """Must use kbuild make -C $(KDIR) M= pattern."""
        c = self._content()
        assert c is not None
        # Allow variations: $(KDIR), ${KDIR}
        assert re.search(r"make\s+-C\s+\$[\({]KDIR[\)}]", c), \
            "Makefile must use 'make -C $(KDIR)' kbuild pattern"
        assert re.search(r"M=", c), \
            "Makefile must use 'M=' for out-of-tree module path"

    def test_obj_m_hello(self):
        """Must define obj-m targeting hello module."""
        c = self._content()
        assert c is not None
        # obj-m += hello.o or obj-m := hello.o
        assert re.search(r"obj-m\s*[\+:]?=\s*hello\.o", c), \
            "Makefile must have 'obj-m += hello.o' or 'obj-m := hello.o'"

    def test_has_build_target(self):
        """Must have a default build target (all or default)."""
        c = self._content()
        assert c is not None
        # Look for 'all:' or 'default:' or 'modules:' as a target
        assert re.search(r"^(all|default|modules)\s*:", c, re.MULTILINE), \
            "Makefile must have a default build target (all, default, or modules)"

    def test_has_clean_target(self):
        """Must have a clean target."""
        c = self._content()
        assert c is not None
        assert re.search(r"^clean\s*:", c, re.MULTILINE), \
            "Makefile must have a 'clean' target"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. README VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadme:
    """Validate the README.md documentation."""

    PATH = os.path.join(BASE, "README.md")

    def _content(self):
        return read_text(self.PATH)

    def test_not_empty(self):
        c = self._content()
        assert c is not None, "README.md missing"
        assert len(c.strip()) > 50, "README.md appears empty or trivially small"

    def test_docker_build_command(self):
        """Must contain a docker build command."""
        c = self._content()
        assert c is not None
        assert re.search(r"docker\s+build", c), \
            "README must contain a 'docker build' command"

    def test_docker_run_command(self):
        """Must contain a docker run command."""
        c = self._content()
        assert c is not None
        assert re.search(r"docker\s+run", c), \
            "README must contain a 'docker run' command"

    def test_artifacts_directory_mentioned(self):
        """Must mention /artifacts as the output directory."""
        c = self._content()
        assert c is not None
        assert "/artifacts" in c, \
            "README must mention /artifacts as the output directory"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CROSS-FILE CONSISTENCY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:
    """Verify consistency between artifacts."""

    def test_dockerfile_references_tarball(self):
        """Dockerfile must reference the vendor tarball."""
        c = read_text(os.path.join(BASE, "Dockerfile"))
        assert c is not None
        assert "acme-kernel-5.10.tar.gz" in c, \
            "Dockerfile must reference acme-kernel-5.10.tar.gz"

    def test_dockerfile_copies_module_src(self):
        """Dockerfile must COPY the module source directory."""
        c = read_text(os.path.join(BASE, "Dockerfile"))
        assert c is not None
        assert re.search(r"COPY\s+.*module-src", c), \
            "Dockerfile must COPY module-src/ into the container"

    def test_makefile_module_matches_source(self):
        """Makefile obj-m target must match the .c source file name."""
        makefile = read_text(os.path.join(BASE, "module-src", "Makefile"))
        assert makefile is not None
        # Extract the obj-m target name
        match = re.search(r"obj-m\s*[\+:]?=\s*(\w+)\.o", makefile)
        assert match, "Could not find obj-m target in Makefile"
        module_name = match.group(1)
        # Corresponding .c file must exist
        c_file = os.path.join(BASE, "module-src", f"{module_name}.c")
        assert os.path.isfile(c_file), \
            f"Makefile targets {module_name}.o but {module_name}.c not found"
