# MeshCore MCP Server

An MCP (Model Context Protocol) server that provides tools for interacting with MeshCore companion radio nodes via HTTP. This enables AI assistants and web-based tools to control and communicate with mesh network devices.

## Features

**Core Tools:**
- `meshcore_connect` - Connect to devices via Serial, BLE, or TCP
- `meshcore_disconnect` - Cleanly disconnect from devices
- `meshcore_send_message` - Send messages to contacts
- `meshcore_get_contacts` - List all contacts
- `meshcore_get_device_info` - Query device information
- `meshcore_get_battery` - Check battery status

**Transport:**
- HTTP with Streamable transport (MCP protocol 2025-03-26)
- Web-accessible for browser clients and agents
- Configurable host/port binding

## Installation

### Prerequisites
- Python 3.10 or higher
- A MeshCore-compatible device (connected via Serial/BLE/TCP)

### Install from source

```bash
# Clone the repository
git clone https://github.com/ipnet-mesh/meshcore-mcp.git
cd meshcore-mcp

# Install dependencies
pip install -e .
```

## Usage

### Starting the HTTP Server

**Default (localhost:8000):**
```bash
python -m meshcore_mcp.server
```

**Custom host/port:**
```bash
python -m meshcore_mcp.server --host 0.0.0.0 --port 3000
```

**As an installed command:**
```bash
meshcore-mcp --host 0.0.0.0 --port 8080
```

The server will print:
```
Starting MeshCore MCP Server on 0.0.0.0:8000
Server URL: http://0.0.0.0:8000
```

### With Claude Desktop (HTTP)

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

For remote servers:
```json
{
  "mcpServers": {
    "meshcore": {
      "url": "http://your-server-ip:8000"
    }
  }
}
```

### With OpenAI Agents / Web Tools

The HTTP server is compatible with any MCP client that supports the Streamable HTTP transport:

```python
# Example client connection
import requests

# List tools
response = requests.post("http://localhost:8000/mcp/v1/tools/list")
print(response.json())

# Call a tool
response = requests.post(
    "http://localhost:8000/mcp/v1/tools/call",
    json={
        "name": "meshcore_connect",
        "arguments": {
            "type": "serial",
            "port": "/dev/ttyUSB0"
        }
    }
)
print(response.json())
```

## Tool Examples

### Connecting to a Device

**Serial Connection:**
```json
{
  "type": "serial",
  "port": "/dev/ttyUSB0",
  "baud_rate": 115200,
  "debug": true
}
```

**BLE Connection:**
```json
{
  "type": "ble",
  "address": "12:34:56:78:90:AB",
  "pin": "123456"
}
```

**TCP Connection:**
```json
{
  "type": "tcp",
  "host": "192.168.1.100",
  "port": "4000",
  "auto_reconnect": true
}
```

### Sending a Message

```json
{
  "destination": "Alice",
  "text": "Hello from MCP!"
}
```

### Getting Contacts

Call `meshcore_get_contacts` with no parameters to retrieve your contact list.

### Querying Device Info

Call `meshcore_get_device_info` to get device name, version, and configuration details.

### Checking Battery

Call `meshcore_get_battery` to get current battery level and status.

## Example Conversation with Claude

```
You: Connect to my MeshCore device on /dev/ttyUSB0

Claude: I'll connect to your MeshCore device.
[Uses meshcore_connect tool]
Successfully connected to MeshCore device via serial

You: What's my battery level?

Claude: Let me check your battery status.
[Uses meshcore_get_battery tool]
Battery Level: 85%

You: Send a message to Bob saying "Meeting at 3pm"

Claude: I'll send that message to Bob.
[Uses meshcore_send_message tool]
Message sent to Bob: "Meeting at 3pm"
Result: MSG_SENT
```

## Architecture

The server uses **FastMCP** with **Streamable HTTP transport** for web accessibility. Connection state is managed globally, and all tools validate connectivity before executing commands.

**Key Components:**
- **HTTP Server**: FastMCP with streamable-http transport (MCP 2025-03-26)
- **Server State**: Global `ServerState` class maintains connection instance
- **Tool Decorators**: Each tool uses `@mcp.tool()` for automatic registration
- **Error Handling**: All commands check for EventType.ERROR responses
- **Connection Types**: Supports Serial, BLE, and TCP with appropriate validation

**Why HTTP?**
- **Web Accessible**: Compatible with browser-based clients and agents
- **Stateless Options**: Can be scaled horizontally if needed
- **Remote Access**: Connect from anywhere on the network
- **Standard Protocol**: Uses MCP Streamable HTTP (latest standard)

## Development

### Project Structure

```
meshcore-mcp/
├── src/
│   └── meshcore_mcp/
│       ├── __init__.py
│       └── server.py          # FastMCP HTTP server
├── examples/
│   └── claude_desktop_config.json
├── pyproject.toml
├── README.md
└── LICENSE
```

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Testing the Server

Start the server:
```bash
python -m meshcore_mcp.server --port 8000
```

In another terminal, test with curl:
```bash
# List available tools
curl -X POST http://localhost:8000/mcp/v1/tools/list

# Connect to a device
curl -X POST http://localhost:8000/mcp/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "meshcore_connect",
    "arguments": {
      "type": "serial",
      "port": "/dev/ttyUSB0"
    }
  }'
```

## Troubleshooting

**Connection Issues:**
- Verify device is powered on and accessible
- Check port/address permissions (Serial: user in `dialout` group)
- Enable `debug: true` in connect parameters for verbose logging

**HTTP Server Issues:**
- Check if port is already in use: `lsof -i :8000`
- Try a different port: `--port 8080`
- For remote access, ensure firewall allows the port

**Tool Call Failures:**
- Ensure you're connected before calling other tools
- Check that contact names/keys are correct
- Verify device firmware is compatible with meshcore_py 2.2.1+

**BLE Pairing:**
- Use the `pin` parameter if your device requires pairing
- Ensure Bluetooth is enabled on your system
- Check that BLE address format is correct (XX:XX:XX:XX:XX:XX)

## Command-Line Options

```
usage: server.py [-h] [--host HOST] [--port PORT]

MeshCore MCP Server - HTTP/Streamable transport

options:
  -h, --help   show this help message and exit
  --host HOST  Host to bind to (default: 0.0.0.0)
  --port PORT  Port to bind to (default: 8000)
```

## Dependencies

- [meshcore](https://pypi.org/project/meshcore/) (>=2.2.1) - Python library for MeshCore devices
- [mcp](https://pypi.org/project/mcp/) (>=1.0.0) - Model Context Protocol SDK with FastMCP

## Security Considerations

**Important**: The HTTP server does not include authentication by default. For production use:

- Deploy behind a reverse proxy with authentication (nginx, Apache)
- Use HTTPS/TLS for encrypted connections
- Restrict network access with firewall rules
- Consider using SSH tunneling for remote access
- Do not expose directly to the internet without proper security

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Future Enhancements

Planned features for future releases:
- Message history and event buffering
- MCP resources for device state
- Event subscription tools (real-time message monitoring)
- Advanced configuration (TX power, device name)
- Message acknowledgment tracking
- Auto message fetching/monitoring
- Authentication/authorization support
- WebSocket support for real-time updates

## Links

- [MeshCore Python Library](https://github.com/meshcore-dev/meshcore_py)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop](https://claude.ai/desktop)
