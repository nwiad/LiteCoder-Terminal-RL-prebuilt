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

WORKDIR /app

# Configure git user for commits
RUN git config --global user.email "dev@example.com" && \
    git config --global user.name "Developer"

# Step 1: Initialize repo with initial project structure
RUN git init && \
    mkdir -p src && \
    echo "# main entry point" > src/main.py && \
    echo "# data-processor" > README.md && \
    git add . && \
    git commit -m "Initial project structure"

# Step 2: Add configuration files
RUN mkdir -p config && \
    printf '{\n  "database": "postgres",\n  "host": "localhost",\n  "port": 5432,\n  "debug": true\n}\n' > config/settings.json && \
    git add . && \
    git commit -m "Add configuration files"

# Step 3: Add large test fixture (1MB+ binary file)
RUN mkdir -p tests/fixtures && \
    dd if=/dev/urandom of=tests/fixtures/large_test_data.bin bs=1024 count=1100 2>/dev/null && \
    git add . && \
    git commit -m "Add large test fixtures"

# Step 4: Add processor module
RUN echo "# data processor module" > src/processor.py && \
    git add . && \
    git commit -m "Add processor module"

# Step 5: Simulate accidental rebase that drops the "Add configuration files" commit
# Use GIT_SEQUENCE_EDITOR to non-interactively remove the config commit line
RUN GIT_SEQUENCE_EDITOR="sed -i '/Add configuration files/d'" git rebase -i --root
