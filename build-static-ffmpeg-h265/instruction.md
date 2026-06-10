## Build an Optimized FFmpeg with H.265/HEVC Support

Build a statically-linked FFmpeg binary with H.265/HEVC encoding/decoding support via x265, and package it for deployment.

### Requirements

1. **Build x265 (libx265) as a static library**
   - Must include 10-bit encoding support.

2. **Build FFmpeg as a statically-linked binary**
   - Must link against the x265 static library built in step 1.
   - The resulting `ffmpeg` binary must be a statically-linked ELF executable (i.e., not dynamically linked to system libraries for its core functionality).
   - The `ffmpeg` binary must include the `libx265` encoder and the `hevc` decoder.

3. **Strip and optimize the binary**
   - The final `ffmpeg` binary must be stripped of debug symbols.

4. **Verify H.265 encode/decode functionality**
   - Generate a short test video (at least 1 second, any resolution ≥ 64x64) encoded in H.265/HEVC format and save it to `/app/test_h265.mp4`.
   - The file `/app/test_h265.mp4` must be a valid video file whose video stream codec is `hevc`.

5. **Package for deployment**
   - Create a gzip-compressed tarball at `/app/ffmpeg-static.tar.gz`.
   - The tarball must contain the stripped `ffmpeg` binary.

### Output Files

| File | Description |
|---|---|
| `/app/ffmpeg-static.tar.gz` | Gzip-compressed tarball containing the static `ffmpeg` binary |
| `/app/test_h265.mp4` | A short H.265/HEVC encoded test video |

### Verification Criteria

- The `ffmpeg` binary (extracted from the tarball) reports `--enable-libx265` in its configuration output (`ffmpeg -version`).
- `ffmpeg -encoders` lists `libx265`.
- `ffmpeg -decoders` lists `hevc`.
- The `ffmpeg` binary is a statically-linked ELF executable.
- `/app/test_h265.mp4` exists and its video stream codec is `hevc` (verifiable via `ffprobe`).
- The `ffmpeg` binary inside the tarball is stripped (no debug symbols).
