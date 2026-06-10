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

# Install LAMP stack components
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    apache2 \
    mariadb-server \
    php libapache2-mod-php php-mysql \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy web application files to Apache document root
COPY index.php /var/www/html/index.php
COPY config.php /var/www/html/config.php

# Copy database initialization script
COPY init_db.sql /docker-entrypoint-initdb.d/init_db.sql

# Create backup directory structure with correct permissions
RUN mkdir -p /backup/files /backup/database /backup/logs && \
    chmod -R 750 /backup

# Initialize MariaDB and load sample data
RUN service mariadb start && \
    mysql < /docker-entrypoint-initdb.d/init_db.sql && \
    service mariadb stop

# Set working directory
WORKDIR /app
