#!/usr/bin/env python3
"""
MeshCore MCP Server - HTTP Implementation

Provides MCP tools for interacting with MeshCore companion radio nodes.
Supports Serial, BLE, and TCP connections via HTTP/Streamable transport.
"""

import argparse
import asyncio
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import deque

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

    # Message listening state
    message_buffer: deque = deque(maxlen=1000)  # Store up to 1000 messages
    message_subscriptions: List = []  # Active subscriptions
    is_listening: bool = False


state = ServerState()


# Channel name mapping
CHANNEL_NAMES = {
    0: "General/Public",
    1: "Channel 1",
    2: "Channel 2",
    3: "Channel 3",
    4: "Channel 4",
    5: "Channel 5",
    6: "Channel 6",
    7: "Channel 7"
}

CHANNEL_NAME_MAP = {
    "general": 0,
    "public": 0,
    "main": 0,
    "default": 0
}


def parse_channel_input(channel_input: Optional[str | int]) -> tuple[Optional[int], Optional[str]]:
    """
    Parse channel input which can be either a channel number (int) or a channel name (str).

    Args:
        channel_input: Channel number (0-7) or common name like "general", "public", "main"

    Returns:
        Tuple of (channel_number, error_message). If error_message is not None, channel_number will be None.

    Examples:
        - parse_channel_input(0) -> (0, None)
        - parse_channel_input("general") -> (0, None)
        - parse_channel_input("public") -> (0, None)
        - parse_channel_input(5) -> (5, None)
        - parse_channel_input("invalid") -> (None, "Error: Unknown channel name...")
    """
    if channel_input is None:
        return (None, None)

    # If it's already an integer, validate it
    if isinstance(channel_input, int):
        if 0 <= channel_input <= 7:
            return (channel_input, None)
        else:
            return (None, f"Error: Channel number must be between 0 and 7, got {channel_input}")

    # If it's a string, try to parse it
    if isinstance(channel_input, str):
        # Try to parse as integer first
        try:
            channel_num = int(channel_input)
            if 0 <= channel_num <= 7:
                return (channel_num, None)
            else:
                return (None, f"Error: Channel number must be between 0 and 7, got {channel_num}")
        except ValueError:
            # Not a number, try to map from name
            channel_name_lower = channel_input.lower().strip()
            if channel_name_lower in CHANNEL_NAME_MAP:
                return (CHANNEL_NAME_MAP[channel_name_lower], None)
            else:
                available_names = ", ".join(f"'{name}'" for name in sorted(CHANNEL_NAME_MAP.keys()))
                return (None, f"Error: Unknown channel name '{channel_input}'. Use {available_names} or channel number 0-7")

    return (None, f"Error: Invalid channel input type: {type(channel_input)}")


def get_channel_display_name(channel_num: int) -> str:
    """
    Get a friendly display name for a channel number.

    Args:
        channel_num: Channel number (0-7)

    Returns:
        Friendly name like "0 (General/Public)" or "5 (Channel 5)"
    """
    if channel_num in CHANNEL_NAMES:
        return f"{channel_num} ({CHANNEL_NAMES[channel_num]})"
    return str(channel_num)


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


