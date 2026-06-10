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

# Set up working directory
WORKDIR /app

# Create required directory structure
RUN mkdir -p /app/repo /app/output /home/admin /var/log

# Copy encrypted file and encryption metadata to /app/repo
COPY ssh_tunnel.conf.enc /app/repo/ssh_tunnel.conf.enc
COPY encryption_info.txt /app/repo/encryption_info.txt
COPY .env /app/repo/.env

# Copy passphrase fragment 1 into bash history
COPY .bash_history /home/admin/.bash_history

# Copy passphrase fragment 3 into syslog
COPY syslog.log /var/log/syslog.log
