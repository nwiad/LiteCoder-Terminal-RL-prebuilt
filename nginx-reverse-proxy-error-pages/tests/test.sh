#!/bin/bash

# Install curl
apt-get update
apt-get install -y curl

# Install uv
curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh

source $HOME/.local/bin/env

# Check if we're in a valid working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

uv init
uv add pytest==8.4.1 requests==2.32.3

# --- Start services so integration tests can run ---
# Start Flask backends if start_services.sh exists
if [ -f /app/start_services.sh ]; then
    chmod +x /app/start_services.sh
    /app/start_services.sh || true
    sleep 2
fi

# Validate and start Nginx
if [ -f /etc/nginx/conf.d/reverse_proxy.conf ]; then
    nginx -t 2>/dev/null && {
        nginx -s stop 2>/dev/null || true
        sleep 1
        nginx
        sleep 1
    }
fi

# Use relative path (REQUIRED)
uv run pytest ../tests/test_outputs.py -rA
code=$?
case $code in
  0)
    echo 1 > /logs/verifier/reward.txt
    ;;
  1)
    echo 0 > /logs/verifier/reward.txt
    ;;
  2|3|4|5)
    exit $code
    ;;
  *)
    exit $code
    ;;
esac
