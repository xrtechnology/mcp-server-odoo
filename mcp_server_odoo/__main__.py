"""Entry point for the mcp-server-odoo package.

This module provides the command-line interface for running the
Odoo MCP server via uvx or direct execution.
"""

import asyncio
import logging
import sys
from typing import Optional

from dotenv import load_dotenv

from .config import load_config
from .server import SERVER_VERSION, OdooMCPServer


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the MCP server.

    This function handles command-line arguments, loads configuration,
    and runs the MCP server with stdio transport.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load environment variables from .env file
    load_dotenv()

    # Parse command line arguments
    if argv is None:
        argv = sys.argv[1:]

    # Handle help flag
    if "--help" in argv or "-h" in argv:
        print("Odoo MCP Server - Model Context Protocol server for Odoo ERP", file=sys.stderr)
        print("\nUsage: mcp-server-odoo [options]", file=sys.stderr)
        print("\nOptions:", file=sys.stderr)
        print("  -h, --help         Show this help message and exit", file=sys.stderr)
        print("  --version          Show version information", file=sys.stderr)
        print("\nEnvironment variables:", file=sys.stderr)
        print("  ODOO_URL           Odoo server URL (required)", file=sys.stderr)
        print("  ODOO_API_KEY       Odoo API key (preferred authentication)", file=sys.stderr)
        print("  ODOO_USER          Odoo username (fallback if no API key)", file=sys.stderr)
        print("  ODOO_PASSWORD      Odoo password (required with username)", file=sys.stderr)
        print("  ODOO_DB            Odoo database name (auto-detected if not set)", file=sys.stderr)
        print("\nOptional environment variables:", file=sys.stderr)
        print("  ODOO_MCP_LOG_LEVEL    Log level (DEBUG, INFO, WARNING, ERROR)", file=sys.stderr)
        print("  ODOO_MCP_DEFAULT_LIMIT Default record limit (default: 10)", file=sys.stderr)
        print("  ODOO_MCP_MAX_LIMIT     Maximum record limit (default: 100)", file=sys.stderr)
        print(
            "\nFor more information, visit: https://github.com/ivnvxd/mcp-server-odoo",
            file=sys.stderr,
        )
        return 0

    # Handle version flag
    if "--version" in argv:
        print(f"odoo-mcp-server v{SERVER_VERSION}", file=sys.stderr)
        return 0

    try:
        # Load configuration from environment
        config = load_config()

        # Create server instance
        server = OdooMCPServer(config)

        # Run the server with stdio transport
        # This is the standard way to run MCP servers with uvx
        asyncio.run(server.run_stdio())

        return 0

    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        print("\nServer stopped by user", file=sys.stderr)
        return 0

    except ValueError as e:
        # Configuration errors
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nPlease check your environment variables or .env file", file=sys.stderr)
        return 1

    except Exception as e:
        # Other errors
        logging.error(f"Server error: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


# Entry point for module execution
if __name__ == "__main__":
    sys.exit(main())
