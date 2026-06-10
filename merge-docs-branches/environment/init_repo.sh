#!/bin/bash
set -e

# Configure git
git config --global user.email "test@example.com"
git config --global user.name "Test User"
git config --global init.defaultBranch main

# Initialize repository
cd /app
git init
git config receive.denyCurrentBranch ignore

# Create initial sensor documentation files
cat > sensors.md << 'EOF'
# Sensor Documentation

## Overview
This document describes the environmental sensors used in our monitoring system.

## Sensors List
- Temperature Sensor
- Humidity Sensor
- Pressure Sensor

## General Specifications
All sensors operate on 5V power supply and use I2C communication protocol.
EOF

# Initial commit on main
git add sensors.md
git commit -m "Initial sensor documentation"

# Create docs-temperature branch
git checkout -b docs-temperature
cat > sensors.md << 'EOF'
# Sensor Documentation

## Overview
This document describes the environmental sensors used in our monitoring system.

## Temperature Sensor
The temperature sensor measures ambient temperature with high precision.
- Range: -40°C to 125°C
- Accuracy: ±0.5°C
- Response time: 2 seconds

## Sensors List
- Temperature Sensor
- Humidity Sensor
- Pressure Sensor

## General Specifications
All sensors operate on 5V power supply and use I2C communication protocol.
EOF
git add sensors.md
git commit -m "Add temperature sensor documentation"

# Create docs-humidity branch from main
git checkout main
git checkout -b docs-humidity
cat > sensors.md << 'EOF'
# Sensor Documentation

## Overview
This document describes the environmental sensors used in our monitoring system.

## Humidity Sensor
The humidity sensor detects moisture levels in the environment.
- Range: 0% to 100% RH
- Accuracy: ±2% RH
- Response time: 8 seconds

## Sensors List
- Temperature Sensor
- Humidity Sensor
- Pressure Sensor

## General Specifications
All sensors operate on 5V power supply and use I2C communication protocol.
EOF
git add sensors.md
git commit -m "Add humidity sensor documentation"

# Create docs-pressure branch from main
git checkout main
git checkout -b docs-pressure
cat > sensors.md << 'EOF'
# Sensor Documentation

## Overview
This document describes the environmental sensors used in our monitoring system.

## Pressure Sensor
The pressure sensor monitors atmospheric pressure changes.
- Range: 300 to 1100 hPa
- Accuracy: ±1 hPa
- Response time: 5 seconds

## Sensors List
- Temperature Sensor
- Humidity Sensor
- Pressure Sensor

## General Specifications
All sensors operate on 5V power supply and use I2C communication protocol.
EOF
git add sensors.md
git commit -m "Add pressure sensor documentation"

# Return to main branch
git checkout main

# Set up bare repository as remote origin
cd /tmp
git clone --bare /app /tmp/origin.git
cd /app
git remote add origin /tmp/origin.git
git push origin main docs-temperature docs-humidity docs-pressure

echo "Repository initialized with branches: main, docs-temperature, docs-humidity, docs-pressure"