# Message handling callbacks
async def handle_contact_message(event):
    """Callback for handling received contact messages."""
    try:
        print(f"[DEBUG] Contact message event received: {event.type}", file=sys.stderr)
        print(f"[DEBUG] Event payload: {event.payload}", file=sys.stderr)

        message_data = {
            "type": "contact",
            "timestamp": datetime.now().isoformat(),
            "sender": event.payload.get("sender", "Unknown"),
            "sender_key": event.payload.get("sender_key", "N/A"),
            "pubkey_prefix": event.payload.get("pubkey_prefix", "N/A"),
            "text": event.payload.get("text", ""),
            "raw_payload": event.payload
        }
        state.message_buffer.append(message_data)
        print(f"[DEBUG] Contact message added to buffer. Buffer size: {len(state.message_buffer)}", file=sys.stderr)
        print(f"[DEBUG] Message from {message_data['sender']} (pubkey: {message_data['pubkey_prefix']}): {message_data['text']}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Error handling contact message: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


async def handle_channel_message(event):
    """Callback for handling received channel messages."""
    try:
        print(f"[DEBUG] Channel message event received: {event.type}", file=sys.stderr)
        print(f"[DEBUG] Event payload: {event.payload}", file=sys.stderr)

        message_data = {
            "type": "channel",
            "timestamp": datetime.now().isoformat(),
            "channel": event.payload.get("channel", "Unknown"),
            "sender": event.payload.get("sender", "Unknown"),
            "sender_key": event.payload.get("sender_key", "N/A"),
            "pubkey_prefix": event.payload.get("pubkey_prefix", "N/A"),
            "text": event.payload.get("text", ""),
            "raw_payload": event.payload
        }
        state.message_buffer.append(message_data)
        print(f"[DEBUG] Channel message added to buffer. Buffer size: {len(state.message_buffer)}", file=sys.stderr)
        print(f"[DEBUG] Message from {message_data['sender']} (pubkey: {message_data['pubkey_prefix']}) on channel {message_data['channel']}: {message_data['text']}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Error handling channel message: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


async def handle_advertisement(event):
    """Callback for handling advertisement events."""
    try:
        print(f"[DEBUG] Advertisement event received: {event.type}", file=sys.stderr)
        print(f"[DEBUG] Advertisement payload: {event.payload}", file=sys.stderr)

        # Advertisements contain info about nearby devices
        # This is useful for monitoring mesh network activity
    except Exception as e:
        print(f"[ERROR] Error handling advertisement: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


def cleanup_message_subscriptions():
    """Clean up all active message subscriptions."""
    print(f"[DEBUG] Cleaning up {len(state.message_subscriptions)} message subscriptions", file=sys.stderr)
    for subscription in state.message_subscriptions:
        try:
            subscription.unsubscribe()
            print(f"[DEBUG] Unsubscribed from: {subscription}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Error unsubscribing: {e}", file=sys.stderr)
    state.message_subscriptions.clear()
    state.is_listening = False
    print(f"[DEBUG] Message listening cleanup complete. Listening: {state.is_listening}", file=sys.stderr)


# Initialize MCP server with FastMCP
mcp = FastMCP("meshcore-mcp")


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


@mcp.tool()
async def meshcore_send_message(
    text: str,
    destination: Optional[str] = None,
    channel: Optional[str | int] = None
) -> str:
    """
    Send a text message to a contact or public channel.

    You must specify either 'destination' (for individual messages) or 'channel' (for channel messages),
    but not both.

    Args:
        text: Message text to send
        destination: Contact name or public key prefix (for individual messages)
        channel: Channel number (0-7) or channel name (for channel/broadcast messages).
                 Common channels:
                 - 0 or "general" or "public": Main public channel (most common default)
                 - 1-7: Additional channels as configured on the device

                 Accepted string names: "general", "public", "main", "default" (all map to channel 0)

                 If the user mentions sending to "general" or "public" without specifying a
                 channel number, use channel 0.

    Returns:
        Send status message with result

    Examples:
        - Send to individual: destination="Alice", channel=None
        - Send to general channel: destination=None, channel=0 or channel="general"
        - Send to channel 5: destination=None, channel=5
    """
    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        return error

    # Validate parameters
    if destination and channel is not None:
        return "Error: Specify either 'destination' or 'channel', not both"

    if not destination and channel is None:
        return "Error: Must specify either 'destination' or 'channel'"

    try:
        if channel is not None:
            # Parse channel input (handles both numbers and names)
            channel_num, parse_error = parse_channel_input(channel)
            if parse_error:
                return parse_error

            # Send to channel using dedicated channel message method
            result = await state.meshcore.commands.send_chan_msg(channel_num, text)
            channel_display = get_channel_display_name(channel_num)
            msg_type = f"channel {channel_display}"
        else:
            # Send to individual contact
            result = await state.meshcore.commands.send_msg(destination, text)
            msg_type = f"contact {destination}"

        if result.type == EventType.ERROR:
            return f"Send failed: {result.payload}"

        return f"Message sent to {msg_type}: \"{text}\"\nResult: {result.type.name}"

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


@mcp.tool()
async def meshcore_start_message_listening() -> str:
    """
    Start listening for incoming messages from contacts and channels.

    Messages will be stored in a buffer (up to 1000 messages) and can be retrieved
    using meshcore_get_messages.

    Returns:
        Status message indicating if listening started successfully
    """
    print(f"[DEBUG] meshcore_start_message_listening called", file=sys.stderr)
    print(f"[DEBUG] Current listening state: {state.is_listening}", file=sys.stderr)
    print(f"[DEBUG] Current buffer size: {len(state.message_buffer)}", file=sys.stderr)

    # Ensure connected (auto-reconnect if needed)
    error = await ensure_connected()
    if error:
        print(f"[DEBUG] Connection check failed: {error}", file=sys.stderr)
        return error

    print(f"[DEBUG] Connection verified. Connected: {state.meshcore.is_connected if state.meshcore else False}", file=sys.stderr)

    if state.is_listening:
        print(f"[DEBUG] Already listening with {len(state.message_subscriptions)} active subscriptions", file=sys.stderr)
        return "Already listening for messages"

    try:
        print(f"[DEBUG] Subscribing to CONTACT_MSG_RECV events", file=sys.stderr)
        # Subscribe to contact messages
        contact_sub = state.meshcore.subscribe(
            EventType.CONTACT_MSG_RECV,
            handle_contact_message
        )
        state.message_subscriptions.append(contact_sub)
        print(f"[DEBUG] Contact message subscription created: {contact_sub}", file=sys.stderr)

        print(f"[DEBUG] Subscribing to CHANNEL_MSG_RECV events", file=sys.stderr)
        # Subscribe to channel messages
        channel_sub = state.meshcore.subscribe(
            EventType.CHANNEL_MSG_RECV,
            handle_channel_message
        )
        state.message_subscriptions.append(channel_sub)
        print(f"[DEBUG] Channel message subscription created: {channel_sub}", file=sys.stderr)

        # Start auto message fetching
        print(f"[DEBUG] Starting auto message fetching", file=sys.stderr)
        await state.meshcore.start_auto_message_fetching()
        print(f"[DEBUG] Auto message fetching started", file=sys.stderr)

        state.is_listening = True
        print(f"[DEBUG] Message listening started successfully. Active subscriptions: {len(state.message_subscriptions)}", file=sys.stderr)

        return "Started listening for messages. Messages will be buffered and can be retrieved with meshcore_get_messages."

    except Exception as e:
        print(f"[ERROR] Failed to start message listening: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        cleanup_message_subscriptions()
        return f"Failed to start message listening: {str(e)}"


@mcp.tool()
async def meshcore_stop_message_listening() -> str:
    """
    Stop listening for incoming messages.

    This will unsubscribe from message events but will NOT clear the message buffer.
    Use meshcore_clear_messages to clear buffered messages.

    Returns:
        Status message
    """
    print(f"[DEBUG] meshcore_stop_message_listening called", file=sys.stderr)
    print(f"[DEBUG] Current listening state: {state.is_listening}", file=sys.stderr)
    print(f"[DEBUG] Active subscriptions: {len(state.message_subscriptions)}", file=sys.stderr)

    if not state.is_listening:
        print(f"[DEBUG] Not currently listening, nothing to stop", file=sys.stderr)
        return "Not currently listening for messages"

    try:
        # Stop auto message fetching
        if state.meshcore and state.meshcore.is_connected:
            print(f"[DEBUG] Stopping auto message fetching", file=sys.stderr)
            await state.meshcore.stop_auto_message_fetching()
            print(f"[DEBUG] Auto message fetching stopped", file=sys.stderr)

        # Clean up subscriptions
        cleanup_message_subscriptions()

        print(f"[DEBUG] Message listening stopped. Buffer size: {len(state.message_buffer)}", file=sys.stderr)
        return "Stopped listening for messages. Message buffer retained."

    except Exception as e:
        print(f"[ERROR] Error stopping message listening: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"Error stopping message listening: {str(e)}"


@mcp.tool()
async def meshcore_get_messages(
    limit: Optional[int] = None,
    clear_after_read: bool = False,
    message_type: Optional[str] = None
) -> str:
    """
    Retrieve messages from the message buffer.

    Args:
        limit: Maximum number of messages to return (most recent first). If None, returns all.
        clear_after_read: If True, clears the returned messages from the buffer
        message_type: Filter by message type ('contact' or 'channel'). If None, returns all.

    Returns:
        Formatted list of messages
    """
    print(f"[DEBUG] meshcore_get_messages called", file=sys.stderr)
    print(f"[DEBUG] Buffer size: {len(state.message_buffer)}", file=sys.stderr)
    print(f"[DEBUG] Parameters - limit: {limit}, clear_after_read: {clear_after_read}, message_type: {message_type}", file=sys.stderr)
    print(f"[DEBUG] Is listening: {state.is_listening}", file=sys.stderr)

    if not state.message_buffer:
        print(f"[DEBUG] No messages in buffer", file=sys.stderr)
        return "No messages in buffer"

    try:
        # Convert deque to list for easier manipulation
        messages = list(state.message_buffer)
        print(f"[DEBUG] Retrieved {len(messages)} messages from buffer", file=sys.stderr)

        # Filter by message type if specified
        if message_type:
            if message_type not in ["contact", "channel"]:
                print(f"[DEBUG] Invalid message_type: {message_type}", file=sys.stderr)
                return "Error: message_type must be 'contact' or 'channel'"
            messages = [msg for msg in messages if msg.get("type") == message_type]
            print(f"[DEBUG] Filtered to {len(messages)} {message_type} messages", file=sys.stderr)

        # Reverse to show most recent first
        messages.reverse()

        # Apply limit if specified
        if limit and limit > 0:
            messages = messages[:limit]
            print(f"[DEBUG] Limited to {len(messages)} messages", file=sys.stderr)

        if not messages:
            print(f"[DEBUG] No messages found after filtering", file=sys.stderr)
            return f"No {message_type + ' ' if message_type else ''}messages found"

        # Format output
        output = f"Messages ({len(messages)} total):\n"
        output += "=" * 60 + "\n"

        for i, msg in enumerate(messages, 1):
            msg_type = msg.get("type", "unknown").upper()
            timestamp = msg.get("timestamp", "Unknown")
            sender = msg.get("sender", "Unknown")
            pubkey_prefix = msg.get("pubkey_prefix", "N/A")
            text = msg.get("text", "")

            output += f"\n[{i}] {msg_type} MESSAGE\n"
            output += f"  Time: {timestamp}\n"
            output += f"  From: {sender}\n"

            # Show public key as a separate field for clarity
            if pubkey_prefix != "N/A":
                output += f"  Public Key: {pubkey_prefix}\n"

            if msg.get("type") == "channel":
                channel_num = msg.get('channel', 'Unknown')
                if isinstance(channel_num, int):
                    channel_display = get_channel_display_name(channel_num)
                else:
                    channel_display = str(channel_num)
                output += f"  Channel: {channel_display}\n"

            output += f"  Message: {text}\n"
            output += "-" * 60 + "\n"

        # Clear buffer if requested
        if clear_after_read:
            print(f"[DEBUG] Clearing messages from buffer", file=sys.stderr)
            if message_type:
                # Remove only the filtered messages
                before_count = len(state.message_buffer)
                state.message_buffer = deque(
                    [msg for msg in state.message_buffer if msg.get("type") != message_type],
                    maxlen=1000
                )
                print(f"[DEBUG] Removed {before_count - len(state.message_buffer)} {message_type} messages", file=sys.stderr)
            elif limit:
                # Remove the limited number of most recent messages
                removed = 0
                for _ in range(min(limit, len(messages))):
                    if state.message_buffer:
                        state.message_buffer.pop()
                        removed += 1
                print(f"[DEBUG] Removed {removed} most recent messages", file=sys.stderr)
            else:
                # Clear all
                cleared = len(state.message_buffer)
                state.message_buffer.clear()
                print(f"[DEBUG] Cleared all {cleared} messages", file=sys.stderr)
            output += "\n(Messages cleared from buffer)\n"

        print(f"[DEBUG] Returning {len(messages)} formatted messages. Buffer size now: {len(state.message_buffer)}", file=sys.stderr)
        return output

    except Exception as e:
        print(f"[ERROR] Error retrieving messages: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return f"Error retrieving messages: {str(e)}"


@mcp.tool()
async def meshcore_clear_messages() -> str:
    """
    Clear all messages from the message buffer.

    Returns:
        Status message with number of messages cleared
    """
    print(f"[DEBUG] meshcore_clear_messages called", file=sys.stderr)
    count = len(state.message_buffer)
    print(f"[DEBUG] Clearing {count} messages from buffer", file=sys.stderr)
    state.message_buffer.clear()
    print(f"[DEBUG] Buffer cleared. New size: {len(state.message_buffer)}", file=sys.stderr)
    return f"Cleared {count} message(s) from buffer"


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


async def startup_connect(serial_port: str, baud_rate: int, debug: bool, sync_clock: bool = False) -> bool:
    """
    Connect to MeshCore device on startup.

    Args:
        serial_port: Serial port path
        baud_rate: Baud rate for connection
        debug: Enable debug mode
        sync_clock: Sync device clock to system time after connecting

    Returns:
        True if connected successfully, False otherwise
    """
    print(f"[STARTUP] Attempting to connect to {serial_port} at {baud_rate} baud...", file=sys.stderr)

    try:
        state.meshcore = await MeshCore.create_serial(serial_port, baud_rate, debug=debug)
        state.connection_type = "serial"
        state.connection_params = {"port": serial_port, "baud_rate": baud_rate}
        state.debug = debug

        print(f"[STARTUP] Successfully connected to MeshCore device on {serial_port}", file=sys.stderr)
        print(f"[STARTUP] Connection state - Type: {state.connection_type}, Debug: {state.debug}", file=sys.stderr)

        # Sync clock if requested
        if sync_clock:
            print(f"[STARTUP] Syncing device clock to system time...", file=sys.stderr)
            try:
                import time
                current_time = int(time.time())
                dt = datetime.fromtimestamp(current_time)

                result = await state.meshcore.commands.set_time(current_time)

                if result.type == EventType.ERROR:
                    print(f"[STARTUP] WARNING: Clock sync failed: {result.payload}", file=sys.stderr)
                else:
                    print(f"[STARTUP] Clock synced successfully to {dt.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
            except Exception as e:
                print(f"[STARTUP] WARNING: Clock sync failed: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)

        return True

    except Exception as e:
        print(f"[STARTUP] Failed to connect to {serial_port}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return False


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
    parser.add_argument(
        "--serial-port",
        type=str,
        help="Serial port to auto-connect on startup (e.g., /dev/ttyUSB0). If specified, server will fail-fast if connection fails."
    )
    parser.add_argument(
        "--baud-rate",
        type=int,
        default=115200,
        help="Baud rate for serial connection (default: 115200)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for MeshCore connection"
    )
    parser.add_argument(
        "--sync-clock-on-startup",
        action="store_true",
        help="Automatically sync device clock to system time on startup (requires --serial-port)"
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
    from contextlib import asynccontextmanager

    class TrailingSlashMiddleware(BaseHTTPMiddleware):
        """Normalize trailing slashes to avoid 307 redirects."""
        async def dispatch(self, request: Request, call_next):
            # If path ends with /, remove it before processing
            if request.url.path.endswith("/") and request.url.path != "/":
                request.scope["path"] = request.url.path.rstrip("/")
            return await call_next(request)

    app.add_middleware(TrailingSlashMiddleware)

    # Add startup/shutdown handling via lifespan
    if args.serial_port:
        print(f"[STARTUP] Auto-connect enabled for {args.serial_port}", file=sys.stderr)

        # Save the original lifespan
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app):
            """Combined lifespan that chains our startup with FastMCP's."""
            # Run FastMCP's startup first
            async with original_lifespan(app):
                # Now run our custom startup
                print(f"[STARTUP] Server starting, connecting to device...", file=sys.stderr)
                connected = await startup_connect(args.serial_port, args.baud_rate, args.debug, args.sync_clock_on_startup)

                if not connected:
                    print(f"[STARTUP] FATAL: Failed to connect to {args.serial_port}", file=sys.stderr)
                    print(f"[STARTUP] Shutting down server...", file=sys.stderr)
                    # Force exit since we can't stop uvicorn gracefully from here
                    import os
                    os._exit(1)

                print(f"[STARTUP] Device connected. Starting message listening...", file=sys.stderr)

                # Auto-start message listening
                try:
                    # Subscribe to contact messages
                    contact_sub = state.meshcore.subscribe(
                        EventType.CONTACT_MSG_RECV,
                        handle_contact_message
                    )
                    state.message_subscriptions.append(contact_sub)
                    print(f"[STARTUP] Subscribed to contact messages", file=sys.stderr)

                    # Subscribe to channel messages
                    channel_sub = state.meshcore.subscribe(
                        EventType.CHANNEL_MSG_RECV,
                        handle_channel_message
                    )
                    state.message_subscriptions.append(channel_sub)
                    print(f"[STARTUP] Subscribed to channel messages", file=sys.stderr)

                    # Subscribe to advertisements
                    advert_sub = state.meshcore.subscribe(
                        EventType.ADVERTISEMENT,
                        handle_advertisement
                    )
                    state.message_subscriptions.append(advert_sub)
                    print(f"[STARTUP] Subscribed to advertisements", file=sys.stderr)

                    # Start auto message fetching
                    await state.meshcore.start_auto_message_fetching()
                    print(f"[STARTUP] Auto message fetching started", file=sys.stderr)

                    state.is_listening = True
                    print(f"[STARTUP] Message listening active with {len(state.message_subscriptions)} subscriptions", file=sys.stderr)

                except Exception as e:
                    print(f"[STARTUP] WARNING: Failed to start message listening: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)

                print(f"[STARTUP] Server ready.", file=sys.stderr)

                try:
                    yield
                finally:
                    # Shutdown - runs before FastMCP's shutdown
                    print(f"[SHUTDOWN] Cleaning up...", file=sys.stderr)
                    if state.meshcore:
                        cleanup_message_subscriptions()
                        await state.meshcore.disconnect()
                        print(f"[SHUTDOWN] Device disconnected.", file=sys.stderr)

        # Replace with combined lifespan
        app.router.lifespan_context = combined_lifespan
    else:
        print(f"[STARTUP] No auto-connect configured. Use --serial-port to enable.", file=sys.stderr)
        print(f"[STARTUP] Devices can be connected via meshcore_connect tool after server starts.", file=sys.stderr)

    # Run with uvicorn to support custom host and port
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
