# LiteCoder-Terminal OpenCode Prebuilt Image Pipeline Quality Audit

Audit date: 2026-06-09

Scope:

- Source dataset: `/Users/bytedance/CodeField/LiteCoder-Terminal`
- Derived dataset: `/Users/bytedance/CodeField/LiteCoder-Terminal-opencode`
- Tooling: `/Users/bytedance/CodeField/skill-master/docker/litecoder_terminal_opencode`

No Docker build, Docker push, or full smoke run was started during this audit.

## 1. Executive Summary

This pipeline is not cleared for a full 602-image build.

The generated derived dataset is internally consistent: all 602 tasks have `Dockerfile.prebuilt`, all 602 `task.toml` files parse as TOML and contain `docker_image`, the manifest covers exactly the same 602 tasks, and every generated `Dockerfile.prebuilt` matches the current generator output.

That is not enough. A strict COPY/ADD source check found 7 missing build-context sources across 3 manifest tasks. Those images will fail at Docker build time. The missing files are already absent in the source dataset, so this is a real dataset/build blocker, not just a derivation bug.

There are also serious operational risks:

- `build_images.sh` does not read `pushed_images.tsv` to skip already-pushed images. A naive resume rebuilds from the beginning unless `START` is manually set.
- The per-task image tag hash tracks only the source task Dockerfile. It does not track the base Dockerfile content, base image digest, generator version, unpinned OpenHands, or unpinned Claude Code.
- The base image installs Node/OpenCode under `/root/.nvm` and exposes symlinks in `/usr/local/bin`. Current tasks end as root, but this design is fragile for future non-root images.
- Docker/buildx state could not be inspected in this sandbox because Docker socket access was denied.

Final position: build base and a tiny `LIMIT=5` smoke is acceptable only as a smoke test. Do not start a full build or a long batch until the missing COPY sources are fixed or those tasks are intentionally excluded.

## 2. Blockers

### B1. Three manifest tasks have missing COPY sources and will fail to build

The generated `Dockerfile.prebuilt` files contain `COPY` instructions whose sources do not exist in the `environment/` build context used by `build_images.sh`.

Affected manifest indices:

| Index | Task | Missing source(s) |
|---:|---|---|
| 226 | `fix-cmake-arm-crosscompile` | `ci-build.log` |
| 318 | `k8s-control-plane-diagnosis` | `apiserver.log`, `etcd.log`, `kubelet.log`, `containerd.log`, `dmesg.log` |
| 543 | `shell-backup-rotation-system` | `test_data/sample_logs/` |

Evidence:

- `LiteCoder-Terminal-opencode/fix-cmake-arm-crosscompile/environment/Dockerfile.prebuilt` lines 16-23 copies `ci-build.log`, but the file is absent.
- `LiteCoder-Terminal-opencode/k8s-control-plane-diagnosis/environment/Dockerfile.prebuilt` lines 9-13 copy five log files, but only `apiserver-manifest.yaml` and `certificates.json` exist.
- `LiteCoder-Terminal-opencode/shell-backup-rotation-system/environment/Dockerfile.prebuilt` lines 12-15 copy `test_data/sample_source/` and `test_data/sample_logs/`; only `sample_source/` exists.

This is a hard build blocker. `docker buildx build` cannot satisfy these `COPY` instructions.

### B2. Docker/buildx local state and remote pullability were not verified

Read-only Docker checks failed in the sandbox:

- `docker version`: permission denied on `/Users/bytedance/.docker/run/docker.sock`
- `docker buildx inspect`: permission denied on the Docker API
- `docker system df`: permission denied on the Docker API

One retry with escalated permissions also timed out in the approval reviewer. Therefore this audit did not verify the active builder driver, builder cache pressure, local Docker disk usage, or whether the pushed images can be pulled by the target swalm/terminal sandbox nodes.

This does not prove the pipeline is broken, but it means there is no local Docker evidence in this audit.

## 3. High Risk

### H1. Resume is manual and easy to get wrong

`build_images.sh` appends successful pushes to `pushed_images.tsv`, but it never reads that file. If the script crashes after 200 images, running it again without `START=200` rebuilds already pushed images.

Current status log shows 5 pushed images and 597 remaining. A plain `LIMIT=5` run from index 0 would rebuild the first 5 instead of starting at the next unpushed image.

