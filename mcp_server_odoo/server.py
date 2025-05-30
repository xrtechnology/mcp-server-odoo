"""MCP Server implementation for Odoo.

This module provides the FastMCP server that exposes Odoo data
and functionality through the Model Context Protocol.
"""

import logging
from typing import Optional

from mcp.server import FastMCP

from .config import get_config, OdooConfig
from .odoo_connection import OdooConnection, OdooConnectionError

# Set up logging
logger = logging.getLogger(__name__)

# Server version
SERVER_VERSION = "0.1.0"


class OdooMCPServer:
    """Main MCP server class for Odoo integration.
    
    This class manages the FastMCP server instance and maintains
    the connection to Odoo. The server lifecycle is managed by
    establishing connection before starting and cleaning up on exit.
    """
    
    def __init__(self, config: Optional[OdooConfig] = None):
        """Initialize the Odoo MCP server.
        
        Args:
            config: Optional OdooConfig instance. If not provided,
                   will load from environment variables.
        """
        # Load configuration
        self.config = config or get_config()
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize connection (will be created on startup)
        self.connection: Optional[OdooConnection] = None
        
        # Create FastMCP instance with server metadata
        self.app = FastMCP(
            name="odoo-mcp-server",
            instructions="MCP server for accessing and managing Odoo ERP data through the Model Context Protocol"
        )
        
        # Set up MCP handlers (resources, tools, etc.)
        self._setup_handlers()
        
        logger.info(f"Initialized Odoo MCP Server v{SERVER_VERSION}")
    
    def _ensure_connection(self):
        """Ensure connection to Odoo is established.
        
        Raises:
            OdooConnectionError: If connection fails
        """
        if not self.connection:
            logger.info("Establishing connection to Odoo...")
            self.connection = OdooConnection(self.config)
            
            if not self.connection.test_connection():
                raise OdooConnectionError("Failed to connect to Odoo")
            
            logger.info(f"Successfully connected to Odoo at {self.config.url}")
    
    def _cleanup_connection(self):
        """Clean up Odoo connection."""
        if self.connection:
            try:
                logger.info("Closing Odoo connection...")
                self.connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                # Always clear connection reference
                self.connection = None
    
    def _setup_handlers(self):
        """Set up MCP handlers for resources, tools, and prompts.
        
        This method will be extended in later phases to add:
        - Resource handlers for Odoo data access
        - Tool handlers for Odoo operations
        - Prompt handlers for guided workflows
        """
        # Resources will be added in Step 10.2
        # Tools will be added in Phase 3
        # Prompts will be added in Phase 4
        pass
    
    async def run_stdio(self):
        """Run the server using stdio transport.
        
        This is the main entry point for running the server
        with standard input/output transport (used by uvx).
        """
        try:
            # Establish connection before starting server
            self._ensure_connection()
            
            logger.info("Starting MCP server with stdio transport...")
            await self.app.run_stdio_async()
            
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
        finally:
            # Always cleanup connection
            self._cleanup_connection()
    
    def run_stdio_sync(self):
        """Synchronous wrapper for run_stdio.
        
        This is provided for compatibility with synchronous code.
        """
        import asyncio
        asyncio.run(self.run_stdio())
    
    def get_capabilities(self):
        """Get server capabilities.
        
        Returns:
            Dict with server capabilities
        """
        return {
            "capabilities": {
                "resources": True,  # Will expose Odoo data as resources
                "tools": False,     # Tools will be added in later phases
                "prompts": False    # Prompts will be added in later phases
            }
        }