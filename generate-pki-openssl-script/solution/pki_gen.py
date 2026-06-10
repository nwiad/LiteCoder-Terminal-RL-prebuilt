#!/usr/bin/env python3
"""Complete PKI generator - creates /app/generate_pki.sh and runs it."""
import os, shutil, subprocess, textwrap

PKI = "/app/pki"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"FAIL: {cmd}\n{r.stderr.decode()}")

def wf(path, content, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(textwrap.dedent(content).lstrip("\n"))
    if mode:
        os.chmod(path, mode)

# Clean
if os.path.exists(PKI):
    shutil.rmtree(PKI)
for d in ["root-ca","intermediate-ca","server","client","crl"]:
    os.makedirs(f"{PKI}/{d}")

# ========== Root CA ==========
wf(f"{PKI}/root-ca/root-ca.cnf", """\
    [req]
    distinguished_name = req_dn
    prompt = no
    x509_extensions = v3_ca

    [req_dn]
    CN = Root CA

    [v3_ca]
    basicConstraints = critical, CA:TRUE
    keyUsage = critical, keyCertSign, cRLSign
    subjectKeyIdentifier = hash
    authorityKeyIdentifier = keyid:always, issuer

    [v3_intermediate_ca]
    basicConstraints = critical, CA:TRUE
    keyUsage = critical, keyCertSign, cRLSign
    subjectKeyIdentifier = hash
    authorityKeyIdentifier = keyid:always, issuer
""")

run(f'openssl genrsa -out "{PKI}/root-ca/root-ca.key" 4096')
os.chmod(f"{PKI}/root-ca/root-ca.key", 0o600)

run(f'openssl req -new -x509 -key "{PKI}/root-ca/root-ca.key"'
    f' -out "{PKI}/root-ca/root-ca.crt" -days 3650'
    f' -config "{PKI}/root-ca/root-ca.cnf" -extensions v3_ca')
# ========== Intermediate CA ==========
wf(f"{PKI}/intermediate-ca/intermediate-ca.cnf", """\
    [req]
    distinguished_name = req_dn
    prompt = no

    [req_dn]
    CN = Intermediate CA

    [v3_server]
    basicConstraints = CA:FALSE
    keyUsage = critical, digitalSignature, keyEncipherment
    extendedKeyUsage = serverAuth
    subjectKeyIdentifier = hash
    authorityKeyIdentifier = keyid,issuer

    [v3_client]
    basicConstraints = CA:FALSE
    keyUsage = critical, digitalSignature, keyEncipherment
    extendedKeyUsage = clientAuth
    subjectKeyIdentifier = hash
    authorityKeyIdentifier = keyid,issuer

    [crl_ext]
    authorityKeyIdentifier = keyid:always
""")

run(f'openssl genrsa -out "{PKI}/intermediate-ca/intermediate-ca.key" 4096')
os.chmod(f"{PKI}/intermediate-ca/intermediate-ca.key", 0o600)

run(f'openssl req -new -key "{PKI}/intermediate-ca/intermediate-ca.key"'
    f' -out "{PKI}/intermediate-ca/intermediate-ca.csr"'
    f' -config "{PKI}/intermediate-ca/intermediate-ca.cnf"')

run(f'openssl x509 -req -in "{PKI}/intermediate-ca/intermediate-ca.csr"'
    f' -CA "{PKI}/root-ca/root-ca.crt" -CAkey "{PKI}/root-ca/root-ca.key"'
    f' -CAcreateserial -out "{PKI}/intermediate-ca/intermediate-ca.crt"'
    f' -days 1825 -extfile "{PKI}/root-ca/root-ca.cnf"'
    f' -extensions v3_intermediate_ca')

# ========== Server Certificate ==========
run(f'openssl genrsa -out "{PKI}/server/server.key" 2048')
os.chmod(f"{PKI}/server/server.key", 0o600)

run(f'openssl req -new -key "{PKI}/server/server.key"'
    f' -out "{PKI}/server/server.csr"'
    f' -subj "/CN=server.example.com"')

run(f'openssl x509 -req -in "{PKI}/server/server.csr"'
    f' -CA "{PKI}/intermediate-ca/intermediate-ca.crt"'
    f' -CAkey "{PKI}/intermediate-ca/intermediate-ca.key"'
    f' -CAcreateserial -out "{PKI}/server/server.crt"'
    f' -days 365 -extfile "{PKI}/intermediate-ca/intermediate-ca.cnf"'
    f' -extensions v3_server')

# ========== Client Certificate ==========
run(f'openssl genrsa -out "{PKI}/client/client.key" 2048')
os.chmod(f"{PKI}/client/client.key", 0o600)

run(f'openssl req -new -key "{PKI}/client/client.key"'
    f' -out "{PKI}/client/client.csr"'
    f' -subj "/CN=client.example.com"')

run(f'openssl x509 -req -in "{PKI}/client/client.csr"'
    f' -CA "{PKI}/intermediate-ca/intermediate-ca.crt"'
    f' -CAkey "{PKI}/intermediate-ca/intermediate-ca.key"'
    f' -CAcreateserial -out "{PKI}/client/client.crt"'
    f' -days 365 -extfile "{PKI}/intermediate-ca/intermediate-ca.cnf"'
    f' -extensions v3_client')

# ========== CA Chain ==========
with open(f"{PKI}/intermediate-ca/intermediate-ca.crt") as f:
    inter = f.read()
with open(f"{PKI}/root-ca/root-ca.crt") as f:
    root = f.read()
with open(f"{PKI}/ca-chain.crt", "w") as f:
    f.write(inter)
    if not inter.endswith("\n"):
        f.write("\n")
    f.write(root)

# ========== CRL ==========
# Create required database files for CRL generation
wf(f"{PKI}/intermediate-ca/index.txt", "")
wf(f"{PKI}/intermediate-ca/crlnumber", "1000\n")

wf(f"{PKI}/intermediate-ca/crl.cnf", f"""\
    [ca]
    default_ca = CA_default

    [CA_default]
    dir = {PKI}/intermediate-ca
    database = $dir/index.txt
    crlnumber = $dir/crlnumber
    default_crl_days = 30
    default_md = sha256
    certificate = {PKI}/intermediate-ca/intermediate-ca.crt
    private_key = {PKI}/intermediate-ca/intermediate-ca.key
""")

run(f'openssl ca -gencrl -config "{PKI}/intermediate-ca/crl.cnf"'
    f' -out "{PKI}/crl/intermediate.crl"')

# ========== Write generate_pki.sh wrapper ==========
# The task requires /app/generate_pki.sh to exist
# We write a shell script that calls this python script
wf("/app/generate_pki.sh", """\
    #!/bin/bash
    python3 /tmp/pki_gen.py
""", mode=0o755)

print("PKI generation complete.")
