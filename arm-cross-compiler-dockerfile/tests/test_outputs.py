"""
Tests for ARM Cross-Compiler Dockerfile task.

Since we cannot run `docker build` in the test environment (it would take hours
and require network access to download source tarballs), we validate the
Dockerfile content itself — its structure, instructions, versions, configuration
flags, build ordering, and correctness.
"""

import os
import re
import pytest

DOCKERFILE_PATH = "/app/Dockerfile"


@pytest.fixture
def dockerfile_content():
    """Read the Dockerfile content, failing if it doesn't exist."""
    assert os.path.isfile(DOCKERFILE_PATH), (
        f"Dockerfile not found at {DOCKERFILE_PATH}"
    )
    with open(DOCKERFILE_PATH, "r") as f:
        content = f.read()
    return content


@pytest.fixture
def dockerfile_lines(dockerfile_content):
    """Return non-empty, stripped lines of the Dockerfile."""
    return [line for line in dockerfile_content.splitlines() if line.strip()]


# ─── 1. Basic file existence and structure ───────────────────────────────────

def test_dockerfile_exists():
    """Dockerfile must exist at /app/Dockerfile."""
    assert os.path.isfile(DOCKERFILE_PATH), (
        f"Expected Dockerfile at {DOCKERFILE_PATH}"
    )


def test_dockerfile_not_empty(dockerfile_content):
    """Dockerfile must not be empty or trivially small."""
    stripped = dockerfile_content.strip()
    assert len(stripped) > 500, (
        f"Dockerfile is too small ({len(stripped)} chars). "
        "A valid cross-compiler Dockerfile should be substantial."
    )


def test_dockerfile_has_from(dockerfile_content):
    """Dockerfile must start with a FROM instruction."""
    # Find the first non-comment, non-empty line
    for line in dockerfile_content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            assert stripped.upper().startswith("FROM"), (
                f"First instruction must be FROM, got: {stripped}"
            )
            break


# ─── 2. Base image ──────────────────────────────────────────────────────────

def test_base_image_ubuntu_2204(dockerfile_content):
    """Base image must be ubuntu:22.04."""
    assert re.search(r"FROM\s+ubuntu:22\.04", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must use ubuntu:22.04 as the base image"
    )


# ─── 3. Source versions ─────────────────────────────────────────────────────

def test_binutils_version(dockerfile_content):
    """Must use binutils 2.42."""
    assert re.search(r"binutils.*2\.42|2\.42.*binutils|BINUTILS_VERSION.*2\.42", dockerfile_content), (
        "Dockerfile must reference binutils version 2.42"
    )


def test_gcc_version(dockerfile_content):
    """Must use GCC 13.2.0."""
    assert re.search(r"gcc.*13\.2\.0|13\.2\.0.*gcc|GCC_VERSION.*13\.2\.0", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference GCC version 13.2.0"
    )


def test_glibc_version(dockerfile_content):
    """Must use glibc 2.38."""
    assert re.search(r"glibc.*2\.38|2\.38.*glibc|GLIBC_VERSION.*2\.38", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference glibc version 2.38"
    )


def test_linux_kernel_version(dockerfile_content):
    """Must use Linux kernel 6.6.x headers."""
    assert re.search(r"linux.*6\.6\.\d+|LINUX_VERSION.*6\.6", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference Linux kernel version 6.6.x"
    )


def test_gmp_version(dockerfile_content):
    """Must use gmp 6.3.0."""
    assert re.search(r"gmp.*6\.3\.0|GMP_VERSION.*6\.3\.0", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference gmp version 6.3.0"
    )


def test_mpfr_version(dockerfile_content):
    """Must use mpfr 4.2.1."""
    assert re.search(r"mpfr.*4\.2\.1|MPFR_VERSION.*4\.2\.1", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference mpfr version 4.2.1"
    )


def test_mpc_version(dockerfile_content):
    """Must use mpc 1.3.1."""
    assert re.search(r"mpc.*1\.3\.1|MPC_VERSION.*1\.3\.1", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference mpc version 1.3.1"
    )


def test_isl_version(dockerfile_content):
    """Must use isl 0.26."""
    assert re.search(r"isl.*0\.26|ISL_VERSION.*0\.26", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must reference isl version 0.26"
    )


# ─── 4. Target architecture and triplet ─────────────────────────────────────

def test_target_triplet(dockerfile_content):
    """Must target arm-linux-gnueabihf."""
    assert "arm-linux-gnueabihf" in dockerfile_content, (
        "Dockerfile must reference target triplet arm-linux-gnueabihf"
    )


