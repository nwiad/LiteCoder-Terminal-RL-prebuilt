# LiteCoder-Terminal Dockerfile Analysis

Generated on 2026-06-04.

## Executive Summary

`LiteCoder-Terminal` contains 602 valid Harbor terminal tasks, and every task has its own `environment/Dockerfile`. The Dockerfiles are highly standardized but not identical: all 602 start from `ubuntu:24.04`, while 450 unique Dockerfile contents exist across the dataset.

The dataset is easy to run with Harbor's local `docker` environment because Harbor can build each task from its local `environment/Dockerfile`. It is not directly runnable with the current `swalm-portal + opencode` path because `swalm-portal` requires `[environment].docker_image` to point to a prebuilt image, and none of the 602 `task.toml` files define `docker_image`.

The main operational cost is Docker build time and network dependency. Every Dockerfile downloads `uv`, installs Python 3.13, installs `openhands-ai`, installs Node.js 22 through `nvm`, and installs `@anthropic-ai/claude-code`. A full 602-task run therefore needs substantial image build caching or a prebuild/push workflow.

## Scope

Analyzed directory:

```text
/Users/bytedance/CodeField/LiteCoder-Terminal
```

Repository remote:

```text
https://huggingface.co/datasets/Lite-Coder/LiteCoder-Terminal-RL-preview
```

Harbor local task validation result:

- Valid Harbor task directories: 602
- `task.toml` files: 602
- `environment/Dockerfile` files: 602
- `solution/solve.sh` files: 602
- `tests/test.sh` files: 602

## Dataset Shape

Task metadata distribution:

| Field | Distribution |
| --- | --- |
| Difficulty | medium 342, hard 165, easy 95 |
| Category | system-administration 215, machine-learning 106, security 79, data-processing 74, software-engineering 64, version-control 48, build-tools 8, networking 7, build_tools 1 |
| CPU | 1 CPU: 285, 2 CPU: 293, 4 CPU: 24 |
| Memory | 2048 MB: 311, 4096 MB: 260, 8192 MB: 29, 3072 MB: 1, 16384 MB: 1 |
| Storage | 10240 MB: 474, 20480 MB: 115, 15360 MB: 11, 12288 MB: 1, 51200 MB: 1 |
| Build timeout | 600 sec: 586, 900 sec: 16 |
| Agent timeout | 1800-5400 sec |
| Verifier timeout | 360-900 sec |

There is a minor category normalization issue: both `build-tools` and `build_tools` appear.

## Dockerfile Structure

All Dockerfiles are single-container Dockerfile tasks:

- `FROM ubuntu:24.04`: 602 / 602
- `docker-compose.yaml`: 0
- `.dockerignore`: 0
- `[environment].docker_image` in `task.toml`: 0
- Unique Dockerfile contents by SHA-256: 450

Strict Dockerfile instruction counts after joining continuation lines:

| Instruction | Count |
| --- | ---: |
| `RUN` | 3417 |
| `ENV` | 1815 |
| `FROM` | 602 |
| `WORKDIR` | 605 |
| `COPY` | 462 |
| `CMD` | 3 |
| `USER` | 2 |
| `EXPOSE` | 2 |
| `ENTRYPOINT` | 1 |

Size and complexity:

| Metric | Min | Median | Mean | Max |
| --- | ---: | ---: | ---: | ---: |
| Dockerfile bytes | 823 | 960.5 | 1024.2 | 3006 |
| Dockerfile lines | 30 | 35 | 35.9 | 80 |
| `RUN` instructions per file | 5 | 5 | 5.7 | 12 |

Most tasks use `/app` as the working directory:

- `WORKDIR /app`: 583 Dockerfiles
- Other workdirs include `/root`, `/app/repo`, `/`, `/workspace`, `/home/user`, `/builds`, and several task-specific paths.

## Common Base Template

All 602 Dockerfiles contain the same core setup:

1. Start from `ubuntu:24.04`.
2. Install base apt packages: `tmux`, `asciinema`, `curl`, `wget`, `git`, `build-essential`.
3. Install `uv` from `https://astral.sh/uv/install.sh`.
4. Install Python 3.13 with `uv`.
5. Create `/opt/openhands-venv`.
6. Install `openhands-ai`.
7. Install `nvm` from GitHub.
8. Install Node.js 22.
9. Install `@anthropic-ai/claude-code`.

