#!/usr/bin/env python3
"""
MeshCore MCP Server - Minimal Viable Implementation

Provides MCP tools for interacting with MeshCore companion radio nodes.
Supports Serial, BLE, and TCP connections.
"""

import asyncio
import sys
from typing import Optional, Any
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Import meshcore library
try:
    from meshcore import MeshCore, EventType
except ImportError:
    print("Error: meshcore library not installed. Run: pip install meshcore", file=sys.stderr)
    sys.exit(1)


# Global state
class ServerState:
    """Maintains global server state."""
    meshcore: Optional[MeshCore] = None
    connection_type: Optional[str] = None
    connection_params: dict = {}


state = ServerState()


# Initialize MCP server
app = Server("meshcore-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="meshcore_connect",
            description=(
                "Connect to a MeshCore device. Supports three connection types: "
                "'serial' (requires port, optional baud_rate), "
                "'ble' (requires address, optional pin), "
                "'tcp' (requires host and port). "
                "Example: {\"type\": \"serial\", \"port\": \"/dev/ttyUSB0\", \"baud_rate\": 115200}"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["serial", "ble", "tcp"],
                        "description": "Connection type"
                    },
                    "port": {
                        "type": "string",
                        "description": "Serial port (for serial) or TCP port number (for tcp)"
                    },
                    "baud_rate": {
                        "type": "integer",
                        "description": "Baud rate for serial connection (default: 115200)"
                    },
                    "address": {
                        "type": "string",
                        "description": "BLE MAC address (for ble) or TCP host/IP (for tcp)"
                    },
                    "host": {
                        "type": "string",
                        "description": "TCP host/IP address (for tcp)"
                    },
                    "pin": {
                        "type": "string",
                        "description": "BLE pairing PIN (optional)"
                    },
                    "auto_reconnect": {
                        "type": "boolean",
                        "description": "Enable auto-reconnection (default: false)"
                    },
                    "debug": {
                        "type": "boolean",
                        "description": "Enable debug logging (default: false)"
                    }
                },
                "required": ["type"]
            }
        ),
        Tool(
            name="meshcore_disconnect",
            description="Disconnect from the currently connected MeshCore device.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="meshcore_send_message",
            description=(
                "Send a text message to a contact. Requires destination (contact name or pubkey prefix) "
                "and text message content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Contact name or public key prefix"
                    },
                    "text": {
                        "type": "string",
                        "description": "Message text to send"
                    }
                },
                "required": ["destination", "text"]
            }
        ),
        Tool(
            name="meshcore_get_contacts",
            description="Retrieve the list of all contacts from the MeshCore device.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="meshcore_get_device_info",
            description="Query device information including name, version, and configuration.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        Tool(
            name="meshcore_get_battery",
            description="Get the current battery level of the MeshCore device.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    try:
        if name == "meshcore_connect":
            return await handle_connect(arguments)
        elif name == "meshcore_disconnect":
            return await handle_disconnect(arguments)
        elif name == "meshcore_send_message":
            return await handle_send_message(arguments)
        elif name == "meshcore_get_contacts":
            return await handle_get_contacts(arguments)
        elif name == "meshcore_get_device_info":
            return await handle_get_device_info(arguments)
        elif name == "meshcore_get_battery":
            return await handle_get_battery(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_connect(args: dict) -> list[TextContent]:
    """Handle meshcore_connect tool call."""

    # Check if already connected
    if state.meshcore is not None and state.meshcore.is_connected:
        return [TextContent(
            type="text",
            text=f"Already connected via {state.connection_type}. Disconnect first."
        )]

    conn_type = args.get("type")
    debug = args.get("debug", False)
    auto_reconnect = args.get("auto_reconnect", False)

    try:
        if conn_type == "serial":
            port = args.get("port")
            if not port:
                return [TextContent(type="text", text="Error: 'port' required for serial connection")]

            baud_rate = args.get("baud_rate", 115200)
            state.meshcore = await MeshCore.create_serial(port, baud_rate, debug=debug)
            state.connection_type = "serial"
            state.connection_params = {"port": port, "baud_rate": baud_rate}

        elif conn_type == "ble":
            address = args.get("address")
            if not address:
                return [TextContent(type="text", text="Error: 'address' required for BLE connection")]

            pin = args.get("pin")
            state.meshcore = await MeshCore.create_ble(address, pin=pin)
            state.connection_type = "ble"
            state.connection_params = {"address": address, "pin": pin}

        elif conn_type == "tcp":
            host = args.get("host") or args.get("address")
            port = args.get("port")

            if not host or not port:
                return [TextContent(
                    type="text",
                    text="Error: 'host' and 'port' required for TCP connection"
                )]

            port_int = int(port) if isinstance(port, str) else port

            if auto_reconnect:
                state.meshcore = await MeshCore.create_tcp(
                    host, port_int,
                    auto_reconnect=True,
                    max_reconnect_attempts=5
                )
            else:
                state.meshcore = await MeshCore.create_tcp(host, port_int)

            state.connection_type = "tcp"
            state.connection_params = {"host": host, "port": port_int}

        else:
            return [TextContent(type="text", text=f"Error: Invalid connection type '{conn_type}'")]

        return [TextContent(
            type="text",
            text=f"Successfully connected to MeshCore device via {conn_type}"
        )]

    except Exception as e:
        state.meshcore = None
        state.connection_type = None
        state.connection_params = {}
        return [TextContent(type="text", text=f"Connection failed: {str(e)}")]


async def handle_disconnect(args: dict) -> list[TextContent]:
    """Handle meshcore_disconnect tool call."""

    if state.meshcore is None:
        return [TextContent(type="text", text="Not connected to any device")]

    try:
        await state.meshcore.disconnect()
        conn_type = state.connection_type

        state.meshcore = None
        state.connection_type = None
        state.connection_params = {}

        return [TextContent(type="text", text=f"Disconnected from {conn_type} device")]

    except Exception as e:
        return [TextContent(type="text", text=f"Disconnect failed: {str(e)}")]


async def handle_send_message(args: dict) -> list[TextContent]:
    """Handle meshcore_send_message tool call."""

    if state.meshcore is None or not state.meshcore.is_connected:
        return [TextContent(type="text", text="Error: Not connected. Use meshcore_connect first.")]

    destination = args.get("destination")
    text = args.get("text")

    if not destination or not text:
        return [TextContent(type="text", text="Error: 'destination' and 'text' required")]

    try:
        result = await state.meshcore.commands.send_msg(destination, text)

        if result.type == EventType.ERROR:
            return [TextContent(type="text", text=f"Send failed: {result.payload}")]

        return [TextContent(
            type="text",
            text=f"Message sent to {destination}: \"{text}\"\nResult: {result.type.name}"
        )]

    except Exception as e:
        return [TextContent(type="text", text=f"Send message failed: {str(e)}")]


async def handle_get_contacts(args: dict) -> list[TextContent]:
    """Handle meshcore_get_contacts tool call."""

    if state.meshcore is None or not state.meshcore.is_connected:
        return [TextContent(type="text", text="Error: Not connected. Use meshcore_connect first.")]

    try:
        result = await state.meshcore.commands.get_contacts()

        if result.type == EventType.ERROR:
            return [TextContent(type="text", text=f"Get contacts failed: {result.payload}")]

        contacts = result.payload

        if not contacts:
            return [TextContent(type="text", text="No contacts found")]

        # Format contacts nicely
        output = "Contacts:\n"
        for i, contact in enumerate(contacts, 1):
            name = contact.get("name", "Unknown")
            key = contact.get("pubkey_prefix", "N/A")
            output += f"{i}. {name} (key: {key})\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Get contacts failed: {str(e)}")]


