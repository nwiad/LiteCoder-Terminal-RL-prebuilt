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
uv add pytest==8.4.1

# --- Start services if not already running ---
# Start Node.js apps in background (they may already be running)
NODE_BIN=$(which node 2>/dev/null || echo "/root/.nvm/versions/node/v22.13.1/bin/node")
for svc in svc-a svc-b svc-c; do
    port_check=""
    case "$svc" in
        svc-a) port_check=3001 ;;
        svc-b) port_check=3002 ;;
        svc-c) port_check=3003 ;;
    esac
    if ! curl -s --max-time 1 http://127.0.0.1:${port_check}/ > /dev/null 2>&1; then
        nohup ${NODE_BIN} /app/services/${svc}/index.js > /tmp/${svc}.log 2>&1 &
    fi
done

# Start nginx if not already running
if ! curl -sk --max-time 1 https://127.0.0.1/ > /dev/null 2>&1; then
    nginx 2>/dev/null || true
fi

# Wait for services to be ready
sleep 3

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
