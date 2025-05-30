"""MCP Server implementation for Odoo.

This module provides the FastMCP server that exposes Odoo data
and functionality through the Model Context Protocol.
"""

import logging
from typing import Optional

from mcp.server import FastMCP

from .config import get_config, OdooConfig
from .odoo_connection import OdooConnection, OdooConnectionError
from .access_control import AccessController
from .resources import register_resources

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
        
        # Initialize connection and access controller (will be created on startup)
        self.connection: Optional[OdooConnection] = None
        self.access_controller: Optional[AccessController] = None
        self.resource_handler = None
        
        # Create FastMCP instance with server metadata
        self.app = FastMCP(
            name="odoo-mcp-server",
            instructions="MCP server for accessing and managing Odoo ERP data through the Model Context Protocol"
        )
        
        logger.info(f"Initialized Odoo MCP Server v{SERVER_VERSION}")
    
    def _ensure_connection(self):
        """Ensure connection to Odoo is established.
        
        Raises:
            OdooConnectionError: If connection fails
        """
        if not self.connection:
            logger.info("Establishing connection to Odoo...")
            self.connection = OdooConnection(self.config)
            
            # Connect and authenticate
            self.connection.connect()
            self.connection.authenticate()
            
            logger.info(f"Successfully connected to Odoo at {self.config.url}")
            
            # Initialize access controller
            self.access_controller = AccessController(self.config)
    
    def _cleanup_connection(self):
        """Clean up Odoo connection."""
        if self.connection:
            try:
                logger.info("Closing Odoo connection...")
                self.connection.disconnect()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                # Always clear connection reference
                self.connection = None
                self.access_controller = None
                self.resource_handler = None
    
    def _setup_handlers(self):
        """Set up MCP handlers for resources, tools, and prompts.
        
        This method will be extended in later phases to add:
        - Resource handlers for Odoo data access
        - Tool handlers for Odoo operations
        - Prompt handlers for guided workflows
        """
        # Tools will be added in Phase 3
        # Prompts will be added in Phase 4
        pass
    
    def _register_resources(self):
        """Register resource handlers after connection is established."""
        if self.connection and self.access_controller:
            self.resource_handler = register_resources(
                self.app,
                self.connection,
                self.access_controller,
                self.config
            )
            logger.info("Registered MCP resources")
    
    async def run_stdio(self):
        """Run the server using stdio transport.
        
        This is the main entry point for running the server
        with standard input/output transport (used by uvx).
        """
        try:
            # Establish connection before starting server
            self._ensure_connection()
            
            # Register resources after connection is established
            self._register_resources()
            
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