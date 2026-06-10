FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    tmux asciinema \
    curl wget git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.13 and create OpenHands venv
ENV PATH="/root/.local/bin:$PATH"
RUN uv python install 3.13 && \
    mkdir -p /opt && \
    uv venv /opt/openhands-venv --python 3.13

# Install OpenHands
RUN . /opt/openhands-venv/bin/activate && \
    uv pip install openhands-ai

# Install nvm, Node.js 22 and Claude Code
ENV NVM_DIR="/root/.nvm"
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash && \
    . "$NVM_DIR/nvm.sh" && \
    nvm install 22 && \
    npm install -g @anthropic-ai/claude-code

ENV PATH="/root/.nvm/versions/node/v22.13.1/bin:$PATH"

# --- Task-specific setup: Break the system Python 3 environment ---

WORKDIR /app

# Ensure python3, python3-apt are installed before we break them
RUN apt-get update && apt-get install -y python3 python3-minimal python3-apt && \
    rm -rf /var/lib/apt/lists/*

# Simulate a junior admin accidentally removing critical Python 3 files:
# 1. Remove the python3 binary itself
# 2. Remove key parts of the standard library
# 3. Remove python3-apt module files
# 4. Corrupt dpkg state for python3-minimal to simulate partial removal
# 5. Keep apt sources and dpkg database intact so recovery is possible

RUN PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") && \
    echo "Breaking Python ${PYVER}..." && \
    # Remove the python3 main binary (but leave the versioned symlink target gone too)
    rm -f /usr/bin/python3 && \
    rm -f /usr/bin/python3.* && \
    # Remove parts of the standard library to make it non-functional
    rm -rf /usr/lib/python${PYVER}/json && \
    rm -rf /usr/lib/python${PYVER}/subprocess.py && \
    rm -rf /usr/lib/python${PYVER}/os.py && \
    # Remove python3-apt shared object
    rm -rf /usr/lib/python3/dist-packages/apt* && \
    # Mark python3-minimal as half-installed in dpkg to simulate botched removal
    sed -i '/^Package: python3-minimal$/,/^$/s/^Status: .*/Status: deinstall ok half-installed/' /var/lib/dpkg/status && \
    # Update apt lists so reinstallation is possible
    apt-get update