Recommended direction: add `SKIP_PUSHED=1` as the default behavior and skip any manifest image already present in `pushed_images.tsv`.

### H2. Image tags are not reproducible enough

Per-task tags are `opencode-1.15.4-<12-char-source-Dockerfile-hash>`. That hash is useful but incomplete.

It does not capture:

- `Dockerfile.base.opencode`
- base image digest
- `generate_prebuilt_dockerfiles.py`
- `check_common_prefix.py`
- unpinned `openhands-ai`
- unpinned `@anthropic-ai/claude-code`
- nvm install script content
- `uv` installer content

If the base image tag `hub.byted.org/dwn_open_docker/litecoder-terminal-base.opencode:1.15.4` is rebuilt with different content, the same task image tags can be overwritten with different final images.

### H3. `PUSH=0 LOAD=0` silently creates an unusable build mode

In `build_images.sh`, if `PUSH=0` and `LOAD=0`, `output_flag` is empty. `docker buildx build` then builds into BuildKit cache only. It does not push, does not load a local Docker image, and does not write a pushed log.

That mode should be rejected unless there is an explicit cache-only option.

### H4. Full build on an arm64 host targeting `linux/amd64` is high risk

`uname -m` returned `arm64`, while the scripts default to `PLATFORM=linux/amd64`.

Unless the active buildx builder is remote or a properly configured docker-container builder, Docker Desktop will likely run amd64 builds through emulation. For 602 images, that is slow and failure-prone. It also amplifies disk and cache pressure.

### H5. Global builder pruning is too blunt

`build_images.sh` runs:

```bash
docker builder prune -af
```

every `PRUNE_EVERY` builds by default. This can remove useful cache for later LiteCoder images and unrelated concurrent Docker work. It reduces disk pressure but increases rebuild time and makes failures harder to analyze.

### H6. Base image OpenCode runtime was not container-smoke-tested

Verified from npm metadata:

- `npm view opencode-ai@1.15.4 version` returned `1.15.4`
- `npm view opencode-ai@1.15.4 bin version` returned `bin = { opencode: 'bin/opencode.exe' }`

The Harbor OpenCode agent checks:

```bash
. ~/.nvm/nvm.sh 2>/dev/null && command -v node && command -v npm && command -v opencode && opencode --version
```

and later runs:

```bash
. ~/.nvm/nvm.sh; opencode run ...
```

The base Dockerfile is designed to satisfy that for root. However, no actual container run was performed, so `. ~/.nvm/nvm.sh && command -v opencode && opencode --version` remains unverified inside the built base image.

## 4. Medium/Low Risk

### M1. Extra apt packages are preserved, but not in the original transaction

The 10 outlier tasks have extra apt packages extracted from the first common apt block and reinstalled in a later task-specific `RUN`.

This preserves package presence for the current tasks, but it is not strictly byte-for-byte equivalent to the original apt transaction. Package install ordering can matter if a package has side effects or dependencies that affect later base setup.

### M2. Dockerfile parsing is intentionally narrow

`check_common_prefix.py` finds `COMMON_TAIL` by exact string search and parses the first apt block with a regex. It works on the current 602 Dockerfiles. It is not a general Dockerfile parser.

If the upstream dataset changes formatting, comments, apt flags, heredocs, shell forms, or common-tail versions, the checker will either fail hard or require manual updates.

### M3. `patch_task_toml` uses regex instead of a TOML writer

All current derived `task.toml` files parse successfully, and removing the inserted `docker_image` line exactly recovers the original source `task.toml`.

Still, the patcher is fragile for future TOML formatting:

- no `[environment]` section means silent no-op
- multiline or commented `docker_image` fields are not handled structurally
- insertion location is regex-based, not schema-based

### M4. `push_status.sh` does not model resolved failures

It counts unique images in `pushed_images.tsv` and unique images in `failed_images.tsv`. If an image failed once and later succeeded, it can appear in both counts. `remaining = total - pushed`, so remaining is still reasonable, but `failed_unique` can remain misleading after recovery.

### M5. Base image is root-centric

Current generated tasks end as root. Only `ecommerce-sales-analytics` switches to `USER postgres` and then back to `USER root`.

The base image still exposes OpenCode through symlinks into `/root/.nvm`. If a future task ends as non-root, `/usr/local/bin/opencode` may point into an inaccessible `/root` path. Installing Node/OpenCode under `/opt` or `/usr/local` would be safer.

