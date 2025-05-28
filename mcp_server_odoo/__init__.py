"""MCP Server for Odoo - Model Context Protocol server for Odoo ERP systems."""

__version__ = "0.1.0"
__author__ = "Andrey Ivanov"
__license__ = "MPL-2.0"

from .server import OdooMCPServer

__all__ = ["OdooMCPServer", "__version__"]