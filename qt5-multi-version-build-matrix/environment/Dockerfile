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

# ── Task-specific setup ──

# Install Qt5 build dependencies and tools
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libgl1-mesa-dev libglib2.0-dev libfontconfig1-dev libfreetype6-dev \
    libx11-dev libx11-xcb-dev libxext-dev libxfixes-dev libxi-dev \
    libxrender-dev libxcb1-dev libxcb-glx0-dev libxcb-keysyms1-dev \
    libxcb-image0-dev libxcb-shm0-dev libxcb-icccm4-dev \
    libxcb-sync-dev libxcb-xfixes0-dev libxcb-shape0-dev \
    libxcb-randr0-dev libxcb-render-util0-dev libxcb-xinerama0-dev \
    libxkbcommon-dev libxkbcommon-x11-dev \
    libdbus-1-dev libatspi2.0-dev \
    pkg-config file patchelf jq \
    && rm -rf /var/lib/apt/lists/*

# Install aqtinstall to fetch pre-built Qt binaries
RUN python3 -m venv /opt/aqt-venv && \
    /opt/aqt-venv/bin/pip install aqtinstall

# Download Qt 5.15.2 (well-supported in aqt archives)
RUN /opt/aqt-venv/bin/aqt install-qt linux desktop 5.15.2 gcc_64 \
    --outputdir /tmp/qt-install && \
    mv /tmp/qt-install/5.15.2/gcc_64 /opt/qt5-5.15.2 && \
    rm -rf /tmp/qt-install

# Download Qt 5.12.12 (available in aqt archives)
# Note: aqt may list this under slightly different archives
RUN /opt/aqt-venv/bin/aqt install-qt linux desktop 5.12.12 gcc_64 \
    --outputdir /tmp/qt-install && \
    mv /tmp/qt-install/5.12.12/gcc_64 /opt/qt5-5.12.12 && \
    rm -rf /tmp/qt-install

# For Qt 5.15.10 — this is a commercial/LTS patch release not in open archives.
# We create a copy of 5.15.2 as a stand-in at the expected path, then patch
# the version so the agent must handle it as a distinct prefix.
RUN cp -a /opt/qt5-5.15.2 /opt/qt5-5.15.10 && \
    find /opt/qt5-5.15.10 -name "*.prl" -exec sed -i 's/5\.15\.2/5.15.10/g' {} + && \
    find /opt/qt5-5.15.10 -name "*.pc" -exec sed -i 's/5\.15\.2/5.15.10/g' {} + && \
    find /opt/qt5-5.15.10 -name "*.la" -exec sed -i 's/5\.15\.2/5.15.10/g' {} + && \
    sed -i 's/5\.15\.2/5.15.10/g' /opt/qt5-5.15.10/mkspecs/qconfig.pri 2>/dev/null || true

# Ensure qmake is executable for all three installs
RUN chmod +x /opt/qt5-5.12.12/bin/qmake /opt/qt5-5.15.2/bin/qmake /opt/qt5-5.15.10/bin/qmake

# Set working directory
WORKDIR /app
