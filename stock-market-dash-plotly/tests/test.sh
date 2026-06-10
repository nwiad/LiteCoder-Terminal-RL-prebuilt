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
uv add dash plotly requests numpy flask

# Ensure dash/plotly are also available system-wide (agent may have pip-installed them)
pip install dash plotly requests numpy flask 2>/dev/null || true

# Start the Dash app in the background for HTTP-level tests
if [ -f /app/app.py ]; then
    # Use uv run so the app has access to dash/plotly from the uv venv
    cd /app
    uv run python /app/app.py &
    APP_PID=$!
    cd - > /dev/null
    # Wait for server to be ready (up to 30 seconds)
    echo "Waiting for Dash server to start..."
    for i in $(seq 1 30); do
        if curl -s http://127.0.0.1:8050/ > /dev/null 2>&1; then
            echo "Dash server is running."
            break
        fi
        sleep 1
    done
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

# Clean up background server
if [ -n "$APP_PID" ]; then
    kill $APP_PID 2>/dev/null
fi
