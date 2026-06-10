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

# Task-specific setup
WORKDIR /app

# Install nginx, certbot, fail2ban, ufw and dependencies for DVWA
RUN apt-get update && apt-get install -y \
    nginx-full \
    certbot \
    python3-certbot-nginx \
    fail2ban \
    ufw \
    apache2 \
    php \
    php-mysqli \
    php-gd \
    mariadb-server \
    && rm -rf /var/lib/apt/lists/*

# Download and setup DVWA
RUN cd /var/www/html && \
    git clone https://github.com/digininja/DVWA.git dvwa && \
    chown -R www-data:www-data /var/www/html/dvwa

# Configure Apache to run on port 8080
RUN sed -i 's/Listen 80/Listen 8080/' /etc/apache2/ports.conf && \
    sed -i 's/:80/:8080/' /etc/apache2/sites-available/000-default.conf && \
    echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Create Apache site config for DVWA
RUN echo '<VirtualHost *:8080>\n\
    ServerAdmin webmaster@localhost\n\
    DocumentRoot /var/www/html/dvwa\n\
    <Directory /var/www/html/dvwa>\n\
        Options Indexes FollowSymLinks\n\
        AllowOverride All\n\
        Require all granted\n\
    </Directory>\n\
    ErrorLog ${APACHE_LOG_DIR}/error.log\n\
    CustomLog ${APACHE_LOG_DIR}/access.log combined\n\
</VirtualHost>' > /etc/apache2/sites-available/dvwa.conf && \
    a2dissite 000-default && \
    a2ensite dvwa

# Configure DVWA
RUN cp /var/www/html/dvwa/config/config.inc.php.dist /var/www/html/dvwa/config/config.inc.php && \
    sed -i "s/p@ssw0rd/password/" /var/www/html/dvwa/config/config.inc.php && \
    sed -i "s/'impossible'/'low'/" /var/www/html/dvwa/config/config.inc.php

# Expose ports
EXPOSE 80 443 8080

CMD ["/bin/bash"]
