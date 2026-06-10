#!/bin/bash
set -e

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    apt-get update -qq
    apt-get install -y -qq nginx curl procps net-tools > /dev/null 2>&1
fi

# Stop nginx if running
systemctl stop nginx 2>/dev/null || service nginx stop 2>/dev/null || nginx -s stop 2>/dev/null || true

# --- Introduce configuration errors in nginx.conf ---
cat > /etc/nginx/nginx.conf << 'NGINXCONF'
user www-data;
worker_processes 1;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 256;
}

http {
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;
    server_tokens on;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Missing semicolon on next line (syntax error)
    keepalive_timeout 90

    # gzip is off
    gzip off;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
NGINXCONF

# --- Introduce errors in default site config ---
cat > /etc/nginx/sites-enabled/default << 'SITECONF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm;

    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    # Broken location block - missing closing brace
    location /api/health {
        return 200 '{"status": "ok"}';
        add_header Content-Type application/json;

}
SITECONF

# --- Create a port conflict on port 80 ---
if command -v python3 &> /dev/null; then
    python3 -c "
import socket, time, os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 80))
s.listen(1)
while True:
    time.sleep(60)
" &
else
    while true; do echo -e "HTTP/1.1 200 OK\r\n\r\noccupied" | nc -l -p 80 -q 1; done &
fi

# Give the port-occupying process a moment to bind
sleep 1

# Ensure default index page exists
mkdir -p /var/www/html
echo "<html><body><h1>Welcome</h1></body></html>" > /var/www/html/index.html

echo "Setup complete. Nginx is broken and port 80 is occupied."
echo "Your task: fix everything and get Nginx running properly."
