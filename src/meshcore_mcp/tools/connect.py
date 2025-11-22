"""Connection management tools."""

from typing import Optional

try:
    from meshcore import MeshCore
except ImportError:
    MeshCore = None

from ..state import state
from ..message_handlers import cleanup_message_subscriptions


def register_tools(mcp):
    """Register connection tools with the MCP server."""

    @mcp.tool()
    async def meshcore_connect(
        type: str,
        port: Optional[str] = "/dev/ttyUSB0",
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
        - 'serial': uses port (default: /dev/ttyUSB0), optional baud_rate (default: 115200)
        - 'ble': requires address (MAC), optional pin for pairing
        - 'tcp': requires host and port, optional auto_reconnect

        Args:
            type: Connection type ('serial', 'ble', or 'tcp')
            port: Serial port path (for serial, default: /dev/ttyUSB0) or TCP port number (for tcp)
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
            # Clean up message subscriptions first
            cleanup_message_subscriptions()
            state.message_buffer.clear()

            await state.meshcore.disconnect()
            conn_type = state.connection_type

            state.meshcore = None
            state.connection_type = None
            state.connection_params = {}
            state.debug = False

            return f"Disconnected from {conn_type} device"

        except Exception as e:
            return f"Disconnect failed: {str(e)}"
