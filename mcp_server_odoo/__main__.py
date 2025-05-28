"""Entry point for the mcp-server-odoo package."""

import asyncio
import sys
from typing import Optional

from dotenv import load_dotenv

from .server import OdooMCPServer


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the MCP server.
    
    Args:
        argv: Command line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load environment variables
    load_dotenv()
    
    # Parse basic help argument
    if argv is None:
        argv = sys.argv[1:]
    
    if "--help" in argv or "-h" in argv:
        print("MCP Server for Odoo")
        print("\nUsage: mcp-server-odoo [options]")
        print("\nOptions:")
        print("  -h, --help    Show this help message and exit")
        print("\nEnvironment variables:")
        print("  ODOO_URL      Odoo server URL (required)")
        print("  ODOO_DB       Odoo database name (required)")
        print("  ODOO_USERNAME Odoo username (required)")
        print("  ODOO_PASSWORD Odoo password (required)")
        print("  ODOO_API_KEY  Odoo API key (optional, alternative to password)")
        return 0
    
    try:
        # Create and run the server
        server = OdooMCPServer()
        asyncio.run(server.app.run_stdio_async())
        return 0
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())