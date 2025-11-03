#!/usr/bin/env bash
# shellcheck shell=bash
#!/bin/bash
# Simple script to run the Brandfetch MCP server
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Run: uv venv && source .venv/bin/activate && uv pip install -e '.[dev]'"
    exit 1
fi
if [ ! -f ".env" ]; then
    echo "Error: .env file not found."
    echo "Copy .env.example to .env and add your BRANDFETCH_CLIENT_ID and BRANDFETCH_API_KEY"
    exit 1
fi

# Verify both API keys are set
if ! grep -q "BRANDFETCH_CLIENT_ID" .env || ! grep -q "BRANDFETCH_API_KEY" .env; then
    echo "Error: Missing API keys in .env file"
    echo "Please set both BRANDFETCH_CLIENT_ID and BRANDFETCH_API_KEY"
    exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate
exec python -m brandfetch_mcp.server
