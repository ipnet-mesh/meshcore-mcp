#!/usr/bin/env python3
"""
MeshCore MCP Server - HTTP Implementation

Provides MCP tools for interacting with MeshCore companion radio nodes.
Supports Serial, BLE, and TCP connections via HTTP/Streamable transport.
"""

import argparse
import asyncio
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Import meshcore library
try:
    from meshcore import MeshCore, EventType
except ImportError:
    print("Error: meshcore library not installed. Run: pip install meshcore", file=sys.stderr)
    sys.exit(1)


# Global state for persistent MeshCore connection
class ServerState:
    """Maintains global server state."""
    meshcore: Optional[MeshCore] = None
    connection_type: Optional[str] = None
    connection_params: dict = {}


state = ServerState()


# Initialize MCP server with FastMCP
mcp = FastMCP("meshcore-mcp")


@mcp.tool()
async def meshcore_connect(
    type: str,
    port: Optional[str] = None,
    baud_rate: int = 115200,
    address: Optional[str] = None,
    host: Optional[str] = None,
    pin: Optional[str] = None,
    auto_reconnect: bool = False,
    debug: bool = False
) -> str:
    """
    Connect to a MeshCore device.

    Supports three connection types:
    - 'serial': requires port, optional baud_rate (default: 115200)
    - 'ble': requires address (MAC), optional pin for pairing
    - 'tcp': requires host and port, optional auto_reconnect

    Args:
        type: Connection type ('serial', 'ble', or 'tcp')
        port: Serial port path (for serial) or TCP port number (for tcp)
        baud_rate: Baud rate for serial connection (default: 115200)
        address: BLE MAC address (for ble) or TCP host (for tcp)
        host: TCP host/IP address (for tcp)
        pin: BLE pairing PIN (optional)
        auto_reconnect: Enable auto-reconnection (default: false)
        debug: Enable debug logging (default: false)

    Returns:
        Connection status message
    """
    # Check if already connected
    if state.meshcore is not None and state.meshcore.is_connected:
        return f"Already connected via {state.connection_type}. Disconnect first."

    try:
        if type == "serial":
            if not port:
                return "Error: 'port' required for serial connection"

            state.meshcore = await MeshCore.create_serial(port, baud_rate, debug=debug)
            state.connection_type = "serial"
            state.connection_params = {"port": port, "baud_rate": baud_rate}

        elif type == "ble":
            if not address:
                return "Error: 'address' required for BLE connection"

            state.meshcore = await MeshCore.create_ble(address, pin=pin)
            state.connection_type = "ble"
            state.connection_params = {"address": address, "pin": pin}

        elif type == "tcp":
            tcp_host = host or address
            if not tcp_host or not port:
                return "Error: 'host' and 'port' required for TCP connection"

            port_int = int(port) if isinstance(port, str) else port

            if auto_reconnect:
                state.meshcore = await MeshCore.create_tcp(
                    tcp_host, port_int,
                    auto_reconnect=True,
                    max_reconnect_attempts=5
                )
            else:
                state.meshcore = await MeshCore.create_tcp(tcp_host, port_int)

            state.connection_type = "tcp"
            state.connection_params = {"host": tcp_host, "port": port_int}

        else:
            return f"Error: Invalid connection type '{type}'. Must be 'serial', 'ble', or 'tcp'."

        return f"Successfully connected to MeshCore device via {type}"

    except Exception as e:
        state.meshcore = None
        state.connection_type = None
        state.connection_params = {}
        return f"Connection failed: {str(e)}"


@mcp.tool()
async def meshcore_disconnect() -> str:
    """
    Disconnect from the currently connected MeshCore device.

    Returns:
        Disconnection status message
    """
    if state.meshcore is None:
        return "Not connected to any device"

    try:
        await state.meshcore.disconnect()
        conn_type = state.connection_type

        state.meshcore = None
        state.connection_type = None
        state.connection_params = {}

        return f"Disconnected from {conn_type} device"

    except Exception as e:
        return f"Disconnect failed: {str(e)}"


@mcp.tool()
async def meshcore_send_message(destination: str, text: str) -> str:
    """
    Send a text message to a contact.

    Args:
        destination: Contact name or public key prefix
        text: Message text to send

    Returns:
        Send status message with result
    """
    if state.meshcore is None or not state.meshcore.is_connected:
        return "Error: Not connected. Use meshcore_connect first."

    try:
        result = await state.meshcore.commands.send_msg(destination, text)

        if result.type == EventType.ERROR:
            return f"Send failed: {result.payload}"

        return f"Message sent to {destination}: \"{text}\"\nResult: {result.type.name}"

    except Exception as e:
        return f"Send message failed: {str(e)}"


@mcp.tool()
async def meshcore_get_contacts() -> str:
    """
    Retrieve the list of all contacts from the MeshCore device.

    Returns:
        Formatted list of contacts with names and keys
    """
    if state.meshcore is None or not state.meshcore.is_connected:
        return "Error: Not connected. Use meshcore_connect first."

    try:
        result = await state.meshcore.commands.get_contacts()

        if result.type == EventType.ERROR:
            return f"Get contacts failed: {result.payload}"

        contacts = result.payload

        if not contacts:
            return "No contacts found"

        # Format contacts nicely
        output = "Contacts:\n"
        for i, contact in enumerate(contacts, 1):
            name = contact.get("name", "Unknown")
            key = contact.get("pubkey_prefix", "N/A")
            output += f"{i}. {name} (key: {key})\n"

        return output

    except Exception as e:
        return f"Get contacts failed: {str(e)}"


@mcp.tool()
async def meshcore_get_device_info() -> str:
    """
    Query device information including name, version, and configuration.

    Returns:
        Formatted device information
    """
    if state.meshcore is None or not state.meshcore.is_connected:
        return "Error: Not connected. Use meshcore_connect first."

    try:
        result = await state.meshcore.commands.send_device_query()

        if result.type == EventType.ERROR:
            return f"Device query failed: {result.payload}"

        info = result.payload

        # Format device info
        output = "Device Information:\n"
        for key, value in info.items():
            output += f"  {key}: {value}\n"

        return output

    except Exception as e:
        return f"Get device info failed: {str(e)}"


@mcp.tool()
async def meshcore_get_battery() -> str:
    """
    Get the current battery level of the MeshCore device.

    Returns:
        Battery status information
    """
    if state.meshcore is None or not state.meshcore.is_connected:
        return "Error: Not connected. Use meshcore_connect first."

    try:
        result = await state.meshcore.commands.get_bat()

        if result.type == EventType.ERROR:
            return f"Get battery failed: {result.payload}"

        battery_data = result.payload

        # Format battery info
        if isinstance(battery_data, dict):
            output = "Battery Status:\n"
            for key, value in battery_data.items():
                output += f"  {key}: {value}\n"
        else:
            output = f"Battery Level: {battery_data}"

        return output

    except Exception as e:
        return f"Get battery failed: {str(e)}"


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MeshCore MCP Server - HTTP/Streamable transport"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the MCP server."""
    args = parse_args()

    print(f"Starting MeshCore MCP Server on {args.host}:{args.port}", file=sys.stderr)
    print(f"Server URL: http://{args.host}:{args.port}", file=sys.stderr)

    # Run the FastMCP server with streamable HTTP transport
    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