async def handle_get_device_info(args: dict) -> list[TextContent]:
    """Handle meshcore_get_device_info tool call."""

    if state.meshcore is None or not state.meshcore.is_connected:
        return [TextContent(type="text", text="Error: Not connected. Use meshcore_connect first.")]

    try:
        result = await state.meshcore.commands.send_device_query()

        if result.type == EventType.ERROR:
            return [TextContent(type="text", text=f"Device query failed: {result.payload}")]

        info = result.payload

        # Format device info
        output = "Device Information:\n"
        for key, value in info.items():
            output += f"  {key}: {value}\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Get device info failed: {str(e)}")]


async def handle_get_battery(args: dict) -> list[TextContent]:
    """Handle meshcore_get_battery tool call."""

    if state.meshcore is None or not state.meshcore.is_connected:
        return [TextContent(type="text", text="Error: Not connected. Use meshcore_connect first.")]

    try:
        result = await state.meshcore.commands.get_bat()

        if result.type == EventType.ERROR:
            return [TextContent(type="text", text=f"Get battery failed: {result.payload}")]

        battery_data = result.payload

        # Format battery info
        if isinstance(battery_data, dict):
            output = "Battery Status:\n"
            for key, value in battery_data.items():
                output += f"  {key}: {value}\n"
        else:
            output = f"Battery Level: {battery_data}"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        return [TextContent(type="text", text=f"Get battery failed: {str(e)}")]


async def main():
    """Main entry point for the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
