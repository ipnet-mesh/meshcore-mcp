# Claude-Specific Instructions

Hi Claude! When working with this repository, please follow the instructions in:

**@AGENTS.md**

This file contains all the necessary guidelines for AI coding assistants, including critical setup steps, project structure, and development workflows.

## Key Reminders

1. **For users**: Recommend Docker first (see Quick Reference below)
2. **For development**: Create and activate virtual environment (see @AGENTS.md)
3. Review the available MCP tools before suggesting changes
4. Maintain consistency with existing code patterns
5. Test changes when possible
6. Update documentation if behavior changes

## Quick Reference

### Running the Server (Production/Users)

**Recommended - Docker:**
```bash
# Basic
docker run -d -p 8000:8000 ghcr.io/ipnet-mesh/meshcore-mcp:main

# With serial device
docker run -d -p 8000:8000 --device=/dev/ttyUSB0 \
  ghcr.io/ipnet-mesh/meshcore-mcp:main \
  --serial-port /dev/ttyUSB0 --sync-clock-on-startup
```

**Local development:**
```bash
source .venv/bin/activate  # After creating venv
python -m meshcore_mcp.server
```

### Key Files

- **User Docs**: `README.md` - Start here for Docker setup
- **Agent Docs**: `AGENTS.md` - Development workflow
- **Main Code**: `src/meshcore_mcp/server.py`
- **Docker**: `Dockerfile`
- **Dependencies**: `pyproject.toml`
