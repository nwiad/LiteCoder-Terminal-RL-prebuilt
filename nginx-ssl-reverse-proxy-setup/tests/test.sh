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

# ---- Bring up services so we can test the live system ----
# Start backend services if start_backends.sh exists
if [ -x /app/backends/start_backends.sh ]; then
    /app/backends/start_backends.sh
    sleep 1
elif [ -f /app/backends/start_backends.sh ]; then
    bash /app/backends/start_backends.sh
    sleep 1
fi

# Start nginx if not already running (validate config first)
nginx -t 2>/dev/null && (nginx -s stop 2>/dev/null || true) && sleep 0.5 && nginx
sleep 1

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
