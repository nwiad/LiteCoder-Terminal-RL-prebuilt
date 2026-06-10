## Build Static FFmpeg with FDK-AAC Encoder from Source

Build a statically-linked, stripped FFmpeg binary from source with Fraunhofer FDK-AAC encoder support enabled, suitable for portable deployment on systems without a package manager.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based)
- **Output binary:** `/app/ffmpeg` — the final statically-linked FFmpeg executable
- **Output report:** `/app/build_report.json` — a JSON file documenting the build result

### Build Requirements

1. **FDK-AAC library:** Download the Fraunhofer FDK-AAC source, build it as a static library, and install it so FFmpeg can link against it.
2. **FFmpeg:** Download FFmpeg source and configure it with:
   - Static linking enabled (the final binary must be a statically-linked ELF executable)
   - FDK-AAC encoder enabled (requires `--enable-libfdk-aac` and `--enable-nonfree`)
3. **Strip** the final binary of debug symbols to minimize file size.
4. Copy or place the final binary at `/app/ffmpeg`.

### Verification Criteria

The resulting `/app/ffmpeg` binary must satisfy all of the following:

1. **Executable:** The file must be an executable ELF binary (not a script or symlink to a shared build).
2. **Statically linked:** `file /app/ffmpeg` must report "statically linked" (no dynamic library dependencies).
3. **FDK-AAC support:** Running `/app/ffmpeg -encoders 2>/dev/null` must list `libfdk_aac` as an available encoder.
4. **Stripped:** The binary must be stripped of debug symbols (i.e., `file /app/ffmpeg` should report "stripped").
5. **Functional:** Running `/app/ffmpeg -version` must exit with code 0 and print a version string.

### Build Report (`/app/build_report.json`)

After the build completes, generate a JSON file at `/app/build_report.json` with the following structure:

```json
{
  "ffmpeg_version": "<version string from ffmpeg -version, first line>",
  "is_static": true,
  "is_stripped": true,
  "has_libfdk_aac": true,
  "binary_size_bytes": <integer, size of /app/ffmpeg in bytes>,
  "binary_path": "/app/ffmpeg"
}
```

- `ffmpeg_version`: The first line of output from `/app/ffmpeg -version`.
- `is_static`: `true` if the binary is statically linked, `false` otherwise.
- `is_stripped`: `true` if the binary is stripped, `false` otherwise.
- `has_libfdk_aac`: `true` if `libfdk_aac` appears in the encoder list, `false` otherwise.
- `binary_size_bytes`: Integer file size in bytes of `/app/ffmpeg`.
- `binary_path`: Must be `"/app/ffmpeg"`.

All boolean fields must be `true` for a successful build.
