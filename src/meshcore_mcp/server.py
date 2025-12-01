#!/usr/bin/env python3
"""
MeshCore MCP Server - HTTP Implementation

Provides MCP tools for interacting with MeshCore API.
Supports message and advertisement operations via HTTP/Streamable transport.
"""

import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

from .state import state
from .tools import messages, advertisements

# Configure logger
logger = logging.getLogger(__name__)

# Initialize MCP server with FastMCP
mcp = FastMCP("meshcore-mcp")

# Register all tools
messages.register_tools(mcp)
advertisements.register_tools(mcp)


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
        "--api-url",
        type=str,
        help="MeshCore API URL (e.g., http://localhost:9000). Can also be set via MESHCORE_API_URL env var."
    )
    parser.add_argument(
        "--api-token",
        type=str,
        help="MeshCore API bearer token for authentication. Can also be set via MESHCORE_API_TOKEN env var."
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

    # Configure API connection
    state.configure(api_url=args.api_url, api_token=args.api_token)

    if state.is_configured:
        logger.info(f"API URL configured: {state.api_url}")
        if state.api_token:
            logger.info("API token configured (authentication enabled)")
        else:
            logger.info("No API token configured (public API mode)")
    else:
        logger.warning("No API URL configured. Set --api-url or MESHCORE_API_URL environment variable.")
        logger.warning("Tools will return errors until API is configured.")

    logger.info(f"Starting MeshCore MCP Server on {args.host}:{args.port}")
    logger.info(f"Server URL: http://{args.host}:{args.port}")

    # Get the Starlette app for streamable HTTP transport
    app = mcp.streamable_http_app()

    # Add middleware to handle trailing slash without redirecting
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class TrailingSlashMiddleware(BaseHTTPMiddleware):
        """Normalize trailing slashes to avoid 307 redirects."""
        async def dispatch(self, request: Request, call_next):
            if request.url.path.endswith("/") and request.url.path != "/":
                request.scope["path"] = request.url.path.rstrip("/")
            return await call_next(request)

    app.add_middleware(TrailingSlashMiddleware)

    logger.info("Server ready.")

    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
