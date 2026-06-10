"""
Tests for Emscripten WebAssembly Primes Build Task.

Validates that:
1. /app/primes.c exists with correct prime computation logic and exported function
2. /app/primes.html exists as a self-contained HTML file with inline WASM
3. No sidecar .wasm or .js files are produced
4. The HTML embeds base64-encoded WebAssembly data
5. The HTML has proper structure and is non-trivially sized
"""

import os
import re

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PRIMES_C = "/app/primes.c"
PRIMES_HTML = "/app/primes.html"
PRIMES_WASM = "/app/primes.wasm"
PRIMES_JS = "/app/primes.js"
APP_DIR = "/app"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", errors="replace") as f:
        return f.read()


def file_size(path):
    """Return file size in bytes, 0 if missing."""
    if not os.path.isfile(path):
        return 0
    return os.path.getsize(path)


# ===========================================================================
# Test Group 1: File Existence and Basic Properties
# ===========================================================================

class TestFileExistence:
    """Verify that required output files exist and are non-empty."""

    def test_primes_c_exists(self):
        """primes.c must exist at /app/primes.c"""
        assert os.path.isfile(PRIMES_C), f"{PRIMES_C} does not exist"

    def test_primes_c_not_empty(self):
        """primes.c must not be empty"""
        size = file_size(PRIMES_C)
        assert size > 0, f"{PRIMES_C} is empty (0 bytes)"

    def test_primes_html_exists(self):
        """primes.html must exist at /app/primes.html"""
        assert os.path.isfile(PRIMES_HTML), f"{PRIMES_HTML} does not exist"

    def test_primes_html_not_empty(self):
        """primes.html must not be empty"""
        size = file_size(PRIMES_HTML)
        assert size > 0, f"{PRIMES_HTML} is empty (0 bytes)"

    def test_primes_html_substantial_size(self):
        """
        A real Emscripten single-file HTML output is typically >50 KB because
        it embeds the JS runtime and base64-encoded WASM binary.
        A trivially small file indicates the build didn't actually run.
        """
        size = file_size(PRIMES_HTML)
        # Even a minimal Emscripten single-file build produces >30 KB
        assert size > 30_000, (
            f"{PRIMES_HTML} is only {size} bytes — too small for a real "
            f"Emscripten single-file HTML build (expected >30 KB)"
        )


# ===========================================================================
# Test Group 2: C Source File Validation
# ===========================================================================

class TestCSourceFile:
    """Validate the C source contains required elements."""

    def test_contains_get_primes_function(self):
        """primes.c must define the get_primes function."""
        content = read_file(PRIMES_C)
        assert content is not None, f"{PRIMES_C} not found"
        # Match function definition: return type, function name, int parameter
        assert re.search(r'get_primes\s*\(', content), (
            "primes.c does not contain a 'get_primes' function definition"
        )

    def test_contains_prime_logic(self):
        """primes.c must contain prime number computation logic."""
        content = read_file(PRIMES_C)
        assert content is not None, f"{PRIMES_C} not found"
        # A prime sieve or trial division will typically use modulo operator
        # and some form of loop. Check for basic indicators.
        has_modulo = "%" in content
        has_loop = ("while" in content or "for" in content)
        assert has_modulo and has_loop, (
            "primes.c does not appear to contain prime computation logic "
            "(expected modulo operator and loop constructs)"
        )

    def test_emscripten_export_annotation(self):
        """
        The get_primes function must be exported for JS interop.
        This is typically done via EMSCRIPTEN_KEEPALIVE or by listing
        in EXPORTED_FUNCTIONS. Check for at least one indicator.
        """
        content = read_file(PRIMES_C)
        assert content is not None, f"{PRIMES_C} not found"
        has_keepalive = "EMSCRIPTEN_KEEPALIVE" in content
        has_emscripten_h = "emscripten.h" in content or "emscripten/emscripten.h" in content
        # Either EMSCRIPTEN_KEEPALIVE annotation or emscripten header inclusion
        # indicates awareness of the export mechanism
        assert has_keepalive or has_emscripten_h, (
            "primes.c does not use EMSCRIPTEN_KEEPALIVE or include emscripten.h — "
            "the get_primes function may not be properly exported"
        )

    def test_includes_stdlib(self):
        """primes.c should include stdlib.h for memory allocation (malloc)."""
        content = read_file(PRIMES_C)
        assert content is not None, f"{PRIMES_C} not found"
        assert "stdlib.h" in content, (
            "primes.c does not include <stdlib.h> — needed for malloc/memory allocation"
        )


