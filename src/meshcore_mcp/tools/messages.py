"""Message sending and listening tools."""

import sys
from typing import Optional
from collections import deque

try:
    from meshcore import EventType
except ImportError:
    EventType = None

from ..state import state
from ..connection import ensure_connected
from ..channels import parse_channel_input, get_channel_display_name
from ..message_handlers import handle_contact_message, handle_channel_message, cleanup_message_subscriptions


def register_tools(mcp):
    """Register message tools with the MCP server."""

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
