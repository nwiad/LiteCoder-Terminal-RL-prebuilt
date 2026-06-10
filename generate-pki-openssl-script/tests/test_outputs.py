"""
Tests for PKI Configuration Generator.
Validates all artifacts produced by /app/generate_pki.sh against instruction.md requirements.
"""
import os
import stat
import subprocess
import re
import pytest

PKI = "/app/pki"


def openssl(args: str) -> str:
    """Run an openssl command and return stdout."""
    r = subprocess.run(
        f"openssl {args}", shell=True, capture_output=True, text=True
    )
    return r.stdout + r.stderr, r.returncode


def cert_text(path: str) -> str:
    """Return the full text dump of a certificate."""
    out, rc = openssl(f"x509 -in {path} -noout -text")
    assert rc == 0, f"Failed to parse certificate {path}: {out}"
    return out


def key_bits(path: str) -> int:
    """Return the RSA key size in bits."""
    out, rc = openssl(f"rsa -in {path} -noout -text")
    assert rc == 0, f"Failed to parse key {path}: {out}"
    m = re.search(r"Private-Key:\s*\((\d+)\s*bit", out)
    assert m, f"Could not find key size in {path}"
    return int(m.group(1))


def cert_subject_cn(path: str) -> str:
    """Extract the CN from a certificate's subject."""
    out, rc = openssl(f"x509 -in {path} -noout -subject")
    assert rc == 0, f"Failed to read subject from {path}: {out}"
    # Handles both 'CN = Foo' and 'CN=Foo' formats
    m = re.search(r"CN\s*=\s*(.+?)(?:/|,|$)", out.strip())
    assert m, f"No CN found in subject of {path}: {out}"
    return m.group(1).strip()


def cert_issuer_cn(path: str) -> str:
    """Extract the CN from a certificate's issuer."""
    out, rc = openssl(f"x509 -in {path} -noout -issuer")
    assert rc == 0, f"Failed to read issuer from {path}: {out}"
    m = re.search(r"CN\s*=\s*(.+?)(?:/|,|$)", out.strip())
    assert m, f"No CN found in issuer of {path}: {out}"
    return m.group(1).strip()


def cert_validity_days(path: str) -> int:
    """Return approximate validity period in days."""
    out, rc = openssl(f"x509 -in {path} -noout -startdate -enddate")
    assert rc == 0, f"Failed to read dates from {path}: {out}"
    from datetime import datetime
    fmt1 = "%b %d %H:%M:%S %Y %Z"
    fmt2 = "%b  %d %H:%M:%S %Y %Z"
    start_m = re.search(r"notBefore=(.+)", out)
    end_m = re.search(r"notAfter=(.+)", out)
    assert start_m and end_m, f"Could not parse dates from {path}: {out}"
    start_str = start_m.group(1).strip()
    end_str = end_m.group(1).strip()
    for fmt in [fmt1, fmt2]:
        try:
            start = datetime.strptime(start_str, fmt)
            end = datetime.strptime(end_str, fmt)
            return (end - start).days
        except ValueError:
            continue
    pytest.fail(f"Could not parse date format from {path}: {start_str} / {end_str}")


def is_pem_file(path: str) -> bool:
    """Check if a file contains PEM-encoded data."""
    with open(path, "r") as f:
        content = f.read()
    return "-----BEGIN " in content and "-----END " in content


# ============================================================
# Test: generate_pki.sh exists and is executable
# ============================================================
class TestScriptEntryPoint:
    def test_generate_pki_sh_exists(self):
        assert os.path.isfile("/app/generate_pki.sh"), \
            "/app/generate_pki.sh does not exist"

    def test_generate_pki_sh_executable(self):
        st = os.stat("/app/generate_pki.sh")
        assert st.st_mode & stat.S_IXUSR, \
            "/app/generate_pki.sh is not executable by owner"


