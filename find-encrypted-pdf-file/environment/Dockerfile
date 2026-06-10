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

# Install qpdf for PDF encryption
RUN apt-get update && apt-get install -y qpdf && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy decoy (non-encrypted) PDFs to various locations
COPY readme.pdf /home/readme.pdf
COPY test_data/report.pdf /var/log/report.pdf
COPY test_data/notes.pdf /tmp/notes.pdf

# Copy source PDF and encrypt it to a hidden location
COPY source_secret.pdf /tmp/source_secret.pdf
RUN mkdir -p /usr/local/share/.backup/2023/archives && \
    qpdf --encrypt secret123 secret123 256 -- /tmp/source_secret.pdf /usr/local/share/.backup/2023/archives/confidential.pdf && \
    rm /tmp/source_secret.pdf
