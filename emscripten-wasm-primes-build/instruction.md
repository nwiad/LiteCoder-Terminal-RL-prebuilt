## Static WebAssembly Build with Emscripten

Create a self-contained static HTML page that embeds a WebAssembly module compiled from C code using Emscripten. The C code computes the first N prime numbers. The final output must be a single HTML file with no external dependencies.

### Technical Requirements

- Language: C (compiled to WebAssembly via Emscripten)
- Emscripten SDK must be installed and functional
- All build artifacts and source files reside under `/app/`

### Source File

Create a C source file at `/app/primes.c` that:

- Implements a function `int* get_primes(int n)` that computes the first `n` prime numbers (where `n >= 0`)
- The function must be exported and callable from JavaScript via the Emscripten module
- When `n` is 0, the result should be an empty list (no primes returned)
- When `n` is 1, the result should be `[2]`
- Prime numbers must be returned in ascending order starting from 2

### Build

- Compile `/app/primes.c` using `emcc` to produce a self-contained HTML output
- The build must use Emscripten's single-file mode so that the WebAssembly binary is embedded inline (base64-encoded) within the output, rather than as a separate `.wasm` file
- The JavaScript glue code must also be inline within the HTML — no separate `.js` files
- The final build output must be a single file at `/app/primes.html`

### Output File: `/app/primes.html`

The generated HTML file must satisfy:

1. It is a valid HTML file (contains `<html>`, `<head>`, and `<body>` tags or equivalent Emscripten-generated structure)
2. It contains embedded base64-encoded WebAssembly data inline (no external `.wasm` file reference)
3. It contains inline JavaScript glue code (no external `.js` file reference via `<script src="...">` pointing to a local file)
4. The file is fully self-contained — opening it in a browser requires no other files or network access
5. The exported `get_primes` function is callable from the JavaScript environment within the page

### Verification Criteria

- `/app/primes.c` exists and contains the prime computation logic
- `/app/primes.html` exists and is a single self-contained HTML file
- `/app/primes.html` does NOT reference any external `.js` or `.wasm` files (i.e., no sidecar files required)
- The WebAssembly binary is embedded inline within `/app/primes.html`
- The prime computation is correct: first 10 primes are `[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`
