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

# Set working directory
WORKDIR /app

# Create required directory structure
RUN mkdir -p /app/data /app/logs /app/.ssh

# Copy test data files into the source directory
COPY test_data/sample1.txt /app/data/sample1.txt
COPY test_data/sample2.csv /app/data/sample2.csv
COPY test_data/config.json /app/data/config.json
COPY test_data/notes.md /app/data/notes.md

# Copy the fake SSH key for testing
COPY ssh_backup_key /app/.ssh/backup_key
RUN chmod 600 /app/.ssh/backup_key