### M6. `upload_local_dockerfile_context=false` is safe only if the prebuilt image is complete

`swalm-portal` requires `[environment].docker_image` and does not build local Dockerfiles. Its documentation says local `COPY`/`ADD` replay can be disabled with `upload_local_dockerfile_context=false`.

For this pipeline, disabling replay is the right direction because the prebuilt image should already contain Dockerfile `COPY` files. But this becomes unsafe if:

- a task image was accidentally built from the original Dockerfile instead of `Dockerfile.prebuilt`
- a prebuilt image build skipped or failed
- the task has missing COPY sources, as found above

## 5. Verified Facts

Commands run and outcomes:

```text
bash -n build_base_image.sh
bash -n build_images.sh
bash -n push_images.sh
bash -n push_status.sh
```

All passed with no output.

```text
python3 -m py_compile check_common_prefix.py generate_prebuilt_dockerfiles.py
```

Passed.

```text
python3 check_common_prefix.py --root /Users/bytedance/CodeField/LiteCoder-Terminal
```

Result:

```text
dockerfiles: 602
valid_common_prefix_shape: 602
exact_common_prefix: 592
prefix_with_extra_apt_packages: 10
```

The 10 outliers are:

```text
audio-genre-cnn-pytorch: libsndfile1 libsox-dev sox
cmake-c-math-library: cmake
cmake-calculator-build: cmake
containerize-legacy-php-lamp: make
custom-shared-lib-dlopen: cmake
fix-git-lfs-upload: git-lfs
gitflow-branching-audit-script: jq
nginx-websocket-reverse-proxy: nginx
rewrite-multiroot-git-history: jq
setup-git-ssh-auth: openssh-client
```

Derived dataset validation:

```text
source_dockerfiles=602
source_tasks=602
derived_task_tomls=602
derived_tasks=602
manifest_rows=602
manifest_unique_tasks=602
missing_prebuilt=0
missing_image=0
multi_image=0
bad_manifest_paths=0
nonexistent_manifest_paths=0
image_mismatch=0
invalid_image=0
generated_mismatch=0
task_toml_not_original_plus_docker_image=0
```

TOML parse validation:

```text
toml_parse_fail=0
missing_environment=0
missing_docker_image=0
```

COPY/ADD source validation:

```text
copy_add_total=462
copy_add_parse_fail=0
copy_add_remote_or_from_skipped=0
copy_add_missing_or_outside=7
```

Missing source sample was the full set:

```text
fix-cmake-arm-crosscompile COPY ci-build.log missing
k8s-control-plane-diagnosis COPY apiserver.log missing
k8s-control-plane-diagnosis COPY etcd.log missing
k8s-control-plane-diagnosis COPY kubelet.log missing
k8s-control-plane-diagnosis COPY containerd.log missing
k8s-control-plane-diagnosis COPY dmesg.log missing
shell-backup-rotation-system COPY test_data/sample_logs/ missing
```

Push status:

```text
total=602
pushed_unique=5
failed_unique=0
remaining=597
```

`pushed_images.tsv` contains successful records for indices 0 through 4:

```text
aes-cbc-padding-oracle
aes-cbc-pdf-decrypt
aes-cbc-png-stego-decrypt
aes-gcm-nonce-reuse-exploit
aes-known-plaintext-recovery
```

`failed_images.tsv` contains only the header.

Host and Docker:

```text
uname -m
arm64
```

Docker socket checks failed with permission denied, so builder driver and Docker disk usage were not verified.

Source git status:

```text
git -C LiteCoder-Terminal status --short
?? DOCKERFILE_ANALYSIS.md
```

No tracked source task modifications were reported by that command.

OpenCode npm metadata:

```text
npm view opencode-ai@1.15.4 version
1.15.4

npm view opencode-ai@1.15.4 bin version
bin = { opencode: 'bin/opencode.exe' }
version = '1.15.4'
```

## 6. Reproducibility/Recovery Plan

Before any full build:

1. Fix or intentionally exclude the three COPY-broken tasks at indices 226, 318, and 543.
2. Regenerate the derived dataset after source fixes.
3. Re-run the full validation checks in this report, especially COPY/ADD source validation.
4. Build and push the base image.
5. Run a base-image smoke test in a container:

