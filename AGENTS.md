# Agent Instructions for MeshCore MCP Server

This document provides instructions for AI coding assistants working with this repository.

## Quick Start for Testing/Running

### Recommended: Docker

For quick testing or running the server, use Docker:

```bash
# Basic usage
docker run -d -p 8000:8000 ghcr.io/ipnet-mesh/meshcore-mcp:main

# With serial device access
docker run -d -p 8000:8000 --device=/dev/ttyUSB0 \
  ghcr.io/ipnet-mesh/meshcore-mcp:main \
  --serial-port /dev/ttyUSB0 --sync-clock-on-startup

# Build locally
docker build -t meshcore-mcp:local .
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

This is a MeshCore MCP (Model Context Protocol) server that provides HTTP-based tools for controlling mesh network devices. It uses:

- **FastMCP** with Streamable HTTP transport
- **meshcore** Python library (>=2.2.1)
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
docker run -p 8000:8000 ghcr.io/ipnet-mesh/meshcore-mcp:main

# Build and run locally
docker build -t meshcore-mcp:local .
docker run -p 8000:8000 meshcore-mcp:local

# With device access
docker run -p 8000:8000 --device=/dev/ttyUSB0 \
  meshcore-mcp:local --serial-port /dev/ttyUSB0
```

**With Python (for code development):**
```bash
# Activate virtual environment first
source .venv/bin/activate

# Default (localhost:8000)
python -m meshcore_mcp.server

# Custom host/port
python -m meshcore_mcp.server --host 0.0.0.0 --port 3000
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
└── server.py          # Main FastMCP HTTP server with all tools
```

**Key Components:**
- `ServerState`: Global connection state management
- `@mcp.tool()`: Tool decorators for MCP tool registration
- Connection types: Serial, BLE, TCP

## Available MCP Tools

1. `meshcore_connect` - Connect to devices
2. `meshcore_disconnect` - Disconnect from devices
3. `meshcore_send_message` - Send messages to contacts
4. `meshcore_get_contacts` - List all contacts
5. `meshcore_get_device_info` - Query device information
6. `meshcore_get_battery` - Check battery status

## Common Tasks

### Adding a New Tool

1. Define tool function in `server.py`
2. Use `@mcp.tool()` decorator
3. Validate connection state if needed
4. Handle errors appropriately
5. Document parameters clearly

### Modifying Existing Tools

1. Check `ServerState` for connection context
2. Ensure error handling for `EventType.ERROR`
3. Update docstrings if behavior changes
4. Test with actual device if possible

### Debugging

- Use `debug=True` in connect parameters
- Check server logs for error messages
- Verify device connectivity separately
- Test with curl before integrating

## Important Notes

- **Virtual Environment**: Always activate `.venv` first
- **Connection State**: Tools depend on successful connection via `meshcore_connect`
- **HTTP Transport**: Server uses Streamable HTTP (MCP 2025-03-26 protocol)
- **Error Handling**: All tools check for ERROR event types
- **Security**: No authentication by default - document security considerations

## Dependencies

Core dependencies are defined in `pyproject.toml`:
- `meshcore>=2.2.1` - MeshCore device library
- `mcp>=1.0.0` - Model Context Protocol SDK

## Git Workflow

- Work on feature branches
- Write clear commit messages
- Test changes before committing
- Update documentation as needed

## Questions or Issues?

Refer to:
- `README.md` - User-facing documentation
- `pyproject.toml` - Dependency and metadata
- `src/meshcore_mcp/server.py` - Implementation details