Representative example:

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    tmux asciinema \
    curl wget git build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"
RUN uv python install 3.13 && \
    mkdir -p /opt && \
    uv venv /opt/openhands-venv --python 3.13

RUN . /opt/openhands-venv/bin/activate && \
    uv pip install openhands-ai

ENV NVM_DIR="/root/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash && \
    . "$NVM_DIR/nvm.sh" && \
    nvm install 22 && \
    npm install -g @anthropic-ai/claude-code

ENV PATH="/root/.nvm/versions/node/v22.13.1/bin:$PATH"
WORKDIR /app
```

This common template is important because Docker layer caching can amortize much of the build cost when running with local Docker. It also means the images include OpenHands and Claude Code even when the actual evaluation agent is `opencode`.

## Task-Specific Additions

The Dockerfiles diverge mainly through local files and task-specific packages.

Local file context:

- Tasks with at least one `COPY`: 278
- Total `COPY` instructions: 462
- Common copied files/directories:
  - `input.json /app/input.json`: 38
  - `test_data/ /app/test_data/`: 31
  - `config.json /app/config.json`: 14
  - `setup_repo.sh /app/setup_repo.sh`: 11
  - `input.csv /app/input.csv`: 10
  - `setup.sh /app/setup.sh`: 9

Extra apt packages beyond the common base list appear in 123 tasks. Frequent examples:

| Package | Occurrences |
| --- | ---: |
| `gnupg` | 29 |
| `ca-certificates` | 24 |
| `lsb-release` | 24 |
| `docker-ce-cli` | 24 |
| `docker-compose-plugin` | 21 |
| `nginx` | 19 |
| `openssl` | 18 |
| `cmake` | 16 |
| `openssh-server` | 11 |
| `jq` | 11 |
| `docker-ce` | 11 |
| `containerd.io` | 11 |

Extra Python packages beyond `openhands-ai` appear in 21 tasks. Frequent examples:

| Package | Occurrences |
| --- | ---: |
| `matplotlib` | 7 |
| `torch` | 7 |
| `pandas` | 6 |
| `scikit-learn` | 6 |
| `torchvision` | 4 |
| `numpy` | 3 |
| `pycryptodome` | 3 |
| `pyarrow` | 2 |
| `seaborn` | 2 |
| `datasets` | 2 |

There were no npm packages beyond the common global `@anthropic-ai/claude-code` install.

## Build-Time Network Dependencies

Every Dockerfile requires internet during build:

- Ubuntu apt repositories.
- `https://astral.sh/uv/install.sh`.
- PyPI or the configured Python package index for `openhands-ai`.
- GitHub raw content for `nvm`.
- Node.js downloads via `nvm`.
- npm registry for `@anthropic-ai/claude-code`.

Additional external URLs appear in 36 tasks. Common examples:

| URL | Occurrences |
| --- | ---: |
| `https://download.docker.com/linux/ubuntu/gpg` | 24 |
| `https://download.docker.com/linux/ubuntu` | 24 |
| `https://download.pytorch.org/whl/cpu` | 5 |

Several one-off URLs download Go toolchains, Emscripten, LLVM sources, Consul, DVWA, or public datasets.

For China-network environments, the build process is likely to be the bottleneck unless apt, PyPI, npm, GitHub raw, and Docker Hub/Ubuntu image access are mirrored or cached.

## Harbor Local Docker Compatibility

The dataset is directly compatible with Harbor's local Docker backend.

Because every task has `environment/Dockerfile` and no `docker_image`, Harbor's Docker environment will build from the local Dockerfile. The relevant behavior in this workspace is:

- `--env docker` uses Docker Compose build mode.
- With no `[environment].docker_image`, Harbor cannot use a prebuilt image and builds the local `environment/` context.
- No `--force-build` is required for first use because there is no prebuilt image field.

Recommended smoke test:

