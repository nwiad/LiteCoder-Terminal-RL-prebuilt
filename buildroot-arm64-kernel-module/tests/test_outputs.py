"""
Tests for Buildroot ARM64 Kernel Module task.
Validates the complete directory structure, file contents, and buildroot
package infrastructure created under /app/.
"""
import os
import re
import pytest

BASE = "/app"
BR2_EXT = os.path.join(BASE, "br2-external")
PKG_DIR = os.path.join(BR2_EXT, "package", "hello-world-module")
SRC_DIR = os.path.join(PKG_DIR, "src")
CONFIGS_DIR = os.path.join(BR2_EXT, "configs")
BOARD_DIR = os.path.join(BR2_EXT, "board", "qemu-aarch64", "rootfs_overlay", "lib", "modules")


def _read(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return ""


# ============================================================================
# 1. DIRECTORY STRUCTURE — File existence
# ============================================================================

class TestFileExistence:
    """All required files must exist and be non-empty (where applicable)."""

    REQUIRED_FILES = [
        os.path.join(BASE, "Makefile"),
        os.path.join(BASE, "BUILD_NOTES.txt"),
        os.path.join(BR2_EXT, "external.desc"),
        os.path.join(BR2_EXT, "external.mk"),
        os.path.join(BR2_EXT, "Config.in"),
        os.path.join(CONFIGS_DIR, "qemu_aarch64_hello_defconfig"),
        os.path.join(PKG_DIR, "Config.in"),
        os.path.join(PKG_DIR, "hello-world-module.mk"),
        os.path.join(SRC_DIR, "hello.c"),
        os.path.join(SRC_DIR, "Makefile"),
    ]

    @pytest.mark.parametrize("fpath", REQUIRED_FILES)
    def test_file_exists(self, fpath):
        assert os.path.isfile(fpath), f"Required file missing: {fpath}"

    @pytest.mark.parametrize("fpath", REQUIRED_FILES)
    def test_file_not_empty(self, fpath):
        if os.path.isfile(fpath):
            assert os.path.getsize(fpath) > 0, f"File is empty: {fpath}"

    def test_buildroot_cloned(self):
        """Buildroot repo must be cloned into /app/buildroot/."""
        assert os.path.isdir(os.path.join(BASE, "buildroot")), \
            "Buildroot directory missing at /app/buildroot/"
        # Must have some buildroot content (Makefile or .git)
        br_dir = os.path.join(BASE, "buildroot")
        has_git = os.path.isdir(os.path.join(br_dir, ".git"))
        has_makefile = os.path.isfile(os.path.join(br_dir, "Makefile"))
        assert has_git or has_makefile, \
            "Buildroot dir exists but appears empty (no .git or Makefile)"

    def test_board_overlay_dir_exists(self):
        """Board overlay directory structure must exist."""
        assert os.path.isdir(BOARD_DIR), \
            f"Board overlay dir missing: {BOARD_DIR}"

    def test_gitkeep_in_overlay(self):
        """A .gitkeep placeholder must exist in the modules overlay dir."""
        gitkeep = os.path.join(BOARD_DIR, ".gitkeep")
        assert os.path.isfile(gitkeep), f".gitkeep missing in {BOARD_DIR}"


# ============================================================================
# 2. KERNEL MODULE SOURCE — hello.c
# ============================================================================

class TestHelloC:
    """Validate the kernel module source file."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(SRC_DIR, "hello.c"))

    def test_includes_linux_init(self):
        assert re.search(r"#include\s+<linux/init\.h>", self.content), \
            "hello.c must include <linux/init.h>"

    def test_includes_linux_module(self):
        assert re.search(r"#include\s+<linux/module\.h>", self.content), \
            "hello.c must include <linux/module.h>"

    def test_module_license_gpl(self):
        assert re.search(r'MODULE_LICENSE\s*\(\s*"GPL"\s*\)', self.content), \
            'hello.c must have MODULE_LICENSE("GPL")'

    def test_module_author(self):
        assert re.search(r'MODULE_AUTHOR\s*\(\s*"Embedded Team"\s*\)', self.content), \
            'hello.c must have MODULE_AUTHOR("Embedded Team")'

    def test_init_printk_message(self):
        assert re.search(r'printk\s*\(.*".*Hello,\s*Buildroot World!', self.content), \
            'init function must printk "Hello, Buildroot World!"'

    def test_exit_printk_message(self):
        assert re.search(r'printk\s*\(.*".*Goodbye,\s*Buildroot World!', self.content), \
            'exit function must printk "Goodbye, Buildroot World!"'

    def test_module_init_macro(self):
        assert re.search(r'module_init\s*\(', self.content), \
            "hello.c must use module_init() macro"

    def test_module_exit_macro(self):
        assert re.search(r'module_exit\s*\(', self.content), \
            "hello.c must use module_exit() macro"

    def test_init_function_signature(self):
        """Must have a proper __init function returning int."""
        assert re.search(r'static\s+int\s+__init\s+\w+', self.content), \
            "hello.c must have a static int __init function"

    def test_exit_function_signature(self):
        """Must have a proper __exit function."""
        assert re.search(r'static\s+void\s+__exit\s+\w+', self.content), \
            "hello.c must have a static void __exit function"


# ============================================================================
# 3. KBUILD MAKEFILE — src/Makefile
# ============================================================================

class TestKbuildMakefile:
    """Validate the Kbuild Makefile for the kernel module."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(SRC_DIR, "Makefile"))

    def test_obj_m_directive(self):
        """Must use obj-m to build as a module."""
        assert re.search(r'obj-m\s*[\+:]?=\s*.*hello_world', self.content), \
            "Kbuild Makefile must have obj-m referencing hello_world"

    def test_builds_hello_world_module(self):
        """Must target hello_world as the module object."""
        assert "hello_world" in self.content, \
            "Kbuild Makefile must reference hello_world"


# ============================================================================
# 4. EXTERNAL DESCRIPTOR — external.desc
# ============================================================================

class TestExternalDesc:
    """Validate the BR2_EXTERNAL descriptor file."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(BR2_EXT, "external.desc"))

    def test_has_name_field(self):
        assert re.search(r'^name:\s*\S+', self.content, re.MULTILINE), \
            "external.desc must have a 'name:' field"

    def test_name_is_hello_world_ext(self):
        assert re.search(r'^name:\s*HELLO_WORLD_EXT', self.content, re.MULTILINE), \
            "external.desc name must be HELLO_WORLD_EXT"

    def test_has_desc_field(self):
        assert re.search(r'^desc:\s*\S+', self.content, re.MULTILINE), \
            "external.desc must have a 'desc:' field"


# ============================================================================
# 5. TOP-LEVEL Config.in
# ============================================================================

class TestTopConfigIn:
    """Validate the top-level Config.in for the external tree."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(BR2_EXT, "Config.in"))

    def test_sources_package_config(self):
        """Must source the hello-world-module Config.in via BR2_EXTERNAL path."""
        assert re.search(
            r'source\s+.*BR2_EXTERNAL_HELLO_WORLD_EXT_PATH.*package/hello-world-module/Config\.in',
            self.content
        ), "Config.in must source the package Config.in via BR2_EXTERNAL_HELLO_WORLD_EXT_PATH"


# ============================================================================
# 6. EXTERNAL.MK
# ============================================================================

class TestExternalMk:
    """Validate the external.mk include file."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(BR2_EXT, "external.mk"))

    def test_includes_package_mk_files(self):
        """Must include package .mk files via wildcard."""
        assert re.search(
            r'include\s+.*wildcard.*BR2_EXTERNAL_HELLO_WORLD_EXT_PATH.*package/\*',
            self.content
        ), "external.mk must include package .mk files via wildcard pattern"


# ============================================================================
# 7. PACKAGE Config.in
# ============================================================================

class TestPackageConfigIn:
    """Validate the package-level Config.in."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(PKG_DIR, "Config.in"))

    def test_defines_config_option(self):
        assert re.search(r'config\s+BR2_PACKAGE_HELLO_WORLD_MODULE', self.content), \
            "Package Config.in must define BR2_PACKAGE_HELLO_WORLD_MODULE"

    def test_bool_type(self):
        assert re.search(r'bool\s', self.content), \
            "Package Config.in must use bool type"

    def test_depends_on_kernel(self):
        assert re.search(r'depends\s+on\s+BR2_LINUX_KERNEL', self.content), \
            "Package Config.in must depend on BR2_LINUX_KERNEL"

    def test_has_help_text(self):
        assert re.search(r'help', self.content), \
            "Package Config.in must have help text"


# ============================================================================
# 8. PACKAGE .MK FILE — hello-world-module.mk
# ============================================================================

class TestPackageMk:
    """Validate the buildroot package .mk file."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(PKG_DIR, "hello-world-module.mk"))

    def test_version_defined(self):
        assert re.search(r'HELLO_WORLD_MODULE_VERSION\s*=', self.content), \
            ".mk must define HELLO_WORLD_MODULE_VERSION"

    def test_site_defined(self):
        assert re.search(
            r'HELLO_WORLD_MODULE_SITE\s*=.*BR2_EXTERNAL_HELLO_WORLD_EXT_PATH.*package/hello-world-module/src',
            self.content
        ), ".mk must define HELLO_WORLD_MODULE_SITE pointing to src dir"

    def test_site_method_local(self):
        assert re.search(r'HELLO_WORLD_MODULE_SITE_METHOD\s*=\s*local', self.content), \
            ".mk must use local site method"

    def test_eval_kernel_module(self):
        assert re.search(r'\$\(eval\s+\$\(kernel-module\)\)', self.content), \
            ".mk must use $(eval $(kernel-module))"

    def test_eval_generic_package(self):
        assert re.search(r'\$\(eval\s+\$\(generic-package\)\)', self.content), \
            ".mk must use $(eval $(generic-package))"

    def test_kernel_module_before_generic(self):
        """kernel-module eval must come before generic-package eval."""
        km_match = re.search(r'\$\(eval\s+\$\(kernel-module\)\)', self.content)
        gp_match = re.search(r'\$\(eval\s+\$\(generic-package\)\)', self.content)
        if km_match and gp_match:
            assert km_match.start() < gp_match.start(), \
                "$(eval $(kernel-module)) must appear before $(eval $(generic-package))"


# ============================================================================
# 9. CUSTOM DEFCONFIG
# ============================================================================

class TestDefconfig:
    """Validate the custom defconfig for QEMU aarch64."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(
            os.path.join(CONFIGS_DIR, "qemu_aarch64_hello_defconfig")
        )

    def test_aarch64_enabled(self):
        assert re.search(r'^BR2_aarch64\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_aarch64=y"

    def test_toolchain_external(self):
        assert re.search(r'^BR2_TOOLCHAIN_EXTERNAL\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_TOOLCHAIN_EXTERNAL=y"

    def test_linux_kernel_enabled(self):
        assert re.search(r'^BR2_LINUX_KERNEL\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_LINUX_KERNEL=y"

    def test_kernel_use_defconfig(self):
        assert re.search(r'^BR2_LINUX_KERNEL_USE_DEFCONFIG\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_LINUX_KERNEL_USE_DEFCONFIG=y"

    def test_hello_world_module_enabled(self):
        assert re.search(r'^BR2_PACKAGE_HELLO_WORLD_MODULE\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_PACKAGE_HELLO_WORLD_MODULE=y"

    def test_rootfs_ext2(self):
        assert re.search(r'^BR2_TARGET_ROOTFS_EXT2\s*=\s*y', self.content, re.MULTILINE), \
            "Defconfig must set BR2_TARGET_ROOTFS_EXT2=y"

    def test_rootfs_overlay(self):
        assert re.search(r'^BR2_ROOTFS_OVERLAY\s*=', self.content, re.MULTILINE), \
            "Defconfig must set BR2_ROOTFS_OVERLAY"
        # The overlay path should reference the board directory
        assert re.search(r'board.*qemu.*aarch64.*rootfs_overlay', self.content), \
            "BR2_ROOTFS_OVERLAY must point to the board overlay directory"


# ============================================================================
# 10. TOP-LEVEL MAKEFILE
# ============================================================================

class TestTopMakefile:
    """Validate the top-level Makefile."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(BASE, "Makefile"))

    def test_br2_external_set(self):
        """Must set BR2_EXTERNAL to the external tree path."""
        assert re.search(r'BR2_EXTERNAL\s*[:?]?=\s*.*br2-external', self.content), \
            "Makefile must set BR2_EXTERNAL to br2-external path"

    def test_buildroot_dir_reference(self):
        """Must reference the buildroot directory."""
        assert re.search(r'buildroot', self.content), \
            "Makefile must reference the buildroot directory"

    def test_all_target(self):
        """Must have an 'all' target."""
        assert re.search(r'^all\s*:', self.content, re.MULTILINE), \
            "Makefile must have an 'all' target"

    def test_defconfig_target(self):
        """Must have a 'defconfig' target."""
        assert re.search(r'^defconfig\s*:', self.content, re.MULTILINE), \
            "Makefile must have a 'defconfig' target"

    def test_clean_target(self):
        """Must have a 'clean' target."""
        assert re.search(r'^clean\s*:', self.content, re.MULTILINE), \
            "Makefile must have a 'clean' target"

    def test_all_invokes_buildroot_make(self):
        """The all target must delegate to buildroot's make with BR2_EXTERNAL."""
        # Look for $(MAKE) or make with BR2_EXTERNAL in the file
        assert re.search(r'MAKE.*BR2_EXTERNAL|BR2_EXTERNAL.*MAKE', self.content) or \
               re.search(r'make.*BR2_EXTERNAL|BR2_EXTERNAL.*make', self.content, re.IGNORECASE), \
            "Makefile targets must invoke buildroot make with BR2_EXTERNAL"

    def test_phony_targets(self):
        """Should declare PHONY targets."""
        assert re.search(r'\.PHONY', self.content), \
            "Makefile should declare .PHONY targets"


# ============================================================================
# 11. BUILD_NOTES.TXT
# ============================================================================

class TestBuildNotes:
    """Validate BUILD_NOTES.txt documentation."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = _read(os.path.join(BASE, "BUILD_NOTES.txt"))
        self.content_lower = self.content.lower()

    def test_mentions_host_dependencies(self):
        """Must document host dependencies."""
        required_deps = ["build-essential", "libncurses", "wget", "bc", "cpio", "python3"]
        found = sum(1 for dep in required_deps if dep in self.content_lower)
        assert found >= 4, \
            f"BUILD_NOTES.txt must mention most host dependencies, found {found}/6"

    def test_mentions_buildroot_version(self):
        """Must document the buildroot version/tag."""
        assert re.search(r'2024\.02|20\d{2}\.\d{2}', self.content), \
            "BUILD_NOTES.txt must mention the buildroot version/tag"

    def test_mentions_build_commands(self):
        """Must document the build sequence (defconfig + make)."""
        assert "defconfig" in self.content_lower, \
            "BUILD_NOTES.txt must mention defconfig step"
        has_make = "make" in self.content_lower or "build" in self.content_lower
        assert has_make, \
            "BUILD_NOTES.txt must mention the build command"

    def test_mentions_ko_verification(self):
        """Must document how to verify the .ko module."""
        assert ".ko" in self.content or "hello_world" in self.content, \
            "BUILD_NOTES.txt must mention .ko module verification"

    def test_mentions_qemu_boot(self):
        """Must document QEMU boot instructions."""
        assert "qemu" in self.content_lower, \
            "BUILD_NOTES.txt must mention QEMU boot"

    def test_mentions_insmod(self):
        """Must document how to load the module."""
        assert "insmod" in self.content_lower or "modprobe" in self.content_lower, \
            "BUILD_NOTES.txt must mention insmod or modprobe"

    def test_minimum_length(self):
        """BUILD_NOTES.txt should be substantive documentation, not a stub."""
        assert len(self.content.strip()) > 200, \
            "BUILD_NOTES.txt is too short to be meaningful documentation"


# ============================================================================
# 12. CROSS-FILE CONSISTENCY CHECKS
# ============================================================================

class TestCrossFileConsistency:
    """Verify consistency across multiple files."""

    def test_defconfig_name_matches_makefile(self):
        """The defconfig filename referenced in the Makefile must match the actual file."""
        makefile = _read(os.path.join(BASE, "Makefile"))
        defconfig_file = os.path.join(CONFIGS_DIR, "qemu_aarch64_hello_defconfig")
        assert os.path.isfile(defconfig_file), "Defconfig file must exist"
        # The Makefile should reference this defconfig name
        assert "qemu_aarch64_hello_defconfig" in makefile, \
            "Makefile defconfig target must reference qemu_aarch64_hello_defconfig"

    def test_external_desc_name_consistent(self):
        """The name in external.desc must match the BR2_EXTERNAL variable used elsewhere."""
        desc = _read(os.path.join(BR2_EXT, "external.desc"))
        config_in = _read(os.path.join(BR2_EXT, "Config.in"))
        ext_mk = _read(os.path.join(BR2_EXT, "external.mk"))
        # Extract name from external.desc
        m = re.search(r'^name:\s*(\S+)', desc, re.MULTILINE)
        assert m, "external.desc must have a name field"
        ext_name = m.group(1)
        # The derived BR2_EXTERNAL_<NAME>_PATH must appear in Config.in and external.mk
        br2_var = f"BR2_EXTERNAL_{ext_name}_PATH"
        assert br2_var in config_in, \
            f"Config.in must use {br2_var} (derived from external.desc name)"
        assert br2_var in ext_mk, \
            f"external.mk must use {br2_var} (derived from external.desc name)"

    def test_package_mk_site_points_to_existing_src(self):
        """The SITE in .mk must reference a path where hello.c actually exists."""
        pkg_mk = _read(os.path.join(PKG_DIR, "hello-world-module.mk"))
        assert "package/hello-world-module/src" in pkg_mk, \
            ".mk SITE must reference package/hello-world-module/src"
        assert os.path.isfile(os.path.join(SRC_DIR, "hello.c")), \
            "hello.c must exist at the path referenced by SITE"

