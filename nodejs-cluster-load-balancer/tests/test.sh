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
uv add pytest==8.4.1 requests==2.32.3 psutil==7.0.0

# Kill any existing node processes that might be lingering
pkill -f "node /app/index.js" 2>/dev/null || true
pkill -f "node index.js" 2>/dev/null || true
sleep 1

# Start the load balancer in the background for testing
if [ -f /app/index.js ]; then
    node /app/index.js &
    SERVER_PID=$!
    echo "Started server with PID $SERVER_PID"
    # Wait for the server to be ready (up to 15 seconds)
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:8080/lb-status > /dev/null 2>&1; then
            echo "Server is ready after $((i/2)) seconds"
            break
        fi
        sleep 0.5
    done
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

# Cleanup
kill $SERVER_PID 2>/dev/null || true
pkill -f "node /app/index.js" 2>/dev/null || true