# ===========================================================================
# Test Group 3: No Sidecar Files (Self-Containment)
# ===========================================================================

class TestNoSidecarFiles:
    """Verify that no separate .wasm or .js sidecar files exist."""

    def test_no_separate_wasm_file(self):
        """
        No separate primes.wasm file should exist.
        SINGLE_FILE=1 embeds the WASM binary inline.
        """
        assert not os.path.isfile(PRIMES_WASM), (
            f"{PRIMES_WASM} exists — the WASM binary should be embedded inline, "
            f"not as a separate file. Use -s SINGLE_FILE=1."
        )

    def test_no_separate_js_file(self):
        """
        No separate primes.js file should exist.
        The -o primes.html flag should produce inline JS within the HTML.
        """
        assert not os.path.isfile(PRIMES_JS), (
            f"{PRIMES_JS} exists — the JS glue code should be inline within "
            f"the HTML, not as a separate file."
        )

    def test_no_wasm_files_in_app_dir(self):
        """No .wasm files should exist anywhere in /app/."""
        if not os.path.isdir(APP_DIR):
            return  # If /app doesn't exist, other tests will catch it
        wasm_files = [
            f for f in os.listdir(APP_DIR)
            if f.endswith(".wasm")
        ]
        assert len(wasm_files) == 0, (
            f"Found .wasm sidecar file(s) in {APP_DIR}: {wasm_files}. "
            f"All WASM data must be embedded inline in the HTML."
        )


# ===========================================================================
# Test Group 4: HTML Structure and Content
# ===========================================================================

