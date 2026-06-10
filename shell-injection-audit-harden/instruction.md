## Defensive Security: Detecting and Defending Against Shell Injection Vulnerabilities

Audit a vulnerable SUID-root C wrapper, confirm it is exploitable via shell injection, then harden the source code so the vulnerability is eliminated while preserving the program's intended functionality.

### Environment Setup

- The vulnerable C source is located at `/tmp/vuln-wrapper.c`.
- A low-privileged user `ctf` exists on the system.
- A flag file exists at `/root/flag.txt` (readable only by root).
- A directory `/srv/secure/` contains files the wrapper is designed to let unprivileged users read.

### Requirements

**Step 1 — Build the vulnerable binary**

- Compile `/tmp/vuln-wrapper.c` into an executable at `/opt/reader`.
- Set ownership to `root:root` and permissions to `4755` (SUID-root).

**Step 2 — Exploit the vulnerability**

- As the unprivileged user `ctf`, craft a shell-injection payload against `/opt/reader` that exploits the `system()`/`sprintf()` injection point.
- Use the exploit to read the contents of `/root/flag.txt`.
- Write the exact flag content (trimmed of leading/trailing whitespace) to `/app/flag.txt`.

**Step 3 — Patch the source**

- Create a hardened version of the source at `/app/patched-wrapper.c` that eliminates the shell-injection vulnerability. The patched source must satisfy all of the following:
  - Must **not** call `system()` or `popen()` anywhere in the code.
  - Must **not** use `sprintf()` or `snprintf()` to build any shell command string.
  - Input filenames must be sanitized: reject any input containing shell metacharacters (at minimum: `;`, `|`, `&`, `` ` ``, `$`, `(`, `)`, `{`, `}`, `<`, `>`, `\n`).
  - The program must use safe alternatives (e.g., `execve`, direct file I/O via `open`/`read`/`write`, or similar) to perform its privileged file-reading operation.

**Step 4 — Build and install the hardened binary**

- Compile `/app/patched-wrapper.c` into `/opt/reader` (replacing the vulnerable version).
- Set ownership to `root:root` and permissions to `4755` (SUID-root).

**Step 5 — Verify hardened binary**

- Confirm that the previous exploit payload no longer succeeds (the injection must be blocked or neutralized).
- Confirm that the hardened `/opt/reader` can still correctly read a legitimate file inside `/srv/secure/` when invoked by user `ctf`. Write the content of any one successfully read file from `/srv/secure/` to `/app/legitimate-read-output.txt`.

### Output Files

| File | Description |
|---|---|
| `/app/flag.txt` | The flag obtained from `/root/flag.txt` via exploitation |
| `/app/patched-wrapper.c` | Hardened C source with injection vulnerability removed |
| `/app/legitimate-read-output.txt` | Content read from a file in `/srv/secure/` using the hardened binary |
