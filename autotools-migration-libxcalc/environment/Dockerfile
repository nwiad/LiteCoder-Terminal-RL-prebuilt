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

# Install autotools build dependencies
RUN apt-get update && apt-get install -y \
    autoconf automake libtool pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy setup script and generate the legacy source tree
COPY setup.py /app/setup.py
RUN . /opt/openhands-venv/bin/activate && python3 /app/setup.py

# Verify the source tree was created
RUN test -f /app/libxcalc/src/libxcalc.c && \
    test -f /app/libxcalc/include/libxcalc/libxcalc.h && \
    test -f /app/libxcalc/Makefile && \
    test -f /app/libxcalc/tests/test_xcalc.c && \
    echo "Source tree verified successfully"
