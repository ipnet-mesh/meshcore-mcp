"""Message sending and listening tools."""

import logging
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

# Configure logger
logger = logging.getLogger(__name__)


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
        logger.debug("meshcore_start_message_listening called")
        logger.debug(f"Current listening state: {state.is_listening}")
        logger.debug(f"Current buffer size: {len(state.message_buffer)}")

        # Ensure connected (auto-reconnect if needed)
        error = await ensure_connected()
        if error:
            logger.debug(f"Connection check failed: {error}")
            return error

        logger.debug(f"Connection verified. Connected: {state.meshcore.is_connected if state.meshcore else False}")

        if state.is_listening:
            logger.debug(f"Already listening with {len(state.message_subscriptions)} active subscriptions")
            return "Already listening for messages"

        try:
            logger.debug("Subscribing to CONTACT_MSG_RECV events")
            # Subscribe to contact messages
            contact_sub = state.meshcore.subscribe(
                EventType.CONTACT_MSG_RECV,
                handle_contact_message
            )
            state.message_subscriptions.append(contact_sub)
            logger.debug(f"Contact message subscription created: {contact_sub}")

            logger.debug("Subscribing to CHANNEL_MSG_RECV events")
            # Subscribe to channel messages
            channel_sub = state.meshcore.subscribe(
                EventType.CHANNEL_MSG_RECV,
                handle_channel_message
            )
            state.message_subscriptions.append(channel_sub)
            logger.debug(f"Channel message subscription created: {channel_sub}")

            # Start auto message fetching
            logger.debug("Starting auto message fetching")
            await state.meshcore.start_auto_message_fetching()
            logger.debug("Auto message fetching started")

            state.is_listening = True
            logger.debug(f"Message listening started successfully. Active subscriptions: {len(state.message_subscriptions)}")

            return "Started listening for messages. Messages will be buffered and can be retrieved with meshcore_get_messages."

        except Exception as e:
            logger.error(f"Failed to start message listening: {e}")
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
        logger.debug("meshcore_stop_message_listening called")
        logger.debug(f"Current listening state: {state.is_listening}")
        logger.debug(f"Active subscriptions: {len(state.message_subscriptions)}")

        if not state.is_listening:
            logger.debug("Not currently listening, nothing to stop")
            return "Not currently listening for messages"

        try:
            # Stop auto message fetching
            if state.meshcore and state.meshcore.is_connected:
                logger.debug("Stopping auto message fetching")
                await state.meshcore.stop_auto_message_fetching()
                logger.debug("Auto message fetching stopped")

            # Clean up subscriptions
            cleanup_message_subscriptions()

            logger.debug(f"Message listening stopped. Buffer size: {len(state.message_buffer)}")
            return "Stopped listening for messages. Message buffer retained."

        except Exception as e:
            logger.error(f"Error stopping message listening: {e}")
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
        logger.debug("meshcore_get_messages called")
        logger.debug(f"Buffer size: {len(state.message_buffer)}")
        logger.debug(f"Parameters - limit: {limit}, clear_after_read: {clear_after_read}, message_type: {message_type}")
        logger.debug(f"Is listening: {state.is_listening}")

        if not state.message_buffer:
            logger.debug("No messages in buffer")
            return "No messages in buffer"

        try:
            # Convert deque to list for easier manipulation
            messages = list(state.message_buffer)
            logger.debug(f"Retrieved {len(messages)} messages from buffer")

            # Filter by message type if specified
            if message_type:
                if message_type not in ["contact", "channel"]:
                    logger.debug(f"Invalid message_type: {message_type}")
                    return "Error: message_type must be 'contact' or 'channel'"
                messages = [msg for msg in messages if msg.get("type") == message_type]
                logger.debug(f"Filtered to {len(messages)} {message_type} messages")

            # Reverse to show most recent first
            messages.reverse()

            # Apply limit if specified
            if limit and limit > 0:
                messages = messages[:limit]
                logger.debug(f"Limited to {len(messages)} messages")

            if not messages:
                logger.debug("No messages found after filtering")
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
                logger.debug("Clearing messages from buffer")
                if message_type:
                    # Remove only the filtered messages
                    before_count = len(state.message_buffer)
                    state.message_buffer = deque(
                        [msg for msg in state.message_buffer if msg.get("type") != message_type],
                        maxlen=1000
                    )
                    logger.debug(f"Removed {before_count - len(state.message_buffer)} {message_type} messages")
                elif limit:
                    # Remove the limited number of most recent messages
                    removed = 0
                    for _ in range(min(limit, len(messages))):
                        if state.message_buffer:
                            state.message_buffer.pop()
                            removed += 1
                    logger.debug(f"Removed {removed} most recent messages")
                else:
                    # Clear all
                    cleared = len(state.message_buffer)
                    state.message_buffer.clear()
                    logger.debug(f"Cleared all {cleared} messages")
                output += "\n(Messages cleared from buffer)\n"

            logger.debug(f"Returning {len(messages)} formatted messages. Buffer size now: {len(state.message_buffer)}")
            return output

        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
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
        logger.debug("meshcore_clear_messages called")
        count = len(state.message_buffer)
        logger.debug(f"Clearing {count} messages from buffer")
        state.message_buffer.clear()
        logger.debug(f"Buffer cleared. New size: {len(state.message_buffer)}")
        return f"Cleared {count} message(s) from buffer"
