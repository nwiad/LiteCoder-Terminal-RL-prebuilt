#!/bin/bash
set -e

# ============================================================
# setup.sh - Simulate a post-reboot Docker failure environment
# ============================================================
# This script:
# 1. Installs Docker if not present
# 2. Starts Docker and creates three production containers
# 3. Simulates a post-reboot failure by breaking Docker config
# ============================================================

export DEBIAN_FRONTEND=noninteractive

echo "[setup] Installing Docker..."
apt-get update -qq
apt-get install -y -qq docker.io >/dev/null 2>&1

# Start Docker daemon manually for setup (bypass systemd inside container)
echo "[setup] Starting Docker daemon for initial setup..."
dockerd --storage-driver=overlay2 &>/tmp/dockerd-setup.log &
DOCKERD_PID=$!

# Wait for Docker to be ready
echo "[setup] Waiting for Docker daemon..."
for i in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then
        echo "[setup] Docker daemon is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[setup] ERROR: Docker daemon failed to start during setup."
        cat /tmp/dockerd-setup.log
        exit 1
    fi
    sleep 1
done

# Create three production containers
echo "[setup] Creating production containers..."
docker run -d --name prod-nginx  nginx:alpine  >/dev/null 2>&1 || true
docker run -d --name prod-app    python:3.11-alpine sleep infinity >/dev/null 2>&1 || true
docker run -d --name prod-db     postgres:alpine -c 'echo "db placeholder"' >/dev/null 2>&1 || \
  docker run -d --name prod-db alpine sleep infinity >/dev/null 2>&1 || true

echo "[setup] Verifying containers are created..."
docker ps -a --format '{{.Names}}' | sort

# Stop all containers (simulating reboot)
echo "[setup] Stopping containers (simulating reboot)..."
docker stop prod-nginx prod-app prod-db >/dev/null 2>&1 || true

# Stop the Docker daemon
echo "[setup] Stopping Docker daemon..."
kill "$DOCKERD_PID" 2>/dev/null || true
sleep 2
kill -9 "$DOCKERD_PID" 2>/dev/null || true

# Wait for dockerd to fully stop
for i in $(seq 1 10); do
    if ! pgrep -x dockerd >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# ============================================================
# Simulate the post-reboot failure:
# Corrupt the Docker daemon configuration file so Docker
# cannot start. This is a realistic scenario where a bad
# daemon.json prevents the service from launching.
# ============================================================
echo "[setup] Simulating post-reboot Docker failure..."

# Create a corrupted daemon.json (invalid JSON)
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'BADJSON'
{
    "storage-driver": "overlay2",
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m"
        "max-file": "3"
    }
    "default-runtime": "runc"
}
BADJSON

# Mask the docker service so systemctl start docker fails
systemctl mask docker.service 2>/dev/null || true
systemctl mask docker.socket 2>/dev/null || true

echo "[setup] Environment is ready."
echo "[setup] Docker is broken and will not start."
echo "[setup] Your task: diagnose, fix, and restore the production stack."