# ============================================================
# Test: All expected files exist
# ============================================================
class TestFileExistence:
    EXPECTED_FILES = [
        f"{PKI}/root-ca/root-ca.key",
        f"{PKI}/root-ca/root-ca.crt",
        f"{PKI}/intermediate-ca/intermediate-ca.key",
        f"{PKI}/intermediate-ca/intermediate-ca.csr",
        f"{PKI}/intermediate-ca/intermediate-ca.crt",
        f"{PKI}/server/server.key",
        f"{PKI}/server/server.csr",
        f"{PKI}/server/server.crt",
        f"{PKI}/client/client.key",
        f"{PKI}/client/client.csr",
        f"{PKI}/client/client.crt",
        f"{PKI}/crl/intermediate.crl",
        f"{PKI}/ca-chain.crt",
    ]

    @pytest.mark.parametrize("filepath", EXPECTED_FILES)
    def test_file_exists(self, filepath):
        assert os.path.isfile(filepath), f"Missing file: {filepath}"

    @pytest.mark.parametrize("filepath", EXPECTED_FILES)
    def test_file_not_empty(self, filepath):
        assert os.path.getsize(filepath) > 0, f"File is empty: {filepath}"


# ============================================================
# Test: PEM format for all certs and keys
# ============================================================
class TestPEMFormat:
    PEM_FILES = [
        f"{PKI}/root-ca/root-ca.key",
        f"{PKI}/root-ca/root-ca.crt",
        f"{PKI}/intermediate-ca/intermediate-ca.key",
        f"{PKI}/intermediate-ca/intermediate-ca.crt",
        f"{PKI}/server/server.key",
        f"{PKI}/server/server.crt",
        f"{PKI}/client/client.key",
        f"{PKI}/client/client.crt",
        f"{PKI}/ca-chain.crt",
    ]

    @pytest.mark.parametrize("filepath", PEM_FILES)
    def test_pem_format(self, filepath):
        if not os.path.isfile(filepath):
            pytest.skip(f"File missing: {filepath}")
        assert is_pem_file(filepath), f"Not PEM format: {filepath}"


# ============================================================
# Test: Root CA certificate
# ============================================================
class TestRootCA:
    CRT = f"{PKI}/root-ca/root-ca.crt"
    KEY = f"{PKI}/root-ca/root-ca.key"

    def test_root_ca_key_size(self):
        assert key_bits(self.KEY) == 4096, "Root CA key must be 4096 bits"

    def test_root_ca_cn(self):
        cn = cert_subject_cn(self.CRT)
        assert cn == "Root CA", f"Root CA CN must be 'Root CA', got '{cn}'"

    def test_root_ca_self_signed(self):
        subject_cn = cert_subject_cn(self.CRT)
        issuer_cn = cert_issuer_cn(self.CRT)
        assert subject_cn == issuer_cn, \
            f"Root CA must be self-signed: subject CN='{subject_cn}', issuer CN='{issuer_cn}'"

    def test_root_ca_is_ca(self):
        text = cert_text(self.CRT)
        assert "CA:TRUE" in text, "Root CA must have basicConstraints CA:TRUE"

    def test_root_ca_validity(self):
        days = cert_validity_days(self.CRT)
        # Allow ±10 day tolerance
        assert 3640 <= days <= 3660, \
            f"Root CA validity must be ~3650 days, got {days}"


# ============================================================
# Test: Intermediate CA certificate
# ============================================================
class TestIntermediateCA:
    CRT = f"{PKI}/intermediate-ca/intermediate-ca.crt"
    KEY = f"{PKI}/intermediate-ca/intermediate-ca.key"
    CSR = f"{PKI}/intermediate-ca/intermediate-ca.csr"

    def test_intermediate_ca_key_size(self):
        assert key_bits(self.KEY) == 4096, "Intermediate CA key must be 4096 bits"

    def test_intermediate_ca_cn(self):
        cn = cert_subject_cn(self.CRT)
        assert cn == "Intermediate CA", \
            f"Intermediate CA CN must be 'Intermediate CA', got '{cn}'"

    def test_intermediate_ca_signed_by_root(self):
        issuer_cn = cert_issuer_cn(self.CRT)
        assert issuer_cn == "Root CA", \
            f"Intermediate CA must be signed by Root CA, issuer CN='{issuer_cn}'"

    def test_intermediate_ca_is_ca(self):
        text = cert_text(self.CRT)
        assert "CA:TRUE" in text, \
            "Intermediate CA must have basicConstraints CA:TRUE"

    def test_intermediate_ca_validity(self):
        days = cert_validity_days(self.CRT)
        assert 1815 <= days <= 1835, \
            f"Intermediate CA validity must be ~1825 days, got {days}"

    def test_intermediate_csr_exists_and_parseable(self):
        out, rc = openssl(f"req -in {self.CSR} -noout -text")
        assert rc == 0, f"Intermediate CA CSR not parseable: {out}"


