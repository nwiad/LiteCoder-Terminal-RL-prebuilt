## Build Static FFmpeg with All Features

Compile a fully-featured, statically-linked FFmpeg binary from source that supports all major audio/video codecs and formats, and place it at `/app/ffmpeg`.

### Requirements

1. **Static Binary**: The final `/app/ffmpeg` binary must be statically linked. Running `file /app/ffmpeg` should report it as "statically linked". It must not depend on any shared libraries (i.e., `ldd /app/ffmpeg` should report "not a dynamic executable" or similar).

2. **Required External Libraries**: FFmpeg must be compiled with the following libraries built from source and linked statically:
   - **x264** — H.264 video encoder (`--enable-libx264`)
   - **x265** — H.265/HEVC video encoder (`--enable-libx265`)
   - **libvpx** — VP8/VP9 video encoder/decoder (`--enable-libvpx`)
   - **libaom** — AV1 video encoder/decoder (`--enable-libaom`)
   - **fdk-aac** — AAC audio encoder (`--enable-libfdk-aac`)
   - **LAME (libmp3lame)** — MP3 audio encoder (`--enable-libmp3lame`)
   - **libopus** — Opus audio encoder/decoder (`--enable-libopus`)

3. **Encoder/Decoder Verification**: The binary must report support for the following when queried:
   - Encoders (via `/app/ffmpeg -encoders`): `libx264`, `libx265`, `libvpx_vp9`, `libaom_av1`, `libfdk_aac`, `libmp3lame`, `libopus`
   - Decoders (via `/app/ffmpeg -decoders`): `h264`, `hevc`, `vp9`, `av1`, `aac`, `mp3`, `opus`

4. **Functional Test**: The binary must be able to:
   - Report its version successfully (`/app/ffmpeg -version` exits with code 0).
   - Generate a synthetic test video: `/app/ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=10 -f lavfi -i sine=frequency=440:duration=1 -c:v libx264 -c:a aac -shortest /app/test_output.mp4` should produce a valid MP4 file at `/app/test_output.mp4` (file size > 0 bytes).

5. **Build Tools**: NASM and/or Yasm assemblers must be compiled from source as needed for assembly optimizations in the codec libraries.

6. **License**: FFmpeg must be configured with `--enable-gpl` and `--enable-nonfree` to allow all codec combinations.

### Output

- `/app/ffmpeg` — the final statically-linked FFmpeg binary.
