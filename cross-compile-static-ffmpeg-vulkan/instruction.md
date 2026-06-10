## Cross-Compile Static FFmpeg with Vulkan Support

Build a statically-linked FFmpeg binary for x86_64 Linux with Vulkan video filter support. The entire build process must be performed inside a Docker container based on Ubuntu (20.04 or later) to ensure reproducibility.

### Technical Requirements

- **Base environment:** Ubuntu Docker container (20.04+)
- **Target architecture:** x86_64 Linux
- **Linking:** Fully static (no dynamic library dependencies beyond the Linux kernel interface)
- **Vulkan support:** FFmpeg must be built with `--enable-vulkan` and include Vulkan-based video filters

### Build Steps

1. Create and use a Docker container from an official Ubuntu base image (20.04 or later).
2. Inside the container, install all necessary build tools and cross-compilation dependencies.
3. Build the Vulkan SDK/loader as a static library.
4. Build any required FFmpeg codec/format dependencies as static libraries (e.g., x264, x265, fdk-aac, opus, etc.). At minimum, include x264 and x265.
5. Download the FFmpeg source, configure it with static linking and Vulkan filter support enabled, and compile.
6. Strip debug symbols from the final binary.

### Output Requirements

1. **FFmpeg binary:** Place the final stripped, statically-linked FFmpeg binary at `/app/ffmpeg`.

2. **Build report:** Write a JSON file to `/app/build_report.json` with the following structure:

```json
{
  "ffmpeg_version": "<version string from ffmpeg -version, first line>",
  "binary_path": "/app/ffmpeg",
  "binary_size_bytes": <integer, file size in bytes>,
  "binary_md5": "<md5 hex digest of the binary>",
  "docker_image": "<name:tag of the Ubuntu base image used>",
  "static_linked": true,
  "vulkan_filters": ["<list of Vulkan filter names reported by ffmpeg -filters>"],
  "enabled_encoders": ["<list of encoder names from ffmpeg -encoders that are available>"],
  "enabled_decoders": ["<list of decoder names from ffmpeg -decoders that are available>"]
}
```

### Verification Criteria

- `/app/ffmpeg` must be a valid ELF x86_64 executable.
- Running `file /app/ffmpeg` must indicate "statically linked".
- Running `ldd /app/ffmpeg` must report "not a dynamic executable" (or equivalent).
- Running `/app/ffmpeg -version` must exit with code 0 and print a version string.
- Running `/app/ffmpeg -filters` must list at least one filter containing the substring `vulkan` (case-insensitive).
- `/app/build_report.json` must be valid JSON conforming to the structure above.
- `build_report.json` field `static_linked` must be `true`.
- `build_report.json` field `vulkan_filters` must be a non-empty array.
- `build_report.json` field `binary_md5` must match the actual MD5 of `/app/ffmpeg`.
- The binary size (`binary_size_bytes`) must match the actual file size of `/app/ffmpeg`.
