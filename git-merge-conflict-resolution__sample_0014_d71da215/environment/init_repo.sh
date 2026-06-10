#!/bin/bash
set -e

cd /app

# Initialize git repository
git init
git config user.name "Initial Setup"
git config user.email "setup@tinygraph.dev"

# Create initial commit
git add .
git commit -m "Initial commit: Add core graph module"
