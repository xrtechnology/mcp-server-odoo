"""MCP resource handlers for Odoo data access.

This module implements MCP resources for accessing Odoo data through
standardized URIs using FastMCP decorators.
"""

import logging
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .uri_schema import parse_uri, OdooOperation, URIError
from .odoo_connection import OdooConnection, OdooConnectionError
from .access_control import AccessController, AccessControlError


logger = logging.getLogger(__name__)


class ResourceError(Exception):
    """Base exception for resource operations."""
    pass


class ResourceNotFoundError(ResourceError):
    """Exception raised when a resource is not found."""
    pass


class ResourcePermissionError(ResourceError):
    """Exception raised when access to a resource is denied."""
    pass


class OdooResourceHandler:
    """Handles MCP resource requests for Odoo data."""
    
    def __init__(self, app: FastMCP, connection: OdooConnection, access_controller: AccessController):
        """Initialize resource handler.
        
        Args:
            app: FastMCP application instance
            connection: Odoo connection instance
            access_controller: Access control instance
        """
        self.app = app
        self.connection = connection
        self.access_controller = access_controller
        
        # Register resources
        self._register_resources()
    
    def _register_resources(self):
        """Register all resource handlers with FastMCP."""
        # Register record retrieval resource
        @self.app.resource("odoo://{model}/record/{record_id}")
        async def get_record(model: str, record_id: str) -> str:
            """Retrieve a specific record from Odoo.
            
            Args:
                model: The Odoo model name (e.g., 'res.partner')
                record_id: The record ID to retrieve
                
            Returns:
                Formatted record data as text
            """
            return await self._handle_record_retrieval(model, record_id)
    
    async def _handle_record_retrieval(self, model: str, record_id: str) -> str:
        """Handle record retrieval request.
        
        Args:
            model: The Odoo model name
            record_id: The record ID to retrieve
            
        Returns:
            Formatted record data
            
        Raises:
            ResourceNotFoundError: If record doesn't exist
            ResourcePermissionError: If access is denied
            ResourceError: For other errors
        """
        logger.info(f"Retrieving record: {model}/{record_id}")
        
        try:
            # Validate record ID
            try:
                record_id_int = int(record_id)
                if record_id_int <= 0:
                    raise ValueError("Record ID must be positive")
            except ValueError as e:
                raise ResourceError(f"Invalid record ID '{record_id}': {e}")
            
            # Check model access permissions
            try:
                self.access_controller.validate_model_access(model, 'read')
            except AccessControlError as e:
                logger.warning(f"Access denied for {model}.read: {e}")
                raise ResourcePermissionError(f"Access denied: {e}")
            
            # Ensure we're connected
            if not self.connection.is_authenticated:
                raise ResourceError("Not authenticated with Odoo")
            
            # Search for the record to check if it exists
            record_ids = self.connection.search(model, [('id', '=', record_id_int)])
            
            if not record_ids:
                raise ResourceNotFoundError(
                    f"Record not found: {model} with ID {record_id} does not exist"
                )
            
            # Read the record
            records = self.connection.read(model, record_ids)
            
            if not records:
                raise ResourceNotFoundError(
                    f"Record not found: {model} with ID {record_id} does not exist"
                )
            
            record = records[0]
            
            # Format the record data
            formatted_data = self._format_record(model, record)
            
            logger.info(f"Successfully retrieved record: {model}/{record_id}")
            return formatted_data
            
        except (ResourceNotFoundError, ResourcePermissionError, ResourceError):
            # Re-raise our custom exceptions
            raise
        except OdooConnectionError as e:
            logger.error(f"Connection error retrieving {model}/{record_id}: {e}")
            raise ResourceError(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving {model}/{record_id}: {e}")
            raise ResourceError(f"Failed to retrieve record: {e}")
    
    def _format_record(self, model: str, record: Dict[str, Any]) -> str:
        """Format a record for MCP consumption.
        
        Args:
            model: The model name
            record: The record data
            
        Returns:
            Formatted text representation
        """
        lines = []
        lines.append(f"Resource: {model}/record/{record.get('id', 'unknown')}")
        lines.append("=" * 50)
        
        # Get display name if available
        if 'display_name' in record:
            lines.append(f"Name: {record['display_name']}")
        elif 'name' in record:
            lines.append(f"Name: {record['name']}")
        
        # Add ID
        lines.append(f"ID: {record.get('id', 'unknown')}")
        
        # Add other fields
        skip_fields = {'id', 'name', 'display_name', '__last_update'}
        
        for field, value in sorted(record.items()):
            if field in skip_fields:
                continue
            
            # Format the field value
            formatted_value = self._format_field_value(field, value)
            if formatted_value is not None:
                lines.append(f"{field}: {formatted_value}")
        
        return "\n".join(lines)
    
    def _format_field_value(self, field: str, value: Any) -> Optional[str]:
        """Format a field value for display.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Formatted string or None to skip the field
        """
        if value is None or value is False:
            return "Not set"
        
        # Handle many2one fields (tuple of [id, name])
        if isinstance(value, tuple) and len(value) == 2:
            return f"{value[1]} (ID: {value[0]})"
        
        # Handle one2many and many2many fields (list of IDs)
        if isinstance(value, list):
            if not value:
                return "None"
            # For now, just show the count
            return f"{len(value)} record(s)"
        
        # Handle other types
        return str(value)


def register_resources(app: FastMCP, connection: OdooConnection, 
                      access_controller: AccessController) -> OdooResourceHandler:
    """Register all Odoo resources with the FastMCP app.
    
    Args:
        app: FastMCP application instance
        connection: Odoo connection instance
        access_controller: Access control instance
        
    Returns:
        The resource handler instance
    """
    handler = OdooResourceHandler(app, connection, access_controller)
    logger.info("Registered Odoo MCP resources")
    return handler