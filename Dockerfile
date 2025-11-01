FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir mcp[cli] httpx python-dotenv

# Copy environment file (should be mounted as volume in production)
COPY .env.example .env

# Run the MCP server
CMD ["python", "-m", "brandfetch_mcp.server"]