def test_armv7a_architecture(dockerfile_content):
    """Must configure for armv7-a architecture."""
    assert re.search(r"armv7-a|armv7a", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must configure for armv7-a architecture"
    )


def test_hard_float_abi(dockerfile_content):
    """Must use hard-float ABI."""
    # Check for either configure flag or compiler flag style
    assert re.search(r"(float.*hard|hard.*float|mfloat-abi=hard)", dockerfile_content), (
        "Dockerfile must configure hard-float ABI"
    )


def test_cortex_a9_cpu(dockerfile_content):
    """Must target Cortex-A9 CPU."""
    assert re.search(r"cortex.a9", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must target Cortex-A9 CPU"
    )


def test_vfp_fpu(dockerfile_content):
    """Must configure VFPv3-D16 or NEON FPU."""
    assert re.search(r"vfpv3-d16|vfpv3|neon", dockerfile_content, re.IGNORECASE), (
        "Dockerfile must configure VFPv3-D16 or NEON FPU"
    )


# ─── 5. Non-root build user ─────────────────────────────────────────────────

def test_xbuilder_user_created(dockerfile_content):
    """Must create a non-root user named xbuilder."""
    assert re.search(r"useradd.*xbuilder|adduser.*xbuilder", dockerfile_content), (
        "Dockerfile must create a non-root user named 'xbuilder'"
    )


def test_user_switch_to_xbuilder(dockerfile_content):
    """Must switch to xbuilder user for build steps."""
    assert re.search(r"^USER\s+xbuilder", dockerfile_content, re.MULTILINE), (
        "Dockerfile must switch to xbuilder user (USER xbuilder) for compilation"
    )


# ─── 6. Toolchain prefix ────────────────────────────────────────────────────

def test_cross_prefix(dockerfile_content):
    """Toolchain install prefix must be /cross."""
    assert re.search(r"PREFIX.*=/cross|--prefix=/cross|prefix=/cross", dockerfile_content), (
        "Dockerfile must use /cross as the toolchain install prefix"
    )


# ─── 7. Build stages and ordering ───────────────────────────────────────────

def test_binutils_configure(dockerfile_content):
    """Must configure and build binutils."""
    assert re.search(r"binutils.*configure|configure.*binutils", dockerfile_content, re.DOTALL), (
        "Dockerfile must configure binutils"
    )


def test_kernel_headers_install(dockerfile_content):
    """Must install Linux kernel headers."""
    assert re.search(r"headers_install|INSTALL_HDR_PATH", dockerfile_content), (
        "Dockerfile must install Linux kernel headers"
    )


def test_stage1_gcc_c_only(dockerfile_content):
    """Stage-1 GCC must be C-only (bootstrap)."""
    # Look for a configure block that has --enable-languages=c (without c++)
    # and bootstrap flags like --without-headers or --with-newlib
    has_bootstrap_flag = bool(re.search(
        r"(--without-headers|--with-newlib)", dockerfile_content
    ))
    has_c_only = bool(re.search(
        r"--enable-languages=c\b", dockerfile_content
    ))
    assert has_bootstrap_flag, (
        "Stage-1 GCC must use --without-headers or --with-newlib for bootstrap"
    )
    assert has_c_only, (
        "Stage-1 GCC must have --enable-languages=c (C-only)"
    )


def test_stage1_gcc_disable_shared(dockerfile_content):
    """Stage-1 GCC must disable shared libraries."""
    assert "--disable-shared" in dockerfile_content, (
        "Stage-1 GCC must use --disable-shared"
    )


def test_glibc_configure(dockerfile_content):
    """Must configure and build glibc."""
    assert re.search(r"glibc.*configure|configure.*glibc", dockerfile_content, re.DOTALL), (
        "Dockerfile must configure glibc"
    )


def test_stage2_gcc_cpp_support(dockerfile_content):
    """Stage-2 GCC must enable C and C++ languages."""
    assert re.search(r"--enable-languages=c,c\+\+", dockerfile_content), (
        "Stage-2 GCC must enable both C and C++ (--enable-languages=c,c++)"
    )


def test_stage2_gcc_lto(dockerfile_content):
    """Stage-2 GCC must enable link-time optimization."""
    assert "--enable-lto" in dockerfile_content, (
        "Stage-2 GCC must use --enable-lto"
    )


