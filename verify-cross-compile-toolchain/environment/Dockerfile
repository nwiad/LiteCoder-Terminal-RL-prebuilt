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

# Install task-specific tools: jq for JSON parsing, readelf/objdump from binutils,
# gcc-multilib for 32-bit compilation support
RUN apt-get update && apt-get install -y \
    jq binutils gcc-multilib \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the main targets.json input file
COPY targets.json /app/targets.json

# Copy additional test data
COPY test_data/ /app/test_data/

# Create the build output directory
RUN mkdir -p /app/build
