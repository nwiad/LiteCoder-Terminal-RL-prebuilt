#!/bin/bash

# Install curl
apt-get update
apt-get install -y curl nginx

# Install uv
curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh

source $HOME/.local/bin/env

# Check if we're in a valid working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

# Ensure nginx is running for runtime tests
# The agent should have started it, but try to ensure it's up
nginx -t 2>/dev/null && (service nginx start 2>/dev/null || nginx 2>/dev/null) || true

uv init
uv add pytest==8.4.1 beautifulsoup4==4.13.4 lxml==5.4.0

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
