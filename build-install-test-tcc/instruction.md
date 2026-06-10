## Task: Build and Test Tiny C Compiler

Build the Tiny C Compiler (tcc) from source, install it system-wide, and verify it works by compiling and running a test program.

**Technical Requirements:**
- Operating System: Linux with apt package manager
- Required tools: gcc, make, libc-dev, wget
- TCC version: 0.9.27
- Installation prefix: /usr/local

**Implementation Steps:**

1. Install build dependencies (gcc, make, libc-dev, wget)

2. Download tcc 0.9.27 source tarball from official mirror:
   - URL: http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27.tar.bz2
   - Download location: /tmp/tcc-0.9.27.tar.bz2

3. Extract and build:
   - Extract tarball to /tmp
   - Run `./configure` with default settings
   - Run `make` to build
   - Run `make install` to install to /usr/local

4. Create test program at `/app/hello.c` with this exact content:
   ```c
   #include <stdio.h>
   int main() {
       printf("Hello from tcc!\n");
       return 0;
   }
   ```

5. Compile the test program:
   - Use tcc to compile `/app/hello.c`
   - Output binary: `/app/hello_tcc`

6. Verify installation:
   - tcc must be executable from PATH
   - `/app/hello_tcc` must run successfully and print "Hello from tcc!" to stdout
   - `/app/hello_tcc` must exit with code 0

**Output Requirements:**

Create `/app/result.json` with:
```json
{
  "tcc_version": "version string from tcc -v",
  "tcc_path": "full path to tcc binary",
  "test_program_compiled": true/false,
  "test_output": "actual output from running hello_tcc",
  "binary_size_bytes": <integer size of hello_tcc>
}
```
