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
uv add flask requests

# Install dnsmasq if not present (needed for restart tests)
apt-get install -y dnsmasq 2>/dev/null || true

# Ensure Flask app is running for API tests
# First try systemctl, then fall back to direct launch
if ! curl -s http://localhost:5000/api/domains > /dev/null 2>&1; then
    # Try starting via systemctl
    systemctl start dns-dashboard 2>/dev/null || true
    sleep 2
fi

if ! curl -s http://localhost:5000/api/domains > /dev/null 2>&1; then
    # Fall back to direct launch
    if [ -f /app/dns_dashboard/app.py ]; then
        cd /app/dns_dashboard
        nohup python3 /app/dns_dashboard/app.py > /tmp/dns_dashboard_test.log 2>&1 &
        cd -
        sleep 3
    fi
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
