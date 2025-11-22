"""Connection management utilities."""

from typing import Optional

try:
    from meshcore import MeshCore
except ImportError:
    MeshCore = None

from .state import state


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
