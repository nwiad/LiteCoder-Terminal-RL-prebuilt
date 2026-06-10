## Compile and Deploy a C++ WebSocket Server

Set up a C++ WebSocket server with SSL/TLS support, compile it, and configure it as a systemd service for production deployment.

### Technical Requirements

- **Language:** C++17 or later
- **OS:** Ubuntu (systemd-based)
- **Working directory:** /app

### Step-by-step Requirements

#### 1. Install Build Tools and Dependencies

Install the necessary packages for C++ WebSocket development with SSL support. At minimum, the following tools/libraries must be available after this step:

- A C++ compiler supporting C++17 (g++ or clang++)
- CMake (version 3.10+)
- OpenSSL development libraries
- A WebSocket library (e.g., libwebsocketpp-dev, libixwebsocket-dev, or Boost.Beast)

#### 2. Create the C++ WebSocket Server Source

Create the source file at `/app/ws_server.cpp`. The server must:

- Listen for WebSocket connections on port **9443** using SSL/TLS.
- Accept incoming connections and echo back any received text message prefixed with `Echo: `. For example, if a client sends `hello`, the server responds with `Echo: hello`.
- Gracefully handle client disconnections without crashing.
- Load SSL certificate and private key from `/app/certs/server.crt` and `/app/certs/server.key` respectively.
- Print `WebSocket server started on port 9443` to stdout when the server begins listening.

Also create a corresponding `/app/CMakeLists.txt` that builds the project. The CMake project name must be `ws_server`.

#### 3. Generate Self-Signed SSL/TLS Certificates

Generate a self-signed certificate and private key:

- Certificate file: `/app/certs/server.crt`
- Private key file: `/app/certs/server.key`
- Key type: RSA, 2048-bit minimum
- Validity: 365 days
- Subject Common Name (CN): `localhost`

Both files must be PEM-encoded.

#### 4. Compile the WebSocket Server

Build the server using CMake with an out-of-source build directory at `/app/build`. The final compiled binary must be located at `/app/build/ws_server`.

The binary must:
- Be a valid ELF executable
- Be dynamically linked against OpenSSL (libssl)

#### 5. Create a systemd Service File

Create a systemd service unit file at `/app/ws_server.service` with the following required directives:

- **[Unit]** section:
  - `Description` set to `WebSocket Server`
  - `After=network.target`

- **[Service]** section:
  - `ExecStart` pointing to `/app/build/ws_server`
  - `Restart=on-failure`
  - `RestartSec=5`
  - `WorkingDirectory=/app`

- **[Install]** section:
  - `WantedBy=multi-user.target`

#### 6. Generate Deployment Status Report

After completing all steps, create a JSON status report at `/app/deploy_status.json` with the following structure:

```json
{
  "binary_path": "/app/build/ws_server",
  "service_file": "/app/ws_server.service",
  "cert_path": "/app/certs/server.crt",
  "key_path": "/app/certs/server.key",
  "port": 9443,
  "ssl_enabled": true,
  "compiler_used": "<g++ or clang++>",
  "cpp_standard": "<17 or later>"
}
```

All string values must be actual paths/values (not placeholders). The `compiler_used` field should reflect the compiler actually used (e.g., `"g++"`). The `cpp_standard` field should be a string like `"17"` or `"20"`.

### Expected Output Files

| File | Description |
|---|---|
| `/app/ws_server.cpp` | WebSocket server source code |
| `/app/CMakeLists.txt` | CMake build configuration |
| `/app/certs/server.crt` | Self-signed SSL certificate (PEM) |
| `/app/certs/server.key` | RSA private key (PEM) |
| `/app/build/ws_server` | Compiled server binary (ELF executable) |
| `/app/ws_server.service` | systemd service unit file |
| `/app/deploy_status.json` | Deployment status report (JSON) |
