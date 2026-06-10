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

# Install BIND9, Apache2, iptables, and DNS utilities
RUN apt-get update && apt-get install -y \
    bind9 \
    bind9utils \
    bind9-dnsutils \
    apache2 \
    iptables \
    systemctl \
    && rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p /var/log/named && \
    chown bind:bind /var/log/named && \
    mkdir -p /var/www/company.com && \
    mkdir -p /var/www/portal.company.com && \
    mkdir -p /var/www/api.company.com && \
    mkdir -p /app

WORKDIR /app
