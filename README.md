# MeshCore MCP Server

An MCP (Model Context Protocol) server that provides tools for interacting with the MeshCore API via HTTP. This enables AI assistants and web-based tools to query and send messages and advertisements on mesh networks.

## Features

**Message Tools:**
- `meshcore_get_messages` - Query messages with filters (sender, channel, type, date range)
- `meshcore_send_direct_message` - Send a direct message to a specific node
- `meshcore_send_channel_message` - Broadcast a message to the channel

**Advertisement Tools:**
- `meshcore_get_advertisements` - Query advertisements with filters (node, type, date range)
- `meshcore_send_advertisement` - Send an advertisement to announce presence on the network

**Transport:**
- HTTP with Streamable transport (MCP protocol 2025-03-26)
- Web-accessible for browser clients and agents
- Configurable host/port binding

## Quick Start with Docker (Recommended)

The easiest way to run MeshCore MCP Server is using our official Docker image:

```bash
# Basic usage (port 8000)
docker run -d \
  --name meshcore-mcp \
  -p 8000:8000 \
  -e MESHCORE_API_URL=http://your-meshcore-api:9000 \
  -e MESHCORE_API_TOKEN=your-api-token \
  ghcr.io/ipnet-mesh/meshcore-mcp:main

# Or with command-line arguments
docker run -d \
  --name meshcore-mcp \
  -p 8000:8000 \
  ghcr.io/ipnet-mesh/meshcore-mcp:main \
  --api-url http://your-meshcore-api:9000 \
  --api-token your-api-token
```

**Available tags:**
- `main` - Latest development build
- `latest` - Latest stable release
- `vX.Y.Z` - Specific version tags

**Docker Compose example:**

```yaml
version: '3.8'
services:
  meshcore-mcp:
    image: ghcr.io/ipnet-mesh/meshcore-mcp:main
    ports:
      - "8000:8000"
    environment:
      - MESHCORE_API_URL=http://meshcore-api:9000
      - MESHCORE_API_TOKEN=your-api-token
    restart: unless-stopped
```

## Installation from Source

### Prerequisites
- Python 3.10 or higher
- Access to a MeshCore API server

### Install from source

```bash
# Clone the repository
git clone https://github.com/ipnet-mesh/meshcore-mcp.git
cd meshcore-mcp

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .
```

## Configuration

The server requires connection to a MeshCore API server. Configure via environment variables or command-line arguments:

**Environment Variables:**
- `MESHCORE_API_URL` - Base URL for the MeshCore API (e.g., `http://localhost:9000`)
- `MESHCORE_API_TOKEN` - Bearer token for API authentication (optional if API is public)

**Command-Line Arguments:**
- `--api-url` - MeshCore API URL
- `--api-token` - API bearer token

## Usage

### Starting the HTTP Server

**Default (localhost:8000):**
```bash
python -m meshcore_mcp.server --api-url http://localhost:9000
```

**Custom host/port:**
```bash
python -m meshcore_mcp.server --host 0.0.0.0 --port 3000 --api-url http://localhost:9000
```

**With authentication:**
```bash
python -m meshcore_mcp.server --api-url http://localhost:9000 --api-token your-secret-token
```

**As an installed command:**
```bash
meshcore-mcp --api-url http://localhost:9000
```

The server will print:
```
API URL configured: http://localhost:9000
API token configured (authentication enabled)
Starting MeshCore MCP Server on 0.0.0.0:8000
Server URL: http://0.0.0.0:8000
Server ready.
```