def test_build_order_binutils_before_gcc(dockerfile_content):
    """Binutils must be built before any GCC stage."""
    # Match actual configure invocations, not ENV variable definitions
    # Look for path-style references: binutils-*/configure or build-binutils
    binutils_pos = re.search(r"binutils.*/configure|build.binutils", dockerfile_content)
    # For GCC, look for gcc-*/configure or build-gcc
    gcc_pos = re.search(r"gcc.*/configure|build.gcc", dockerfile_content, re.IGNORECASE)
    assert binutils_pos is not None, "Binutils configure step not found"
    assert gcc_pos is not None, "GCC configure step not found"
    assert binutils_pos.start() < gcc_pos.start(), (
        "Binutils must be configured before GCC"
    )


def test_build_order_headers_before_glibc(dockerfile_content):
    """Kernel headers must be installed before glibc is built."""
    headers_pos = re.search(r"headers_install", dockerfile_content)
    # Match actual glibc configure invocation, not download references
    glibc_pos = re.search(r"glibc.*/configure|build.glibc", dockerfile_content)
    assert headers_pos is not None, "Kernel headers_install step not found"
    assert glibc_pos is not None, "glibc configure step not found"
    assert headers_pos.start() < glibc_pos.start(), (
        "Kernel headers must be installed before glibc is configured"
    )


def test_build_order_glibc_before_stage2_gcc(dockerfile_content):
    """glibc must be built before stage-2 GCC."""
    # Match actual glibc configure invocation
    glibc_pos = re.search(r"glibc.*/configure|build.glibc", dockerfile_content)
    # Stage-2 GCC is identified by --enable-languages=c,c++
    stage2_pos = re.search(r"--enable-languages=c,c\+\+", dockerfile_content)
    assert glibc_pos is not None, "glibc configure step not found"
    assert stage2_pos is not None, "Stage-2 GCC configure step not found"
    assert glibc_pos.start() < stage2_pos.start(), (
        "glibc must be built before stage-2 GCC"
    )


# ─── 8. Source downloads ────────────────────────────────────────────────────

def test_downloads_binutils(dockerfile_content):
    """Must download binutils source tarball."""
    assert re.search(r"(wget|curl).*binutils.*\.tar", dockerfile_content, re.DOTALL), (
        "Dockerfile must download binutils source tarball"
    )


def test_downloads_gcc(dockerfile_content):
    """Must download GCC source tarball."""
    assert re.search(r"(wget|curl).*gcc.*\.tar", dockerfile_content, re.DOTALL | re.IGNORECASE), (
        "Dockerfile must download GCC source tarball"
    )


def test_downloads_glibc(dockerfile_content):
    """Must download glibc source tarball."""
    assert re.search(r"(wget|curl).*glibc.*\.tar", dockerfile_content, re.DOTALL), (
        "Dockerfile must download glibc source tarball"
    )


def test_downloads_linux_kernel(dockerfile_content):
    """Must download Linux kernel source tarball."""
    assert re.search(r"(wget|curl).*linux.*\.tar", dockerfile_content, re.DOTALL), (
        "Dockerfile must download Linux kernel source tarball"
    )


# ─── 9. Reproducible tarball ────────────────────────────────────────────────

def test_output_tarball_path(dockerfile_content):
    """Output tarball must be at /tmp/arm-cortex-a9--linux-gnueabihf.tar.xz."""
    assert "arm-cortex-a9--linux-gnueabihf.tar.xz" in dockerfile_content, (
        "Dockerfile must produce /tmp/arm-cortex-a9--linux-gnueabihf.tar.xz"
    )


def test_reproducible_tar_sort(dockerfile_content):
    """Tarball must use deterministic file ordering."""
    assert "--sort=name" in dockerfile_content, (
        "Tarball creation must use --sort=name for reproducibility"
    )


def test_reproducible_tar_mtime(dockerfile_content):
    """Tarball must use normalized timestamps."""
    assert re.search(r"--mtime", dockerfile_content), (
        "Tarball creation must use --mtime for reproducible timestamps"
    )


def test_reproducible_tar_owner(dockerfile_content):
    """Tarball must use normalized ownership."""
    assert re.search(r"--owner=0", dockerfile_content), (
        "Tarball creation must use --owner=0 for reproducible ownership"
    )


def test_reproducible_tar_group(dockerfile_content):
    """Tarball must use normalized group."""
    assert re.search(r"--group=0", dockerfile_content), (
        "Tarball creation must use --group=0 for reproducible ownership"
    )


# ─── 10. Post-build stripping ───────────────────────────────────────────────

