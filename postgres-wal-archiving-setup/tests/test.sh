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

# Ensure PostgreSQL is running before tests (it may have stopped on container restart)
PG_VERSION=$(ls /etc/postgresql/ 2>/dev/null | head -1)
if [ -n "$PG_VERSION" ]; then
    pg_ctlcluster "$PG_VERSION" main start 2>/dev/null || true
    # Wait for PG to be ready
    for i in $(seq 1 30); do
        if su - postgres -c "pg_isready" >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

# Ensure cron is running
service cron start 2>/dev/null || true

# Ensure sshd is running
mkdir -p /run/sshd
/usr/sbin/sshd 2>/dev/null || true

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
