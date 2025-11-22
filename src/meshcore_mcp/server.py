#!/usr/bin/env python3
"""
MeshCore MCP Server - HTTP Implementation

Provides MCP tools for interacting with MeshCore companion radio nodes.
Supports Serial, BLE, and TCP connections via HTTP/Streamable transport.
"""

import argparse
import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

# Configure logger
logger = logging.getLogger(__name__)

# Import meshcore library
try:
    from meshcore import MeshCore, EventType
except ImportError:
    print("Error: meshcore library not installed. Run: pip install meshcore", file=sys.stderr)
    sys.exit(1)

# Import our modules
from .state import state
from .message_handlers import handle_contact_message, handle_channel_message, handle_advertisement, cleanup_message_subscriptions

# Import tool registration functions
from .tools import connect, messages, device, time


# Initialize MCP server with FastMCP
mcp = FastMCP("meshcore-mcp")

# Register all tools
connect.register_tools(mcp)
messages.register_tools(mcp)
device.register_tools(mcp)
time.register_tools(mcp)


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
    logger.info(f"Attempting to connect to {serial_port} at {baud_rate} baud...")

    try:
        state.meshcore = await MeshCore.create_serial(serial_port, baud_rate, debug=debug)
        state.connection_type = "serial"
        state.connection_params = {"port": serial_port, "baud_rate": baud_rate}
        state.debug = debug

        logger.info(f"Successfully connected to MeshCore device on {serial_port}")
        logger.info(f"Connection state - Type: {state.connection_type}, Debug: {state.debug}")

        # Sync clock if requested
        if sync_clock:
            logger.info("Syncing device clock to system time...")
            try:
                import time
                current_time = int(time.time())
                dt = datetime.fromtimestamp(current_time)

                result = await state.meshcore.commands.set_time(current_time)

                if result.type == EventType.ERROR:
                    logger.warning(f"Clock sync failed: {result.payload}")
                else:
                    logger.info(f"Clock synced successfully to {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                logger.warning(f"Clock sync failed: {e}")
                import traceback
                traceback.print_exc(file=sys.stderr)

        return True

    except Exception as e:
        logger.error(f"Failed to connect to {serial_port}: {e}")
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
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG level) logging. Default is INFO level."
    )
    return parser.parse_args()


def main():
    """Main entry point for the MCP server."""
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )

    logger.info(f"Starting MeshCore MCP Server on {args.host}:{args.port}")
    logger.info(f"Server URL: http://{args.host}:{args.port}")

    # Get the Starlette app for streamable HTTP transport
    app = mcp.streamable_http_app()

    # Add middleware to handle trailing slash without redirecting
    # MCPO may append trailing slashes which causes 307 redirects by default
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

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
        logger.info(f"Auto-connect enabled for {args.serial_port}")

        # Save the original lifespan
        original_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app):
            """Combined lifespan that chains our startup with FastMCP's."""
            # Run FastMCP's startup first
            async with original_lifespan(app):
                # Now run our custom startup
                logger.info("Server starting, connecting to device...")
                connected = await startup_connect(args.serial_port, args.baud_rate, args.debug, args.sync_clock_on_startup)

                if not connected:
                    logger.error(f"FATAL: Failed to connect to {args.serial_port}")
                    logger.error("Shutting down server...")
                    # Force exit since we can't stop uvicorn gracefully from here
                    import os
                    os._exit(1)

                logger.info("Device connected. Starting message listening...")

                # Auto-start message listening
                try:
                    # Subscribe to contact messages
                    contact_sub = state.meshcore.subscribe(
                        EventType.CONTACT_MSG_RECV,
                        handle_contact_message
                    )
                    state.message_subscriptions.append(contact_sub)
                    logger.info("Subscribed to contact messages")

                    # Subscribe to channel messages
                    channel_sub = state.meshcore.subscribe(
                        EventType.CHANNEL_MSG_RECV,
                        handle_channel_message
                    )
                    state.message_subscriptions.append(channel_sub)
                    logger.info("Subscribed to channel messages")

                    # Subscribe to advertisements
                    advert_sub = state.meshcore.subscribe(
                        EventType.ADVERTISEMENT,
                        handle_advertisement
                    )
                    state.message_subscriptions.append(advert_sub)
                    logger.info("Subscribed to advertisements")

                    # Start auto message fetching
                    await state.meshcore.start_auto_message_fetching()
                    logger.info("Auto message fetching started")

                    state.is_listening = True
                    logger.info(f"Message listening active with {len(state.message_subscriptions)} subscriptions")

                except Exception as e:
                    logger.warning(f"Failed to start message listening: {e}")
                    import traceback
                    traceback.print_exc(file=sys.stderr)

                logger.info("Server ready.")

                try:
                    yield
                finally:
                    # Shutdown - runs before FastMCP's shutdown
                    logger.info("Cleaning up...")
                    if state.meshcore:
                        cleanup_message_subscriptions()
                        await state.meshcore.disconnect()
                        logger.info("Device disconnected.")

        # Replace with combined lifespan
        app.router.lifespan_context = combined_lifespan
    else:
        logger.info("No auto-connect configured. Use --serial-port to enable.")
        logger.info("Devices can be connected via meshcore_connect tool after server starts.")

    # Run with uvicorn to support custom host and port
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
