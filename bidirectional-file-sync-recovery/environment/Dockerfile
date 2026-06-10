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

# Install task-specific system packages: rsync, inotify-tools, logrotate, systemd
RUN apt-get update && apt-get install -y \
    rsync \
    inotify-tools \
    logrotate \
    systemd \
    systemd-sysv \
    && rm -rf /var/lib/apt/lists/*

# Create the sync directories with correct permissions
RUN mkdir -p /srv/project_a /srv/project_b && \
    chmod 755 /srv/project_a /srv/project_b

# Create log directory
RUN mkdir -p /var/log && touch /var/log/file_sync.log

# Copy seed test data into sync directories
COPY test_data/sample_a1.txt /srv/project_a/sample_a1.txt
COPY test_data/sample_a2.txt /srv/project_a/sample_a2.txt
COPY test_data/sample_b1.txt /srv/project_b/sample_b1.txt

WORKDIR /root
