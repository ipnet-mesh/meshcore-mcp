"""Time synchronization tools."""

from datetime import datetime

try:
    from meshcore import EventType
except ImportError:
    EventType = None

from ..state import state
from ..connection import ensure_connected


def register_tools(mcp):
    """Register time tools with the MCP server."""

    @mcp.tool()
    async def meshcore_get_time() -> str:
        """
        Get the current time from the MeshCore device.

        Returns:
            Device time information including Unix timestamp and formatted datetime
        """
        # Ensure connected (auto-reconnect if needed)
        error = await ensure_connected()
        if error:
            return error

        try:
            result = await state.meshcore.commands.get_time()

            if result.type == EventType.ERROR:
                return f"Get time failed: {result.payload}"

            # The payload should contain the Unix timestamp
            timestamp = result.payload

            # Format the response
            if isinstance(timestamp, int):
                # Convert Unix timestamp to human-readable format
                dt = datetime.fromtimestamp(timestamp)
                output = "Device Time:\n"
                output += f"  Unix Timestamp: {timestamp}\n"
                output += f"  Formatted: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                output += f"  ISO Format: {dt.isoformat()}\n"
            else:
                output = f"Device Time: {timestamp}"

            return output

        except Exception as e:
            return f"Get time failed: {str(e)}"

    @mcp.tool()
    async def meshcore_set_time(timestamp: int) -> str:
        """
        Set the device time to a specific Unix timestamp.

        Args:
            timestamp: Unix timestamp (seconds since epoch, e.g., 1732276800)

        Returns:
            Status message indicating success or failure

        Example:
            - Set to specific time: timestamp=1732276800 (Nov 22, 2024 12:00:00 UTC)
        """
        # Ensure connected (auto-reconnect if needed)
        error = await ensure_connected()
        if error:
            return error

        try:
            # Validate timestamp
            if timestamp < 0:
                return "Error: Timestamp must be a positive integer"

            # Convert timestamp to datetime for display
            dt = datetime.fromtimestamp(timestamp)

            result = await state.meshcore.commands.set_time(timestamp)

            if result.type == EventType.ERROR:
                return f"Set time failed: {result.payload}"

            return f"Device time set successfully to:\n  Unix Timestamp: {timestamp}\n  Datetime: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n  ISO Format: {dt.isoformat()}"

        except Exception as e:
            return f"Set time failed: {str(e)}"

    @mcp.tool()
    async def meshcore_sync_clock() -> str:
        """
        Synchronize the device clock to the current system time.

        This is a convenience function that gets the current system time and
        sets the device clock to match it.

        Returns:
            Status message with synchronization details
        """
        # Ensure connected (auto-reconnect if needed)
        error = await ensure_connected()
        if error:
            return error

        try:
            # Get current system time as Unix timestamp
            import time
            current_time = int(time.time())
            dt = datetime.fromtimestamp(current_time)

            # Set device time
            result = await state.meshcore.commands.set_time(current_time)

            if result.type == EventType.ERROR:
                return f"Clock sync failed: {result.payload}"

            return f"Device clock synchronized successfully!\n  System Time: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n  Unix Timestamp: {current_time}\n  ISO Format: {dt.isoformat()}"

        except Exception as e:
            return f"Clock sync failed: {str(e)}"
