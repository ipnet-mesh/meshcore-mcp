"""Message event handlers and subscription management."""

import logging
import sys
from datetime import datetime

from .state import state

# Configure logger
logger = logging.getLogger(__name__)


async def handle_contact_message(event):
    """Callback for handling received contact messages."""
    try:
        logger.debug(f"Contact message event received: {event.type}")
        logger.debug(f"Event payload: {event.payload}")

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
        logger.debug(f"Contact message added to buffer. Buffer size: {len(state.message_buffer)}")
        logger.debug(f"Message from {message_data['sender']} (pubkey: {message_data['pubkey_prefix']}): {message_data['text']}")
    except Exception as e:
        logger.error(f"Error handling contact message: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)


async def handle_channel_message(event):
    """Callback for handling received channel messages."""
    try:
        logger.debug(f"Channel message event received: {event.type}")
        logger.debug(f"Event payload: {event.payload}")

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
        logger.debug(f"Channel message added to buffer. Buffer size: {len(state.message_buffer)}")
        logger.debug(f"Message from {message_data['sender']} (pubkey: {message_data['pubkey_prefix']}) on channel {message_data['channel']}: {message_data['text']}")
    except Exception as e:
        logger.error(f"Error handling channel message: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)


async def handle_advertisement(event):
    """Callback for handling advertisement events."""
    try:
        logger.debug(f"Advertisement event received: {event.type}")
        logger.debug(f"Advertisement payload: {event.payload}")

        # Advertisements contain info about nearby devices
        # This is useful for monitoring mesh network activity
    except Exception as e:
        logger.error(f"Error handling advertisement: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)


def cleanup_message_subscriptions():
    """Clean up all active message subscriptions."""
    logger.debug(f"Cleaning up {len(state.message_subscriptions)} message subscriptions")
    for subscription in state.message_subscriptions:
        try:
            subscription.unsubscribe()
            logger.debug(f"Unsubscribed from: {subscription}")
        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
    state.message_subscriptions.clear()
    state.is_listening = False
    logger.debug(f"Message listening cleanup complete. Listening: {state.is_listening}")
