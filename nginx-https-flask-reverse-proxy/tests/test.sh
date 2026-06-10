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

# ---------------------------------------------------------------
# Ensure Flask and Nginx are running before tests
# ---------------------------------------------------------------

# Try to start Flask if not already running
if ! curl -s http://127.0.0.1:5000/ > /dev/null 2>&1; then
    echo "Flask not responding, attempting to start..."
    if [ -f /app/app.py ]; then
        cd /app
        nohup python3 /app/app.py > /tmp/flask_test.log 2>&1 &
        # Wait for Flask to come up
        for i in $(seq 1 15); do
            if curl -s http://127.0.0.1:5000/ > /dev/null 2>&1; then
                echo "Flask started successfully."
                break
            fi
            sleep 1
        done
        cd -
    fi
fi

# Try to start Nginx if not already running
if ! pgrep -x nginx > /dev/null 2>&1; then
    echo "Nginx not running, attempting to start..."
    nginx 2>/dev/null || true
    sleep 2
fi

uv init
uv add pytest==8.4.1

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
