"""Message event handlers and subscription management."""

import sys
from datetime import datetime

from .state import state


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