```bash
cd /Users/bytedance/CodeField/skill-master/run_harbor

bash ./run_harbor.sh \
  --path /Users/bytedance/CodeField/LiteCoder-Terminal/aes-cbc-padding-oracle \
  --n-attempts 1 \
  --n-concurrent 1 \
  --env docker \
  --agent opencode \
  --agent-kwarg version=1.15.4
```

Recommended small batch:

```bash
cd /Users/bytedance/CodeField/skill-master/run_harbor

bash ./run_harbor.sh \
  --path /Users/bytedance/CodeField/LiteCoder-Terminal \
  --n-tasks 5 \
  --n-attempts 1 \
  --n-concurrent 1 \
  --env docker \
  --agent opencode \
  --agent-kwarg version=1.15.4
```

Operational notes:

- Start with low concurrency. Docker builds are network-heavy and will contend for CPU, disk, and package indexes.
- The common base layers should cache well after the first successful build.
- Full 602-task runs will still build many task-specific image variants because there are 450 unique Dockerfile contents.
- The configured task build timeout is usually 600 sec, with 16 tasks at 900 sec.

## swalm-portal + opencode Compatibility

The dataset is not directly compatible with the existing `swalm-portal + opencode` workflow.

Reason:

- `swalm-portal` requires `[environment].docker_image` to point to a prebuilt OCI image.
- This dataset has 0 `docker_image` entries.
- `swalm-portal` does not run local Docker builds.
- Its local Dockerfile support only replays `COPY`/`ADD` instructions into a started prebuilt container. It does not replay `RUN`, `apt`, `pip`, `npm`, `ENV`, or `WORKDIR` semantics as a Docker build.

Therefore, an `image_mapping_file` alone is not enough. Image mapping can rewrite an existing image name, but there is no image name to rewrite.

To use `swalm-portal`, add a prebuild step:

1. Build each task image from `task/environment/Dockerfile`.
2. Push the image to a registry accessible by the sandbox.
3. Inject the pushed image name into the task's `[environment].docker_image`.
4. Optionally use `image_mapping_file` to rewrite source image names to internal registry names.

Because there are 450 unique Dockerfile contents, the minimum build set is likely 450 images if grouped by Dockerfile hash. However, grouping by Dockerfile hash must be done carefully: a Dockerfile with the same text can still depend on different build-context files if `COPY` sources differ by task directory. The safest strategy is one image per task.

## Practical Assessment

For local Docker, usage is straightforward enough for a smoke test and small batches. The main friction is build time, not format compatibility.

For `swalm-portal + opencode`, usage is not simple out of the box. The missing `docker_image` field means the dataset needs a conversion/prebuild pipeline before it can run in that environment.

Recommended path:

1. Use local Docker first to verify task correctness and runner compatibility.
2. Run 1 task, then 5 tasks, then one category subset.
3. If `swalm-portal` is required, implement a prebuild pipeline and patch generated task copies rather than editing the upstream clone in place.
4. Cache or mirror package sources before attempting a full 602-task build.

## Suggested Prebuild Shape for swalm-portal

A minimal prebuild workflow should produce a derived dataset directory, for example:

```text
/Users/bytedance/CodeField/LiteCoder-Terminal-swalm
```

For each task:

```bash
docker build \
  -t <registry>/litecoder-terminal/<task-name>:<hash> \
  /Users/bytedance/CodeField/LiteCoder-Terminal/<task-name>/environment
docker push <registry>/litecoder-terminal/<task-name>:<hash>
```

Then patch the copied `task.toml`:

```toml
[environment]
docker_image = "<registry>/litecoder-terminal/<task-name>:<hash>"
```

After that, the existing `swalm-portal + opencode` command pattern can work:

```bash
bash ./run_harbor.sh \
  --path /Users/bytedance/CodeField/LiteCoder-Terminal-swalm/<task-name> \
  --env swalm-portal \
  --environment-kwarg enable_terminal_sandbox=true \
  --environment-kwarg image_mapping_file=/path/to/image_map.tsv \
  --environment-kwarg upload_local_dockerfile_context=true \
  --agent opencode \
  --agent-kwarg version=1.15.4
```

If the image is already fully built with the task context, `upload_local_dockerfile_context=true` may be redundant. It is only useful when Dockerfile `COPY`/`ADD` sources must be overlaid after sandbox startup.