def test_strip_binaries(dockerfile_content):
    """Must strip debug symbols from binaries."""
    assert re.search(r"strip", dockerfile_content), (
        "Dockerfile must strip debug symbols from binaries"
    )


# ─── 11. Sanity check ───────────────────────────────────────────────────────

def test_sanity_check_hello_world(dockerfile_content):
    """Must compile a Hello World program with the cross-compiler."""
    # Check for a C source with printf/puts and main
    has_hello_source = bool(re.search(
        r'(printf|puts).*[Hh]ello', dockerfile_content
    ))
    # Accept both literal triplet and variable-based references like ${TARGET}-gcc
    has_cross_compile = bool(re.search(
        r'arm-linux-gnueabihf-gcc|\$\{?TARGET\}?-gcc', dockerfile_content
    ))
    assert has_hello_source, (
        "Dockerfile must include a Hello World C source for sanity check"
    )
    assert has_cross_compile, (
        "Dockerfile must compile Hello World with arm-linux-gnueabihf-gcc"
    )


def test_sanity_check_qemu(dockerfile_content):
    """Must run the compiled binary with qemu-arm."""
    assert re.search(r"qemu-arm|qemu-user", dockerfile_content), (
        "Dockerfile must use qemu-arm to run the cross-compiled binary"
    )


def test_qemu_installed(dockerfile_content):
    """Must install qemu-user or qemu-user-static."""
    assert re.search(r"qemu-user-static|qemu-user", dockerfile_content), (
        "Dockerfile must install qemu-user or qemu-user-static"
    )


# ─── 12. Build dependencies ─────────────────────────────────────────────────

def test_build_essential_installed(dockerfile_content):
    """Must install build-essential."""
    assert "build-essential" in dockerfile_content, (
        "Dockerfile must install build-essential"
    )


def test_essential_build_tools(dockerfile_content):
    """Must install essential build tools (texinfo, bison, flex, gawk)."""
    missing = []
    for tool in ["texinfo", "bison", "flex", "gawk"]:
        if tool not in dockerfile_content:
            missing.append(tool)
    assert not missing, (
        f"Dockerfile must install these build tools: {', '.join(missing)}"
    )


# ─── 13. GCC prerequisites linked ───────────────────────────────────────────

def test_gcc_prerequisites_linked(dockerfile_content):
    """GCC prerequisites (gmp, mpfr, mpc, isl) must be linked or configured."""
    # Either symlinked into GCC source tree or passed via --with-gmp etc.
    for lib in ["gmp", "mpfr", "mpc", "isl"]:
        has_link = bool(re.search(rf"ln\s.*{lib}", dockerfile_content))
        has_with = bool(re.search(rf"--with-{lib}", dockerfile_content))
        has_download = bool(re.search(rf"download_prerequisites", dockerfile_content))
        assert has_link or has_with or has_download, (
            f"GCC prerequisite '{lib}' must be linked into source tree, "
            f"passed via --with-{lib}, or fetched via download_prerequisites"
        )


# ─── 14. Sysroot configuration ──────────────────────────────────────────────

def test_sysroot_configured(dockerfile_content):
    """Must configure sysroot for the cross-compiler."""
    assert re.search(r"--with-sysroot", dockerfile_content), (
        "Dockerfile must configure --with-sysroot for the cross-compiler"
    )


def test_disable_multilib(dockerfile_content):
    """Must disable multilib (single target)."""
    assert "--disable-multilib" in dockerfile_content, (
        "Dockerfile must use --disable-multilib"
    )


# ─── 15. Valid Dockerfile syntax ─────────────────────────────────────────────

def test_has_run_instructions(dockerfile_content):
    """Dockerfile must contain RUN instructions for building."""
    run_count = len(re.findall(r"^RUN\s", dockerfile_content, re.MULTILINE))
    assert run_count >= 5, (
        f"Dockerfile has only {run_count} RUN instructions; "
        "expected at least 5 for a full cross-compiler build"
    )


def test_has_env_instructions(dockerfile_content):
    """Dockerfile must set environment variables."""
    assert re.search(r"^ENV\s", dockerfile_content, re.MULTILINE), (
        "Dockerfile must use ENV to set variables (e.g., TARGET, PREFIX)"
    )


def test_has_workdir(dockerfile_content):
    """Dockerfile must set a WORKDIR."""
    assert re.search(r"^WORKDIR\s", dockerfile_content, re.MULTILINE), (
        "Dockerfile must use WORKDIR instruction"
    )
