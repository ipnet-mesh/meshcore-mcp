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
    debug: bool = False


state = ServerState()


async def ensure_connected() -> Optional[str]:
    """
    Ensure MeshCore is connected, automatically reconnecting if needed.

    Returns:
        None if connected successfully, error message otherwise
    """
    # If no connection params stored, can't auto-connect
    if not state.connection_params:
        return "Error: Not connected. Use meshcore_connect first."

    # If already connected, nothing to do
    if state.meshcore is not None and state.meshcore.is_connected:
        return None

    # Need to reconnect - recreate connection
    try:
        conn_type = state.connection_type
        params = state.connection_params
        debug = state.debug

        if conn_type == "serial":
            state.meshcore = await MeshCore.create_serial(
                params["port"],
                params["baud_rate"],
                debug=debug
            )
        elif conn_type == "ble":
            state.meshcore = await MeshCore.create_ble(
                params["address"],
                pin=params.get("pin")
            )
        elif conn_type == "tcp":
            if params.get("auto_reconnect"):
                state.meshcore = await MeshCore.create_tcp(
                    params["host"],
                    params["port"],
                    auto_reconnect=True,
                    max_reconnect_attempts=5
                )
            else:
                state.meshcore = await MeshCore.create_tcp(
                    params["host"],
                    params["port"]
                )
        else:
            return f"Error: Invalid stored connection type '{conn_type}'"

        return None  # Success

    except Exception as e:
        return f"Auto-reconnect failed: {str(e)}"


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
            state.debug = debug

        elif type == "ble":
            if not address:
                return "Error: 'address' required for BLE connection"

            state.meshcore = await MeshCore.create_ble(address, pin=pin)
            state.connection_type = "ble"
            state.connection_params = {"address": address, "pin": pin}
            state.debug = debug

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
            state.connection_params = {
                "host": tcp_host,
                "port": port_int,
                "auto_reconnect": auto_reconnect
            }
            state.debug = debug

        else:
            return f"Error: Invalid connection type '{type}'. Must be 'serial', 'ble', or 'tcp'."

        return f"Successfully connected to MeshCore device via {type}"

    except Exception as e:
        state.meshcore = None
        state.connection_type = None
        state.connection_params = {}
        state.debug = False
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
        state.debug = False

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
    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        return error

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
    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        return error

    try:
        result = await state.meshcore.commands.get_contacts()

        if result.type == EventType.ERROR:
            return f"Get contacts failed: {result.payload}"

        contacts = result.payload

        # Check if payload is a string (error/status message from device)
        if isinstance(contacts, str):
            return contacts

        if not contacts:
            return "No contacts found"

        # Format contacts nicely
        output = "Contacts:\n"
        for i, contact in enumerate(contacts, 1):
            # Ensure contact is a dict before accessing attributes
            if isinstance(contact, dict):
                name = contact.get("name", "Unknown")
                key = contact.get("pubkey_prefix", "N/A")
                output += f"{i}. {name} (key: {key})\n"
            else:
                # Handle non-dict contact entries gracefully
                output += f"{i}. {contact}\n"

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
    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        return error

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
    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        return error

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

    # Get the Starlette app for streamable HTTP transport
    app = mcp.streamable_http_app()

    # Add middleware to handle trailing slash without redirecting
    # MCPO may append trailing slashes which causes 307 redirects by default
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class TrailingSlashMiddleware(BaseHTTPMiddleware):
        """Normalize trailing slashes to avoid 307 redirects."""
        async def dispatch(self, request: Request, call_next):
            # If path ends with /, remove it before processing
            if request.url.path.endswith("/") and request.url.path != "/":
                request.scope["path"] = request.url.path.rstrip("/")
            return await call_next(request)

    app.add_middleware(TrailingSlashMiddleware)

    # Run with uvicorn to support custom host and port
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