class TestHTMLStructure:
    """Validate the HTML file has proper structure."""

    def test_contains_html_tag(self):
        """primes.html must contain an <html> tag."""
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        assert re.search(r'<html', content, re.IGNORECASE), (
            "primes.html does not contain an <html> tag"
        )

    def test_contains_body_tag(self):
        """primes.html must contain a <body> tag."""
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        assert re.search(r'<body', content, re.IGNORECASE), (
            "primes.html does not contain a <body> tag"
        )

    def test_contains_script_tag(self):
        """primes.html must contain at least one <script> tag for JS glue code."""
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        assert re.search(r'<script', content, re.IGNORECASE), (
            "primes.html does not contain any <script> tags — "
            "JS glue code should be inline"
        )

    def test_no_external_wasm_reference(self):
        """
        primes.html must NOT reference an external .wasm file.
        Check for patterns like 'primes.wasm' or fetch('...wasm').
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        # Look for references to a separate .wasm file being loaded
        # SINGLE_FILE mode should NOT have these patterns
        has_wasm_fetch = bool(re.search(
            r"""(fetch|XMLHttpRequest|locateFile).*\.wasm['"\s\)]""",
            content
        ))
        # A data URI for wasm is fine (that's inline), but a bare filename is not
        has_bare_wasm_ref = bool(re.search(
            r"""['"]primes\.wasm['"]""",
            content
        ))
        assert not (has_wasm_fetch and has_bare_wasm_ref), (
            "primes.html appears to reference an external .wasm file. "
            "The WASM binary should be embedded inline via SINGLE_FILE=1."
        )

    def test_no_external_js_src(self):
        """
        primes.html must NOT use <script src="primes.js"> or similar
        to load JS from a separate file.
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        # Match <script src="primes.js"> or similar local JS file references
        # Allow CDN/external URLs but not local .js file references
        local_js_refs = re.findall(
            r'<script\s+[^>]*src\s*=\s*["\'](?!https?://)([\w./\-]+\.js)["\']',
            content,
            re.IGNORECASE
        )
        assert len(local_js_refs) == 0, (
            f"primes.html references external local JS file(s): {local_js_refs}. "
            f"All JS glue code must be inline."
        )


# ===========================================================================
# Test Group 5: Inline WebAssembly Data
# ===========================================================================

class TestInlineWASM:
    """Verify that WebAssembly binary data is embedded inline."""

    def test_contains_base64_data_uri(self):
        """
        Emscripten SINGLE_FILE mode embeds the WASM binary as a base64
        data URI. Check for the characteristic pattern.
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        # Emscripten typically uses data:application/octet-stream;base64,
        # or data:application/wasm;base64,
        has_octet_base64 = "data:application/octet-stream;base64," in content
        has_wasm_base64 = "data:application/wasm;base64," in content
        # Some versions may use a different but still base64 pattern
        has_generic_base64 = bool(re.search(r'base64,[A-Za-z0-9+/]{100,}', content))
        assert has_octet_base64 or has_wasm_base64 or has_generic_base64, (
            "primes.html does not contain base64-encoded WebAssembly data. "
            "Expected a data URI with base64-encoded WASM binary (SINGLE_FILE=1)."
        )

    def test_base64_data_is_substantial(self):
        """
        The base64-encoded WASM data should be non-trivial in size.
        Even a minimal C program compiles to several KB of WASM.
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        # Find the longest base64 chunk in the file
        base64_chunks = re.findall(r'base64,([A-Za-z0-9+/=]{10,})', content)
        if not base64_chunks:
            # If no base64 chunks found, this test is N/A (other test catches it)
            assert False, "No base64 data found in primes.html"
        longest = max(len(chunk) for chunk in base64_chunks)
        # A real compiled WASM binary is at least a few KB when base64-encoded
        # (even a trivial program produces ~1KB+ of WASM → ~1.3KB+ base64)
        assert longest > 500, (
            f"Largest base64 chunk is only {longest} chars — too small for "
            f"a real compiled WASM binary (expected >500 chars of base64 data)"
        )


# ===========================================================================
# Test Group 6: JavaScript Interop Indicators
# ===========================================================================

class TestJSInterop:
    """
    Verify that the HTML contains indicators of proper JS-WASM interop setup.
    These are patterns that Emscripten generates when functions are exported.
    """

    def test_contains_module_or_runtime(self):
        """
        Emscripten-generated HTML should contain references to the Module
        object or WebAssembly runtime setup.
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        has_module = "Module" in content
        has_webassembly = "WebAssembly" in content
        has_wasm_instantiate = "instantiate" in content.lower()
        assert has_module or has_webassembly or has_wasm_instantiate, (
            "primes.html does not contain Emscripten Module/WebAssembly references — "
            "the file may not be a genuine Emscripten build output"
        )

    def test_exported_function_reference(self):
        """
        The compiled HTML should contain a reference to the exported
        get_primes function (possibly as _get_primes in the symbol table).
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        has_get_primes = "get_primes" in content
        has_underscore_get_primes = "_get_primes" in content
        assert has_get_primes or has_underscore_get_primes, (
            "primes.html does not contain any reference to 'get_primes' — "
            "the function may not be properly exported from the WASM module"
        )

    def test_contains_ccall_or_cwrap(self):
        """
        If EXPORTED_RUNTIME_METHODS includes ccall/cwrap, the HTML should
        contain these identifiers for calling C functions from JS.
        """
        content = read_file(PRIMES_HTML)
        assert content is not None, f"{PRIMES_HTML} not found"
        has_ccall = "ccall" in content
        has_cwrap = "cwrap" in content
        has_getValue = "getValue" in content
        # At least one of these runtime methods should be present
        assert has_ccall or has_cwrap or has_getValue, (
            "primes.html does not contain ccall, cwrap, or getValue — "
            "exported runtime methods may not be configured correctly"
        )
