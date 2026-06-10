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

# Copy sample project source files into the container
COPY cpp-project/CMakeLists.txt /app/cpp-project/CMakeLists.txt
COPY cpp-project/src/main.cpp /app/cpp-project/src/main.cpp
COPY java-project/pom.xml /app/java-project/pom.xml
COPY java-project/src/main/java/com/example/Main.java /app/java-project/src/main/java/com/example/Main.java
COPY python-project/requirements.txt /app/python-project/requirements.txt
COPY python-project/src/main.py /app/python-project/src/main.py
