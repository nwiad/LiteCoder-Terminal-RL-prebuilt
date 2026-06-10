## Build Static FFmpeg with VMAF Support from Source

Compile a statically-linked FFmpeg binary from source that includes Netflix's VMAF video quality metric filter, with all dependencies built from source and statically linked.

### Technical Requirements

- **Environment:** Ubuntu-based system (container or host)
- **Output binary:** `/app/ffmpeg` — a statically-linked FFmpeg executable
- **Build approach:** All libraries must be compiled from source with static linking (no shared/dynamic library dependencies for core functionality)

### Build Requirements

The following libraries must be built from source and statically linked into the FFmpeg binary:

1. **VMAF (libvmaf)** — Netflix's video quality metric library; FFmpeg must be built with `--enable-libvmaf`
2. **x264** — H.264 video encoder; FFmpeg must be built with `--enable-libx264`
3. **x265** — H.265/HEVC video encoder; FFmpeg must be built with `--enable-libx265`

Additional codec libraries (libvpx, aom, etc.) are optional.

### Verification Criteria

1. **Binary exists:** The file `/app/ffmpeg` must exist and be executable.

2. **Static linking:** The binary must be statically linked. Running `file /app/ffmpeg` must contain the string `statically linked`.

3. **VMAF filter available:** Running `/app/ffmpeg -filters 2>&1` must include `libvmaf` in the output, confirming the VMAF filter is compiled in.

4. **VMAF library enabled:** Running `/app/ffmpeg -buildconf 2>&1` must contain `--enable-libvmaf`.

5. **x264 encoder enabled:** Running `/app/ffmpeg -buildconf 2>&1` must contain `--enable-libx264`.

6. **x265 encoder enabled:** Running `/app/ffmpeg -buildconf 2>&1` must contain `--enable-libx265`.

7. **Basic functionality:** The binary must be able to execute a basic operation. Running `/app/ffmpeg -version` must exit with code 0 and include the string `ffmpeg version` in its output.

8. **Encoder availability:** Running `/app/ffmpeg -encoders 2>&1` must list both `libx264` and `libx265` encoders.

9. **VMAF scoring test:** The binary must be capable of performing a VMAF quality comparison. Generate two short synthetic test videos and run a VMAF filter between them:
   - Generate a 1-second reference video: `/app/ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=10 -c:v libx264 -y /app/ref.mp4`
   - Generate a 1-second distorted video: `/app/ffmpeg -f lavfi -i testsrc2=duration=1:size=320x240:rate=10 -c:v libx264 -y /app/dist.mp4`
   - Run VMAF comparison: `/app/ffmpeg -i /app/dist.mp4 -i /app/ref.mp4 -lavfi libvmaf -f null -` must exit with code 0.
