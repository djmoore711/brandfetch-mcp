.PHONY: help install test test-verbose format lint clean run inspector

# Default target
help:
	@echo "Brandfetch MCP Server - Available Commands:"
	@echo ""
	@echo "  make install        Install dependencies and setup environment"
	@echo "  make test           Run test suite"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo "  make format         Format code with black"
	@echo "  make lint           Check code with ruff"
	@echo "  make clean          Remove virtual environment and build artifacts"
	@echo "  make run            Run the MCP server directly"
	@echo "  make inspector      Open MCP Inspector for testing"
	@echo "  make manual-test    Run manual API test"
	@echo ""

# Install dependencies
install:
	@echo "Creating virtual environment..."
	uv venv
	@echo "Installing dependencies..."
	. .venv/bin/activate && uv pip install -e ".[dev]"
	@echo ""
	@echo "✅ Installation complete!"
	@echo "Don't forget to:"
	@echo "  1. Copy .env.example to .env"
	@echo "  2. Add your BRANDFETCH_CLIENT_ID and BRANDFETCH_API_KEY to .env"
	@echo "  3. Activate environment: source .venv/bin/activate"

# Run tests
test:
	@echo "Running tests..."
	pytest

# Run tests with verbose output
test-verbose:
	@echo "Running tests (verbose)..."
	pytest -v -s

# Format code
format:
	@echo "Formatting code with black..."
	black src/ tests/
	@echo "Auto-fixing with ruff..."
	ruff check --fix src/ tests/ || true
	@echo "✅ Code formatted!"

# Lint code
lint:
	@echo "Linting with ruff..."
	ruff check src/ tests/
	@echo "Checking types..."
	python -m mypy src/ || true

# Clean build artifacts
clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf build dist
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned!"

# Run the MCP server
run:
	@echo "Starting Brandfetch MCP server..."
	@echo "Press Ctrl+C to stop"
	uv run mcp-brandfetch

# Open MCP Inspector
inspector:
	@echo "Starting MCP Inspector..."
	@echo "This will open in your browser"
	npx @modelcontextprotocol/inspector uv --directory $(PWD) run mcp-brandfetch

# Run manual test
manual-test:
	@echo "Running manual API test..."
	python manual_test.py

# Quick verification
verify:
	@echo "Verifying installation..."
	@python -c "import mcp; import httpx; import dotenv; print('✅ All imports successful')"
	@echo "Checking API keys..."
	@python -c "from dotenv import load_dotenv; import os; load_dotenv(); lk=os.getenv('BRANDFETCH_CLIENT_ID'); bk=os.getenv('BRANDFETCH_API_KEY'); print('Logo key: ' + ('✅ found' if lk and lk != 'your_logo_api_key_here' else '❌ missing') + ', Brand key: ' + ('✅ found' if bk and bk != 'your_brand_api_key_here' else '❌ missing'))"
	@echo ""
	@echo "Ready to use!"

# Development setup (install + verify)
dev-setup: install verify
	@echo ""
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Activate environment: source .venv/bin/activate"
	@echo "  2. Run tests: make test"
	@echo "  3. Test manually: make manual-test"
