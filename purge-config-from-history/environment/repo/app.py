#!/usr/bin/env python3
"""Main application entry point"""

import json
import sys
import os

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config.json not found, using defaults")
        return {}

def main():
    config = load_config()
    print("Application started successfully")
    print(f"Environment: {os.getenv('ENV', 'development')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
