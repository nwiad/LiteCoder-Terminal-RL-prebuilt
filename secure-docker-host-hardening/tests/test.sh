#!/bin/bash

# Install curl
apt-get update
apt-get install -y curl

# Install uv
curl -LsSf https://astral.sh/uv/0.7.13/install.sh | sh

source $HOME/.local/bin/env

# The task WORKDIR is /, which uv init doesn't like.
# Create a temporary workspace next to the tests directory.
mkdir -p /tmp/test_workspace
cd /tmp/test_workspace

uv init
uv add pytest==8.4.1

# Use relative path (REQUIRED) — tests/ lives at the repo root
uv run pytest /tests/test_outputs.py -rA
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
