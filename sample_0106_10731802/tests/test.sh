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

# Ensure lighttpd is running before tests (it may have been stopped)
# Try systemctl first, then direct start
if command -v systemctl &>/dev/null && [ -d /run/systemd/system ]; then
    systemctl start lighttpd 2>/dev/null || true
else
    if command -v lighttpd &>/dev/null && [ -f /etc/lighttpd/lighttpd.conf ]; then
        # Only start if not already running
        if ! ss -tlnp 2>/dev/null | grep -q 4443 && ! netstat -tlnp 2>/dev/null | grep -q 4443; then
            lighttpd -f /etc/lighttpd/lighttpd.conf 2>/dev/null || true
        fi
    fi
fi
sleep 2

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
