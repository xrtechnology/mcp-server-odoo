"""MCP Server implementation for Odoo."""

from mcp.server import FastMCP

# Initialize FastMCP instance
mcp = FastMCP(
    name="odoo-mcp-server",
    instructions="MCP server for accessing and managing Odoo ERP data"
)


class OdooMCPServer:
    """Main MCP server class for Odoo integration."""
    
    def __init__(self):
        """Initialize the Odoo MCP server."""
        self.app = mcp
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP handlers and tools."""
        # Tools will be added here
        pass