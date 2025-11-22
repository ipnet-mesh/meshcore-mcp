"""Server state management for MeshCore MCP Server."""

from typing import Optional, List
from collections import deque

try:
    from meshcore import MeshCore
except ImportError:
    MeshCore = None


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


# Global state instance
state = ServerState()
