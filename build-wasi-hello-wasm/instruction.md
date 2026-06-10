## Build a Static, Cross-Platform WebAssembly Executable

Create a self-contained, statically-linked WebAssembly executable that prints "Hello, Wasm!" to standard output.

**Technical Requirements:**
- Language: Any language that compiles to WebAssembly (C, Rust, AssemblyScript, etc.)
- Target: WASI-compatible WebAssembly module
- Linking: Must be statically linked (no external dependencies)
- Output binary: `/app/hello.wasm`

**Output Specifications:**
- The executable must run successfully with: `wasmtime /app/hello.wasm`
- The executable must also run with: `node --experimental-wasi-unstable-preview1 -e "const{WASI}=require('wasi');const fs=require('fs');const wasi=new WASI();const importObject={wasi_snapshot_preview1:wasi.wasiImport};WebAssembly.instantiate(fs.readFileSync('/app/hello.wasm'),importObject).then(m=>{wasi.start(m.instance)})"`
- Expected output to stdout: `Hello, Wasm!\n` (with trailing newline)
- Exit code: 0

**Constraints:**
- The WebAssembly binary must be completely self-contained
- No dynamic library dependencies or external WASM modules
- Must use WASI for system interface (console output)
