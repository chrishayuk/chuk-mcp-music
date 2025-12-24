#!/usr/bin/env python3
"""
Entry point for the CHUK Music MCP Server.

This module provides the main entry point for the MCP server,
supporting multiple transport modes (stdio, http).
"""

import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point with transport detection."""
    parser = argparse.ArgumentParser(description="CHUK Music MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port (only for http transport)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Import after argument parsing to avoid issues
    from chuk_mcp_music.async_server import mcp

    if args.transport == "stdio":
        logger.info("Starting CHUK Music MCP Server (stdio)")
        asyncio.run(mcp.run_stdio())
    else:
        logger.info(f"Starting CHUK Music MCP Server (http:{args.port})")
        asyncio.run(mcp.run_http(port=args.port))


if __name__ == "__main__":
    main()
