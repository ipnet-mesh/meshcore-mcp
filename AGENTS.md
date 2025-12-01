# Agent Instructions for MeshCore MCP Server

This document provides instructions for AI coding assistants working with this repository.

## Quick Start for Testing/Running

### Recommended: Docker

For quick testing or running the server, use Docker:

```bash
# Basic usage with API configuration
docker run -d -p 8000:8000 \
  -e MESHCORE_API_URL=http://your-meshcore-api:9000 \
  -e MESHCORE_API_TOKEN=your-api-token \
  ghcr.io/ipnet-mesh/meshcore-mcp:main

# Build locally
docker build -t meshcore-mcp:local .
docker run -d -p 8000:8000 \
  -e MESHCORE_API_URL=http://your-meshcore-api:9000 \
  meshcore-mcp:local
```

**Available images:**
- `ghcr.io/ipnet-mesh/meshcore-mcp:main` - Latest development
- `ghcr.io/ipnet-mesh/meshcore-mcp:latest` - Latest stable release

### For Development: Virtual Environment Setup

**WHEN MODIFYING CODE**, you must create and activate a virtual environment:

```bash
# Create virtual environment in ./.venv
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

**All subsequent development commands (pip install, pytest, python -m, etc.) MUST be run within the activated virtual environment.**

## Project Overview

This is a MeshCore MCP (Model Context Protocol) server that provides HTTP-based tools for interacting with the MeshCore API. It uses:

- **FastMCP** with Streamable HTTP transport
- **httpx** for async HTTP requests to MeshCore API
- Python 3.10+

## Installation Steps (After Virtual Environment)

Once the virtual environment is activated:

```bash
# Install in development mode
pip install -e .

# For development with test dependencies
pip install -e ".[dev]"
```

## Development Workflow

### 1. Running the Server

**With Docker (recommended for testing):**
```bash
# Using public image
docker run -p 8000:8000 \
  -e MESHCORE_API_URL=http://localhost:9000 \
  ghcr.io/ipnet-mesh/meshcore-mcp:main

# Build and run locally
docker build -t meshcore-mcp:local .
docker run -p 8000:8000 \
  -e MESHCORE_API_URL=http://localhost:9000 \
  meshcore-mcp:local
```

**With Python (for code development):**
```bash
# Activate virtual environment first
source .venv/bin/activate

# Default (localhost:8000)
python -m meshcore_mcp.server --api-url http://localhost:9000

# Custom host/port with authentication
python -m meshcore_mcp.server --host 0.0.0.0 --port 3000 \
  --api-url http://localhost:9000 --api-token your-token
```

### 2. Testing

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run tests (if configured)
pytest

# Manual testing with MCP clients (see README.md)
```

### 3. Code Structure

```
src/meshcore_mcp/
├── __init__.py
├── server.py          # Main FastMCP HTTP server
├── state.py           # Configuration state (API URL, token)
├── client.py          # HTTP client for MeshCore API
└── tools/
    ├── __init__.py
    ├── messages.py    # Message query/send tools
    └── advertisements.py  # Advertisement query/send tools
```

**Key Components:**
- `ServerState`: Global configuration state (API URL, token)
- `client.py`: Async HTTP client with error handling
- `@mcp.tool()`: Tool decorators for MCP tool registration

## Available MCP Tools

### Messages
1. `meshcore_get_messages` - Query messages with filters
2. `meshcore_send_direct_message` - Send direct message to a node
3. `meshcore_send_channel_message` - Broadcast message to channel

### Advertisements
4. `meshcore_get_advertisements` - Query advertisements with filters
5. `meshcore_send_advertisement` - Send advertisement to network

## Common Tasks

### Adding a New Tool

1. Decide which module the tool belongs to (messages.py, advertisements.py, or create new)
2. Define tool function with async and proper type hints
3. Use `@mcp.tool()` decorator inside the `register_tools` function
4. Use `api_get` or `api_post` from `client.py` for API calls
5. Handle `APIError` exceptions appropriately
6. Document parameters clearly in docstring
7. Update `tools/__init__.py` if adding a new module

### Modifying Existing Tools

1. Check the OpenAPI spec in `specs/openapi.json` for API details
2. Ensure error handling for API failures
3. Update docstrings if behavior changes
4. Test with actual MeshCore API if possible

### Debugging

- Use `--verbose` flag for DEBUG level logging
- Check server logs for error messages
- Verify API connectivity separately with curl
- Test with actual MeshCore API before integrating

## Important Notes

- **Virtual Environment**: Always activate `.venv` first
- **API Configuration**: Tools require `MESHCORE_API_URL` to be set
- **HTTP Transport**: Server uses Streamable HTTP (MCP 2025-03-26 protocol)
- **Error Handling**: All tools catch and format API errors
- **Public Keys**: Most API operations require full 64-character hex public keys

## Dependencies

Core dependencies are defined in `pyproject.toml`:
- `httpx>=0.27.0` - Async HTTP client for MeshCore API
- `mcp>=1.0.0` - Model Context Protocol SDK

## Configuration

**Environment Variables:**
- `MESHCORE_API_URL` - Base URL for MeshCore API (required)
- `MESHCORE_API_TOKEN` - Bearer token for authentication (optional)

**Command-line Arguments:**
- `--api-url` - MeshCore API URL
- `--api-token` - API bearer token
- `--host` - Server host (default: 0.0.0.0)
- `--port` - Server port (default: 8000)
- `--verbose` - Enable debug logging

## Git Workflow

- Work on feature branches
- Write clear commit messages
- Test changes before committing
- Update documentation as needed

## Questions or Issues?

Refer to:
- `README.md` - User-facing documentation
- `specs/openapi.json` - MeshCore API specification
- `pyproject.toml` - Dependency and metadata
- `src/meshcore_mcp/` - Implementation details
