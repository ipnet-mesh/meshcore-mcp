# MeshCore MCP Server

An MCP (Model Context Protocol) server that provides tools for interacting with MeshCore companion radio nodes. This enables AI assistants like Claude to control and communicate with mesh network devices.

## Features

**Core Tools:**
- `meshcore_connect` - Connect to devices via Serial, BLE, or TCP
- `meshcore_disconnect` - Cleanly disconnect from devices
- `meshcore_send_message` - Send messages to contacts
- `meshcore_get_contacts` - List all contacts
- `meshcore_get_device_info` - Query device information
- `meshcore_get_battery` - Check battery status

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

### With Claude Desktop

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "meshcore": {
      "command": "python",
      "args": ["-m", "meshcore_mcp.server"],
      "cwd": "/path/to/meshcore-mcp"
    }
  }
}
```

Or if installed system-wide:

```json
{
  "mcpServers": {
    "meshcore": {
      "command": "meshcore-mcp"
    }
  }
}
```

### Standalone Usage

You can also run the server directly for testing:

```bash
python -m meshcore_mcp.server
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
  "port": 4000,
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

Simply call `meshcore_get_contacts` with no parameters to retrieve your contact list.

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

The server maintains a persistent connection to a single MeshCore device per session. Connection state is managed globally, and all tools validate connectivity before executing commands.

**Key Components:**
- **Server State**: Global `ServerState` class maintains connection instance
- **Tool Handlers**: Each tool has a dedicated async handler function
- **Error Handling**: All commands check for EventType.ERROR responses
- **Connection Types**: Supports Serial, BLE, and TCP with appropriate validation

## Development

### Project Structure

```
meshcore-mcp/
├── src/
│   └── meshcore_mcp/
│       ├── __init__.py
│       └── server.py          # Main MCP server implementation
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

## Troubleshooting

**Connection Issues:**
- Verify device is powered on and accessible
- Check port/address permissions (Serial: user in `dialout` group)
- Enable `debug: true` in connect parameters for verbose logging

**Tool Call Failures:**
- Ensure you're connected before calling other tools
- Check that contact names/keys are correct
- Verify device firmware is compatible with meshcore_py 2.2.1+

**BLE Pairing:**
- Use the `pin` parameter if your device requires pairing
- Ensure Bluetooth is enabled on your system
- Check that BLE address format is correct (XX:XX:XX:XX:XX:XX)

## Dependencies

- [meshcore](https://pypi.org/project/meshcore/) - Python library for MeshCore devices
- [mcp](https://pypi.org/project/mcp/) - Model Context Protocol SDK

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## Future Enhancements

Planned features for future releases:
- Message history and event buffering
- MCP resources for device state
- Event subscription tools
- Advanced configuration (TX power, device name)
- Message acknowledgment tracking
- Auto message fetching/monitoring

## Links

- [MeshCore Python Library](https://github.com/meshcore-dev/meshcore_py)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)