# ============================================================
# Test: Server certificate
# ============================================================
class TestServerCert:
    CRT = f"{PKI}/server/server.crt"
    KEY = f"{PKI}/server/server.key"
    CSR = f"{PKI}/server/server.csr"

    def test_server_key_size(self):
        bits = key_bits(self.KEY)
        assert bits >= 2048, f"Server key must be >= 2048 bits, got {bits}"

    def test_server_cn(self):
        cn = cert_subject_cn(self.CRT)
        assert cn == "server.example.com", \
            f"Server CN must be 'server.example.com', got '{cn}'"

    def test_server_signed_by_intermediate(self):
        issuer_cn = cert_issuer_cn(self.CRT)
        assert issuer_cn == "Intermediate CA", \
            f"Server cert must be signed by Intermediate CA, issuer CN='{issuer_cn}'"

    def test_server_eku_server_auth(self):
        text = cert_text(self.CRT)
        assert "TLS Web Server Authentication" in text, \
            "Server cert must include TLS Web Server Authentication in extendedKeyUsage"

    def test_server_not_ca(self):
        text = cert_text(self.CRT)
        # Server cert should NOT be a CA
        assert "CA:TRUE" not in text, \
            "Server cert must not have CA:TRUE"

    def test_server_validity(self):
        days = cert_validity_days(self.CRT)
        assert 355 <= days <= 375, \
            f"Server cert validity must be ~365 days, got {days}"

    def test_server_csr_parseable(self):
        out, rc = openssl(f"req -in {self.CSR} -noout -text")
        assert rc == 0, f"Server CSR not parseable: {out}"


# ============================================================
# Test: Client certificate
# ============================================================
class TestClientCert:
    CRT = f"{PKI}/client/client.crt"
    KEY = f"{PKI}/client/client.key"
    CSR = f"{PKI}/client/client.csr"

    def test_client_key_size(self):
        bits = key_bits(self.KEY)
        assert bits >= 2048, f"Client key must be >= 2048 bits, got {bits}"

    def test_client_cn(self):
        cn = cert_subject_cn(self.CRT)
        assert cn == "client.example.com", \
            f"Client CN must be 'client.example.com', got '{cn}'"

    def test_client_signed_by_intermediate(self):
        issuer_cn = cert_issuer_cn(self.CRT)
        assert issuer_cn == "Intermediate CA", \
            f"Client cert must be signed by Intermediate CA, issuer CN='{issuer_cn}'"

    def test_client_eku_client_auth(self):
        text = cert_text(self.CRT)
        assert "TLS Web Client Authentication" in text, \
            "Client cert must include TLS Web Client Authentication in extendedKeyUsage"

    def test_client_not_ca(self):
        text = cert_text(self.CRT)
        assert "CA:TRUE" not in text, \
            "Client cert must not have CA:TRUE"

    def test_client_validity(self):
        days = cert_validity_days(self.CRT)
        assert 355 <= days <= 375, \
            f"Client cert validity must be ~365 days, got {days}"

    def test_client_csr_parseable(self):
        out, rc = openssl(f"req -in {self.CSR} -noout -text")
        assert rc == 0, f"Client CSR not parseable: {out}"


# ============================================================
# Test: Certificate chain verification
# ============================================================
class TestChainVerification:
    CHAIN = f"{PKI}/ca-chain.crt"

    def test_chain_contains_intermediate_and_root(self):
        """ca-chain.crt must contain at least two PEM certificates."""
        if not os.path.isfile(self.CHAIN):
            pytest.fail("ca-chain.crt missing")
        with open(self.CHAIN, "r") as f:
            content = f.read()
        cert_count = content.count("-----BEGIN CERTIFICATE-----")
        assert cert_count >= 2, \
            f"ca-chain.crt must contain at least 2 certs, found {cert_count}"

    def test_chain_order_intermediate_then_root(self):
        """Intermediate CA cert must appear before Root CA cert in chain."""
        if not os.path.isfile(self.CHAIN):
            pytest.skip("ca-chain.crt missing")
        with open(self.CHAIN, "r") as f:
            content = f.read()
        # Split into individual PEM blocks
        blocks = re.findall(
            r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
            content, re.DOTALL
        )
        assert len(blocks) >= 2, "Need at least 2 certs in chain"
        # Write first cert to temp, check its CN
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(blocks[0])
            first_path = f.name
        try:
            first_cn = cert_subject_cn(first_path)
            assert first_cn == "Intermediate CA", \
                f"First cert in chain must be Intermediate CA, got '{first_cn}'"
        finally:
            os.unlink(first_path)

    def test_verify_server_cert_with_chain(self):
        """openssl verify server cert against ca-chain.crt must succeed."""
        out, rc = openssl(
            f"verify -CAfile {self.CHAIN} {PKI}/server/server.crt"
        )
        assert rc == 0 and "OK" in out, \
            f"Server cert verification failed: {out}"

    def test_verify_client_cert_with_chain(self):
        """openssl verify client cert against ca-chain.crt must succeed."""
        out, rc = openssl(
            f"verify -CAfile {self.CHAIN} {PKI}/client/client.crt"
        )
        assert rc == 0 and "OK" in out, \
            f"Client cert verification failed: {out}"


