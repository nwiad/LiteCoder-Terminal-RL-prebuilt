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

# Kill any existing process on port 8080
pkill -f "python.*app.py" 2>/dev/null || true
sleep 1

# Ensure Flask is installed for the app
pip install flask 2>/dev/null || pip3 install flask 2>/dev/null

# Start the Flask app in the background
cd /app && python3 app.py &
APP_PID=$!

# Wait for the server to be ready (up to 30 seconds)
for i in $(seq 1 30); do
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo "Server is up on port 8080"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Server failed to start within 30 seconds"
    fi
    sleep 1
done

# Go back to the working directory for pytest
cd /app

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

# Cleanup
kill $APP_PID 2>/dev/null || true
