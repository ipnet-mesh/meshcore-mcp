# Agent Instructions for MeshCore MCP Server

This document provides instructions for AI coding assistants working with this repository.

## ⚠️ CRITICAL: Virtual Environment Setup

**BEFORE ANY OTHER ACTIONS**, you must create and activate a virtual environment:

```bash
# Create virtual environment in ./.venv
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

**All subsequent commands (pip install, pytest, python -m, etc.) MUST be run within the activated virtual environment.**

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

```bash
# Default (localhost:8000)
python -m meshcore_mcp.server

# Custom host/port
python -m meshcore_mcp.server --host 0.0.0.0 --port 3000
```

### 2. Testing

```bash
# Run tests (if configured)
pytest

# Manual testing with curl
curl -X POST http://localhost:8000/mcp/v1/tools/list
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