### With Claude Desktop

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "meshcore": {
      "url": "http://localhost:8000"
    }
  }
}
```

### With OpenWebUI

OpenWebUI uses [MCPO](https://github.com/open-webui/mcpo) (MCP-to-OpenAPI proxy) to connect to MCP servers. Configure MCPO with:

```json
{
  "mcpServers": {
    "meshcore": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Tool Examples

### Querying Messages

```json
{
  "sender_public_key": "abc123...64chars",
  "message_type": "contact",
  "limit": 50
}
```

### Sending a Direct Message

```json
{
  "destination": "abc123...64chars",
  "text": "Hello from MCP!"
}
```

Note: The destination must be a full 64-character public key.

### Sending a Channel Message

```json
{
  "text": "Hello everyone!",
  "flood": true
}
```

### Querying Advertisements

```json
{
  "adv_type": "chat",
  "limit": 100
}
```

### Sending an Advertisement

```json
{
  "flood": false
}
```

Use `flood: false` for zero-hop broadcasts to immediate neighbors, or `flood: true` for multi-hop broadcasts.

## Example Conversation with Claude

```
You: Show me the recent messages on the network

Claude: Let me query the recent messages.
[Uses meshcore_get_messages tool]
Messages (3 of 15 total):
============================================================

[1] CONTACT MESSAGE (received)
  ID: 42
  Sender Key: a1b2c3d4...
  Content: Hello everyone!
  SNR: -5.5 dB
  Path Length: 2 hops
  Received: 2025-11-22T14:30:00

[2] CHANNEL MESSAGE (received)
  ID: 41
  Channel: 0
  Content: Weather update: Clear skies
  Received: 2025-11-22T14:25:00
...

You: Send a message to node a1b2c3d4... saying "Got your message!"

Claude: I'll send that direct message.
[Uses meshcore_send_direct_message tool]
Direct message send succeeded: Message queued for delivery
  Queue position: 1
  Estimated wait: 0.5s
```

## Architecture

The server uses **FastMCP** with **Streamable HTTP transport** for web accessibility. It acts as a client to the MeshCore API, translating MCP tool calls into HTTP requests.

**Key Components:**
- **HTTP Server**: FastMCP with streamable-http transport (MCP 2025-03-26)
- **API Client**: httpx-based async client for MeshCore API
- **Server State**: Configuration for API URL and authentication
- **Tool Decorators**: Each tool uses `@mcp.tool()` for automatic registration

**Why HTTP?**
- **Web Accessible**: Compatible with browser-based clients and agents
- **Stateless**: Can be scaled horizontally
- **Remote Access**: Connect from anywhere on the network
- **Standard Protocol**: Uses MCP Streamable HTTP (latest standard)

## Development

### Building the Docker Image

```bash
# Build locally
docker build -t meshcore-mcp:local .

# Run your local build
docker run -p 8000:8000 -e MESHCORE_API_URL=http://localhost:9000 meshcore-mcp:local
```

### Project Structure

```
meshcore-mcp/
├── src/
│   └── meshcore_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP HTTP server
│       ├── state.py           # Configuration state
│       ├── client.py          # API HTTP client
│       └── tools/
│           ├── __init__.py
│           ├── messages.py    # Message tools
│           └── advertisements.py  # Advertisement tools
├── specs/
│   └── openapi.json           # MeshCore API spec
├── Dockerfile
├── pyproject.toml
├── README.md
└── LICENSE
```

### Running Tests

```bash
# Activate virtual environment first
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Command-Line Options

```
usage: server.py [-h] [--host HOST] [--port PORT] [--api-url API_URL]
                 [--api-token API_TOKEN] [--verbose]

MeshCore MCP Server - HTTP/Streamable transport

options:
  -h, --help            show this help message and exit
  --host HOST           Host to bind to (default: 0.0.0.0)
  --port PORT           Port to bind to (default: 8000)
  --api-url API_URL     MeshCore API URL (e.g., http://localhost:9000).
                        Can also be set via MESHCORE_API_URL env var.
  --api-token API_TOKEN
                        MeshCore API bearer token for authentication.
                        Can also be set via MESHCORE_API_TOKEN env var.
  --verbose, -v         Enable verbose (DEBUG level) logging.
```

## Dependencies

- [httpx](https://pypi.org/project/httpx/) (>=0.27.0) - Modern async HTTP client
- [mcp](https://pypi.org/project/mcp/) (>=1.0.0) - Model Context Protocol SDK with FastMCP

## Security Considerations

**Important**: The HTTP server does not include authentication by default. For production use:

- Deploy behind a reverse proxy with authentication (nginx, Apache)
- Use HTTPS/TLS for encrypted connections
- Restrict network access with firewall rules
- Consider using SSH tunneling for remote access
- Do not expose directly to the internet without proper security

## License

GPL-3.0-or-later - see LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Links

- [MeshCore API](https://github.com/ipnet-mesh/meshcore-api)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop](https://claude.ai/desktop)
