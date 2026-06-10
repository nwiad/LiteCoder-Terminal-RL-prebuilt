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

# Install OpenSSH and jq for SSH key operations and JSON parsing
RUN apt-get update && apt-get install -y \
    openssh-client \
    openssh-server \
    jq \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy input configuration
COPY input.json /app/input.json

# Create the user accounts specified in input.json
RUN useradd -m -s /bin/bash alice && \
    useradd -m -s /bin/bash bob && \
    useradd -m -s /bin/bash charlie

# Create .ssh directories with correct permissions for each user
RUN mkdir -p /home/alice/.ssh && chmod 700 /home/alice/.ssh && chown alice:alice /home/alice/.ssh && \
    mkdir -p /home/bob/.ssh && chmod 700 /home/bob/.ssh && chown bob:bob /home/bob/.ssh && \
    mkdir -p /home/charlie/.ssh && chmod 700 /home/charlie/.ssh && chown charlie:charlie /home/charlie/.ssh

# Generate initial SSH key pairs for each user
RUN ssh-keygen -t ed25519 -f /home/alice/.ssh/id_ed25519 -N "" -q && \
    cp /home/alice/.ssh/id_ed25519.pub /home/alice/.ssh/authorized_keys && \
    chmod 600 /home/alice/.ssh/id_ed25519 /home/alice/.ssh/authorized_keys && \
    chmod 644 /home/alice/.ssh/id_ed25519.pub && \
    chown -R alice:alice /home/alice/.ssh

RUN ssh-keygen -t ed25519 -f /home/bob/.ssh/id_ed25519 -N "" -q && \
    cp /home/bob/.ssh/id_ed25519.pub /home/bob/.ssh/authorized_keys && \
    chmod 600 /home/bob/.ssh/id_ed25519 /home/bob/.ssh/authorized_keys && \
    chmod 644 /home/bob/.ssh/id_ed25519.pub && \
    chown -R bob:bob /home/bob/.ssh

RUN ssh-keygen -t ed25519 -f /home/charlie/.ssh/id_ed25519 -N "" -q && \
    cp /home/charlie/.ssh/id_ed25519.pub /home/charlie/.ssh/authorized_keys && \
    chmod 600 /home/charlie/.ssh/id_ed25519 /home/charlie/.ssh/authorized_keys && \
    chmod 644 /home/charlie/.ssh/id_ed25519.pub && \
    chown -R charlie:charlie /home/charlie/.ssh

# Create backup directory
RUN mkdir -p /app/backups
