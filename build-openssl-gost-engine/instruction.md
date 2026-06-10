Build OpenSSL 3.x from source with a custom GOST cryptographic engine, install it to a custom prefix, and create a validation tool to verify the engine's functionality.

## Technical Requirements

- **Language/Tools:** C, Bash, OpenSSL 3.x source, GOST engine
- **Working Directory:** /app
- **Custom Install Prefix:** /opt/openssl-3.x
- **Output Files:**
  - `/opt/openssl-3.x/bin/openssl` - Custom OpenSSL binary
  - `/opt/openssl-3.x/bin/validate_gost` - Validation program
  - `/opt/openssl-3.x/bin/openssl-gost` - Wrapper script
  - `/opt/openssl-3.x/lib64/engines-3/gost.so` or `/opt/openssl-3.x/lib/engines-3/gost.so` - GOST engine shared library
  - `/opt/openssl-3.x/README.md` - Documentation of directory layout
  - `/app/validation_output.txt` - Output from running validate_gost

## Implementation Requirements

1. **Build OpenSSL 3.x:**
   - Clone the official OpenSSL repository
   - Check out the latest stable 3.x tag
   - Configure with custom prefix `/opt/openssl-3.x` and enable dynamic engine loading
   - Compile and install without overwriting system OpenSSL

2. **Build and Install GOST Engine:**
   - Clone the gost-engine repository
   - Apply necessary patches for OpenSSL 3.x compatibility
   - Build and install the engine shared library to the OpenSSL prefix

3. **Configuration:**
   - Create OpenSSL configuration that loads the GOST engine
   - Ensure GOST algorithms are accessible via EVP interface

4. **Validation Program (validate_gost.c):**
   - Write a C program that uses OpenSSL EVP API
   - Must perform digest and/or signature operations using GOST algorithms
   - Must verify the engine is loaded and operational
   - Exit with code 0 on success, non-zero on failure
   - Install to `/opt/openssl-3.x/bin/validate_gost`

5. **Wrapper Script (openssl-gost):**
   - Create a bash script at `/opt/openssl-3.x/bin/openssl-gost`
   - Set appropriate environment variables (LD_LIBRARY_PATH, OPENSSL_CONF, etc.)
   - Execute the custom OpenSSL build transparently

6. **Verification Output:**
   - Run validate_gost and save output to `/app/validation_output.txt`
   - Output must confirm GOST engine is operational

7. **Documentation:**
   - Create `/opt/openssl-3.x/README.md` documenting the directory structure
   - Include paths to binaries, libraries, and configuration files

## Success Criteria

- `/opt/openssl-3.x/bin/openssl version` returns OpenSSL 3.x version string
- GOST engine shared library exists in engines directory
- validate_gost program executes successfully (exit code 0)
- System OpenSSL remains unaffected
- All required output files are present
