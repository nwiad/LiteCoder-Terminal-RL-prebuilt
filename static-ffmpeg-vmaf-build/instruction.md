## Build a Static FFmpeg with VMAF Support

Compile a fully static FFmpeg binary that includes Netflix's VMAF filter for video quality analysis, along with common codec libraries.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based)
- **Output binary:** `/app/ffmpeg_static/bin/ffmpeg`
- **Build prefix:** `/app/ffmpeg_static`
- **Source work directory:** `/app/ffmpeg_sources`

### Build Requirements

1. **VMAF library (libvmaf):** Build Netflix's VMAF library from source with static linking. The resulting FFmpeg must expose the `libvmaf` filter.

2. **Codec libraries:** Build the following from source with static linking:
   - **x264** — H.264 encoder (`--enable-libx264`)
   - **x265** — H.265/HEVC encoder (`--enable-libx265`)
   - **fdk-aac** — AAC audio encoder (`--enable-libfdk-aac`)

3. **FFmpeg configuration:** Configure FFmpeg with at minimum these flags:
   - `--enable-gpl`
   - `--enable-nonfree`
   - `--enable-static`
   - `--disable-shared`
   - `--enable-libvmaf`
   - `--enable-libx264`
   - `--enable-libx265`
   - `--enable-libfdk-aac`

### Verification Criteria

1. **Binary exists:** The file `/app/ffmpeg_static/bin/ffmpeg` must exist and be executable.

2. **Static linking:** Running `ldd /app/ffmpeg_static/bin/ffmpeg` must report `not a dynamic executable` or show only minimal system-level dependencies (libc, libm, libpthread, libdl, ld-linux). No references to libvmaf, libx264, libx265, or libfdk_aac shared libraries should appear.

3. **VMAF filter available:** Running `/app/ffmpeg_static/bin/ffmpeg -filters 2>&1` must include `libvmaf` in its output.

4. **Codec support:** Running `/app/ffmpeg_static/bin/ffmpeg -encoders 2>&1` must list:
   - `libx264`
   - `libx265`
   - `libfdk_aac`

5. **Version output:** Running `/app/ffmpeg_static/bin/ffmpeg -version` must execute successfully (exit code 0) and include the string `ffmpeg version` in its output.

6. **VMAF scoring test:** Generate two short synthetic test videos and compute a VMAF score:
   - Create a reference video: `/app/test_ref.mp4` (at least 1 second, any resolution)
   - Create a distorted video: `/app/test_dist.mp4` (same duration and resolution as reference, but with different quality/encoding)
   - Run VMAF comparison and write the result to `/app/vmaf_result.json` using FFmpeg's `libvmaf` filter with `log_fmt=json` and `log_path=/app/vmaf_result.json`
   - The JSON file must contain a `"VMAF score"` or `"vmaf"` metric with a numeric value between 0 and 100.