# ============================================================
# Test: CRL
# ============================================================
class TestCRL:
    CRL_PATH = f"{PKI}/crl/intermediate.crl"

    def test_crl_parseable(self):
        """CRL must be parseable by openssl crl."""
        out, rc = openssl(f"crl -in {self.CRL_PATH} -noout -text")
        assert rc == 0, f"CRL not parseable: {out}"

    def test_crl_issuer_matches_intermediate_ca(self):
        """CRL issuer must match the Intermediate CA subject."""
        out, rc = openssl(f"crl -in {self.CRL_PATH} -noout -issuer")
        assert rc == 0, f"Failed to read CRL issuer: {out}"
        m = re.search(r"CN\s*=\s*(.+?)(?:/|,|$)", out.strip())
        assert m, f"No CN in CRL issuer: {out}"
        issuer_cn = m.group(1).strip()
        assert issuer_cn == "Intermediate CA", \
            f"CRL issuer CN must be 'Intermediate CA', got '{issuer_cn}'"


# ============================================================
# Test: Private key permissions
# ============================================================
class TestKeyPermissions:
    KEY_FILES = [
        f"{PKI}/root-ca/root-ca.key",
        f"{PKI}/intermediate-ca/intermediate-ca.key",
        f"{PKI}/server/server.key",
        f"{PKI}/client/client.key",
    ]

    @pytest.mark.parametrize("keypath", KEY_FILES)
    def test_key_permission_no_more_than_0600(self, keypath):
        """All .key files must have permissions no more permissive than 0600."""
        if not os.path.isfile(keypath):
            pytest.skip(f"Key file missing: {keypath}")
        st = os.stat(keypath)
        mode = stat.S_IMODE(st.st_mode)
        # No group or other bits should be set; owner bits at most rw
        forbidden = stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | \
                    stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH
        assert (mode & forbidden) == 0, \
            f"{keypath} permissions {oct(mode)} are more permissive than 0600"


# ============================================================
# Test: Key-certificate correspondence
# ============================================================
class TestKeyCertMatch:
    PAIRS = [
        (f"{PKI}/root-ca/root-ca.key", f"{PKI}/root-ca/root-ca.crt"),
        (f"{PKI}/intermediate-ca/intermediate-ca.key", f"{PKI}/intermediate-ca/intermediate-ca.crt"),
        (f"{PKI}/server/server.key", f"{PKI}/server/server.crt"),
        (f"{PKI}/client/client.key", f"{PKI}/client/client.crt"),
    ]

    @pytest.mark.parametrize("key_path,crt_path", PAIRS)
    def test_key_matches_cert(self, key_path, crt_path):
        """Private key modulus must match certificate modulus."""
        if not os.path.isfile(key_path) or not os.path.isfile(crt_path):
            pytest.skip(f"Missing file: {key_path} or {crt_path}")
        key_out, rc1 = openssl(f"rsa -in {key_path} -noout -modulus")
        crt_out, rc2 = openssl(f"x509 -in {crt_path} -noout -modulus")
        assert rc1 == 0 and rc2 == 0, "Failed to extract modulus"
        key_mod = re.search(r"Modulus=([0-9A-Fa-f]+)", key_out)
        crt_mod = re.search(r"Modulus=([0-9A-Fa-f]+)", crt_out)
        assert key_mod and crt_mod, "Could not parse modulus"
        assert key_mod.group(1) == crt_mod.group(1), \
            f"Key and cert modulus mismatch for {key_path}"
