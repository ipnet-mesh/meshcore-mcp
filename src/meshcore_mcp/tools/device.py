"""Device information and management tools."""

try:
    from meshcore import EventType
except ImportError:
    EventType = None

from ..state import state
from ..connection import ensure_connected


def register_tools(mcp):
    """Register device tools with the MCP server."""

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

    @mcp.tool()
    async def meshcore_send_advert(flood: bool = False) -> str:
        """
        Send an advertisement to the mesh network.

        Advertisements announce your device's presence to other nodes in the network.

        Args:
            flood: If True, the advertisement is broadcasted and repeated by all repeaters (multi-hop).
                   If False, it's a zero-hop broadcast only to immediate listeners (default: False).

        Returns:
            Status message with result

        Examples:
            - Zero-hop advert (immediate neighbors only): flood=False
            - Flooded advert (entire network via repeaters): flood=True
        """
        # Ensure connected (auto-reconnect if needed)
        error = await ensure_connected()
        if error:
            return error

        try:
            result = await state.meshcore.commands.send_advert(flood=flood)

            if result.type == EventType.ERROR:
                return f"Send advert failed: {result.payload}"

            advert_type = "flooded (multi-hop)" if flood else "zero-hop"
            return f"Advertisement sent successfully ({advert_type})\nResult: {result.type.name}"

        except Exception as e:
            return f"Send advert failed: {str(e)}"
