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

# Install openssh-server and ufw for the SSH hardening task
RUN apt-get update && apt-get install -y \
    openssh-server ufw \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH host keys so sshd can start
RUN ssh-keygen -A

# Ensure the privilege separation directory exists
RUN mkdir -p /run/sshd

# Place the default sshd_config (Ubuntu-style defaults)
COPY sshd_config /etc/ssh/sshd_config

# Create working directory
RUN mkdir -p /app
WORKDIR /app
