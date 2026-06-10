#!/bin/bash

# Install curl
apt-get update
apt-get install -y curl openssl procps

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

# Ensure nginx is running before tests (agent may have started it but container restarted)
# Try to start nginx if it's not running, but don't fail if it can't
if command -v nginx &>/dev/null; then
    if ! pgrep -x nginx > /dev/null 2>&1; then
        nginx 2>/dev/null || true
        sleep 1
    fi
fi

# Use relative path (REQUIRED)
uv run pytest ../tests/test_outputs.py -rA -v
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