```bash
docker run --rm --platform linux/amd64 \
  hub.byted.org/dwn_open_docker/litecoder-terminal-base.opencode:1.15.4 \
  bash -lc '. ~/.nvm/nvm.sh && command -v node && command -v npm && command -v opencode && opencode --version'
```

For task image builds:

1. Keep `pushed_images.tsv` and `failed_images.tsv`. They are the only current recovery record.
2. Use `push_status.sh` before each batch.
3. Because `build_images.sh` does not auto-skip pushed rows, resume with explicit `START`.
4. Build small batches first, for example `START=5 LIMIT=10`.
5. If a task fails and `CONTINUE_ON_ERROR=1` is used, inspect `failed_images.tsv`, fix the source, regenerate, and rebuild that exact index.
6. Do not use `PUSH=0 LOAD=0`.
7. Do not run full 602 on the default local builder until `docker buildx inspect` and `docker system df` are known good.

If the script crashes after a push but before logging, the remote registry may contain an image that `pushed_images.tsv` does not know about. The current tooling has no registry reconciliation step. Add a `docker manifest inspect` or registry API check if exact recovery matters.

## 7. Recommended Fixes

### Fix the data blockers

In the source dataset, then regenerate derived output:

- `LiteCoder-Terminal/fix-cmake-arm-crosscompile/environment`: add `ci-build.log` or remove the `COPY ci-build.log /app/ci-build.log` line if the task does not need it.
- `LiteCoder-Terminal/k8s-control-plane-diagnosis/environment`: add `apiserver.log`, `etcd.log`, `kubelet.log`, `containerd.log`, and `dmesg.log`, or remove those COPY lines and adjust the task.
- `LiteCoder-Terminal/shell-backup-rotation-system/environment`: add `test_data/sample_logs/` or remove the COPY line and adjust the task.

### Harden `build_images.sh`

Recommended changes:

- Reject `PUSH=0 LOAD=0` unless an explicit `CACHE_ONLY=1` is set.
- Add `SKIP_PUSHED=1` default behavior by reading `pushed_images.tsv`.
- Add an option to build from `SHOW_REMAINING` output or a filtered manifest.
- Write logs atomically through a temp file or at least flush after each row.
- Do not run global `docker builder prune -af` by default. Make it opt-in or use a scoped builder.

### Harden `push_status.sh`

Recommended changes:

- Report `failed_unresolved`, excluding images that later succeeded.
- Report duplicate pushed rows and duplicate failed rows.
- Verify manifest image uniqueness.

### Harden `Dockerfile.base.opencode`

Recommended changes:

- Install Node/OpenCode under `/opt/node` or `/usr/local`, not `/root/.nvm`, or ensure all relevant directories are executable by non-root users.
- Pin `openhands-ai` and `@anthropic-ai/claude-code`, or record their resolved versions.
- Add an explicit runtime verification command after build, not only during build.
- Consider tagging base images with a base Dockerfile hash or immutable digest.

### Harden `generate_prebuilt_dockerfiles.py`

Recommended changes:

- Validate all COPY/ADD sources during generation and fail before writing a manifest if any are missing.
- Use a TOML parser/writer instead of regex patching for `task.toml`.
- Include base image digest or base Dockerfile hash in the per-task tag or manifest.
- Add a safety guard so `--overwrite` cannot delete the source root or an unexpected parent directory.

### Harden `check_common_prefix.py`

Recommended changes:

- Keep the current exact-shape checker, but add a Dockerfile logical-instruction parser for validation.
- Compare the generated prebuilt suffix against the original suffix for every task as part of the standard workflow.

### Update README

Add explicit warnings:

- full build is blocked until COPY/ADD source validation passes
- first 5 images are already marked pushed in the current status log
- use `START=5 LIMIT=5` for the next smoke batch, not plain `LIMIT=5`, unless rebuilding the first five is intentional
- Docker socket/buildx inspection is required before long local batches

## 8. Final Recommendation

Do not run the full 602-image build now.

It is acceptable to run a small smoke test only after acknowledging it is not a full clearance. Since indices 0-4 are already logged as pushed, the next useful smoke batch would be:

```bash
START=5 LIMIT=5 PRUNE_EVERY=5 ./build_images.sh
```

Before any full or long build, fix the missing COPY source blockers, verify Docker/buildx with actual socket access, and add or manually enforce a resume plan that does not rebuild already-pushed images.
