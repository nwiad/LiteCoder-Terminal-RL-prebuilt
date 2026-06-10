## Automated Systemd Service Builder

Build a shell-based build tool that takes a C source file and a JSON configuration, compiles the binary, generates a systemd service unit file, and produces an installation script. All components are orchestrated by a single entry point script.

### Technical Requirements

- Language: Bash (all scripts), C (sample application)
- Input: `/app/service_config.json` (service configuration), plus a C source file specified in the config
- Outputs:
  - `/app/build/` directory containing the compiled binary
  - `/app/build/<service_name>.service` — the generated systemd unit file
  - `/app/build/install.sh` — the generated installation script
- Entry point: `/app/build.sh` — the main build script that reads config, compiles, and generates all outputs

### Input Specification

`/app/service_config.json` has the following structure:

```json
{
  "service_name": "myapp",
  "description": "My custom daemon application",
  "source_file": "src/myapp.c",
  "user": "www-data",
  "restart_policy": "on-failure",
  "after": "network.target",
  "compile_flags": "-Wall -O2"
}
```

Field definitions:
- `service_name` (string, required): Name used for the binary, service file, and install paths.
- `description` (string, required): Description line in the systemd unit file.
- `source_file` (string, required): Relative path (from `/app/`) to the C source file to compile.
- `user` (string, optional, default `root`): The `User=` directive in the service file.
- `restart_policy` (string, optional, default `always`): The `Restart=` directive. Valid values: `no`, `always`, `on-success`, `on-failure`, `on-abnormal`, `on-watchdog`, `on-abort`.
- `after` (string, optional, default `network.target`): The `After=` directive.
- `compile_flags` (string, optional, default `-Wall`): Flags passed to `gcc`.

### Sample C Application

Create a minimal sample daemon at `/app/src/myapp.c` that:
- Runs an infinite loop (e.g., sleeps in a loop)
- Writes a startup message to syslog or stdout
- Handles SIGTERM for graceful shutdown

### build.sh Behavior

When executed (`bash /app/build.sh`):

1. Read and parse `/app/service_config.json`.
2. Create the `/app/build/` directory if it does not exist.
3. Compile the C source file specified in `source_file` using `gcc` with the flags from `compile_flags`. Output the binary to `/app/build/<service_name>`.
4. Generate the systemd service unit file at `/app/build/<service_name>.service`.
5. Generate the installation script at `/app/build/install.sh`.
6. Exit with code `0` on success, non-zero on any failure (e.g., missing config, compilation error).

### Systemd Service File Format

The generated `/app/build/<service_name>.service` must follow this exact structure:

```
[Unit]
Description=<description>
After=<after>

[Service]
Type=simple
ExecStart=/usr/local/bin/<service_name>
Restart=<restart_policy>
User=<user>

[Install]
WantedBy=multi-user.target
```

- All values are substituted from the JSON config (or defaults).
- The file must end with a trailing newline.

### Installation Script Format

The generated `/app/build/install.sh` must:
- Start with `#!/bin/bash`.
- Copy the compiled binary to `/usr/local/bin/<service_name>`.
- Copy the service file to `/etc/systemd/system/<service_name>.service`.
- Run `systemctl daemon-reload`.
- Run `systemctl enable <service_name>`.
- Run `systemctl start <service_name>`.
- Be executable (`chmod +x`).

### Error Handling

- If `/app/service_config.json` does not exist, `build.sh` must print an error message to stderr and exit with a non-zero code.
- If the C source file specified in `source_file` does not exist, `build.sh` must print an error message to stderr and exit with a non-zero code.
- If `gcc` compilation fails, `build.sh` must exit with a non-zero code.
