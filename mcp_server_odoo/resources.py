"""MCP resource handlers for Odoo data access.

This module implements MCP resources for accessing Odoo data through
standardized URIs using FastMCP decorators.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import unquote
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .uri_schema import parse_uri, OdooOperation, URIError, build_uri, build_search_uri, build_record_uri
from .odoo_connection import OdooConnection, OdooConnectionError
from .access_control import AccessController, AccessControlError
from .formatters import RecordFormatter, DatasetFormatter
from .config import OdooConfig


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
    
    def __init__(self, app: FastMCP, connection: OdooConnection, 
                 access_controller: AccessController, config: OdooConfig):
        """Initialize resource handler.
        
        Args:
            app: FastMCP application instance
            connection: Odoo connection instance
            access_controller: Access control instance
            config: Odoo configuration instance
        """
        self.app = app
        self.connection = connection
        self.access_controller = access_controller
        self.config = config
        
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
        
        # Register search resource
        @self.app.resource("odoo://{model}/search?domain={domain}&fields={fields}&limit={limit}&offset={offset}&order={order}")
        async def search_records(model: str, domain: Optional[str] = None,
                                fields: Optional[str] = None,
                                limit: Optional[str] = None,
                                offset: Optional[str] = None,
                                order: Optional[str] = None) -> str:
            """Search for records using domain filters.
            
            Args:
                model: The Odoo model name (e.g., 'res.partner')
                domain: URL-encoded domain filter (e.g., "[['is_company','=',true]]")
                fields: Comma-separated list of fields to return
                limit: Maximum number of records to return
                offset: Number of records to skip (for pagination)
                order: Sort order (e.g., "name asc, id desc")
                
            Returns:
                Formatted search results with pagination metadata
            """
            # Convert string parameters to proper types
            limit_int = int(limit) if limit else None
            offset_int = int(offset) if offset else None
            return await self._handle_search(model, domain, fields, limit_int, offset_int, order)
    
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
    
    async def _handle_search(self, model: str, domain: Optional[str], 
                           fields: Optional[str], limit: Optional[int],
                           offset: Optional[int], order: Optional[str]) -> str:
        """Handle search request with domain filtering.
        
        Args:
            model: The Odoo model name
            domain: URL-encoded domain filter
            fields: Comma-separated list of fields
            limit: Maximum records to return
            offset: Pagination offset
            order: Sort order
            
        Returns:
            Formatted search results with pagination
            
        Raises:
            ResourcePermissionError: If access is denied
            ResourceError: For other errors
        """
        logger.info(f"Searching {model} with domain={domain}, limit={limit}, offset={offset}")
        
        try:
            # Check model access permissions
            try:
                self.access_controller.validate_model_access(model, 'read')
            except AccessControlError as e:
                logger.warning(f"Access denied for {model}.read: {e}")
                raise ResourcePermissionError(f"Access denied: {e}")
            
            # Ensure we're connected
            if not self.connection.is_authenticated:
                raise ResourceError("Not authenticated with Odoo")
            
            # Parse parameters
            parsed_domain = self._parse_domain(domain)
            fields_list = self._parse_fields(fields)
            limit_value = self._parse_limit(limit)
            offset_value = self._parse_offset(offset)
            order_value = self._parse_order(order)
            
            # Get total count for pagination
            total_count = self.connection.search_count(model, parsed_domain)
            
            # Perform search
            record_ids = self.connection.search(
                model, parsed_domain, 
                limit=limit_value, 
                offset=offset_value,
                order=order_value
            )
            
            # Read records if any found
            records = []
            if record_ids:
                records = self.connection.read(model, record_ids, fields_list)
            
            # Get field metadata for formatting
            try:
                fields_metadata = self.connection.fields_get(model)
            except Exception as e:
                logger.debug(f"Could not retrieve field metadata: {e}")
                fields_metadata = None
            
            # Format search results
            formatted_results = self._format_search_results(
                model, records, parsed_domain, fields_list,
                limit_value, offset_value, total_count, fields_metadata
            )
            
            logger.info(f"Search completed: found {len(records)} of {total_count} records")
            return formatted_results
            
        except (ResourcePermissionError, ResourceError):
            # Re-raise our custom exceptions
            raise
        except OdooConnectionError as e:
            logger.error(f"Connection error searching {model}: {e}")
            raise ResourceError(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching {model}: {e}")
            raise ResourceError(f"Failed to search records: {e}")
    
    def _parse_domain(self, domain: Optional[str]) -> List[Any]:
        """Parse domain parameter from URL-encoded string.
        
        Args:
            domain: URL-encoded domain string
            
        Returns:
            Parsed domain list
        """
        if not domain:
            return []
        
        try:
            # URL decode
            decoded = unquote(domain)
            # Parse JSON
            parsed = json.loads(decoded)
            
            if not isinstance(parsed, list):
                raise ValueError("Domain must be a list")
                
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid domain parameter: {domain} - {e}")
            return []
    
    def _parse_fields(self, fields: Optional[str]) -> Optional[List[str]]:
        """Parse fields parameter from comma-separated string.
        
        Args:
            fields: Comma-separated field names
            
        Returns:
            List of field names or None
        """
        if not fields:
            return None
            
        # Split and clean field names
        field_list = [f.strip() for f in fields.split(',') if f.strip()]
        return field_list if field_list else None
    
    def _parse_limit(self, limit: Optional[int]) -> int:
        """Parse and validate limit parameter.
        
        Args:
            limit: Limit value from request
            
        Returns:
            Valid limit value
        """
        if limit is None:
            return self.config.default_limit
            
        # Ensure it's within bounds
        if limit <= 0:
            return self.config.default_limit
        elif limit > self.config.max_limit:
            return self.config.max_limit
        else:
            return limit
    
    def _parse_offset(self, offset: Optional[int]) -> int:
        """Parse and validate offset parameter.
        
        Args:
            offset: Offset value from request
            
        Returns:
            Valid offset value
        """
        if offset is None or offset < 0:
            return 0
        return offset
    
    def _parse_order(self, order: Optional[str]) -> Optional[str]:
        """Parse and validate order parameter.
        
        Args:
            order: Order string (e.g., "name asc, id desc")
            
        Returns:
            Validated order string or None
        """
        if not order:
            return None
            
        # Basic validation - just ensure it's not empty after stripping
        cleaned = order.strip()
        return cleaned if cleaned else None
    
    def _format_search_results(self, model: str, records: List[Dict[str, Any]],
                              domain: List[Any], fields: Optional[List[str]],
                              limit: int, offset: int, total_count: int,
                              fields_metadata: Optional[Dict[str, Any]]) -> str:
        """Format search results with pagination metadata.
        
        Args:
            model: Model name
            records: List of record data
            domain: Applied domain filter
            fields: Requested fields
            limit: Records per page
            offset: Current offset
            total_count: Total matching records
            fields_metadata: Field metadata for formatting
            
        Returns:
            Formatted search results
        """
        # Calculate pagination info
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = offset + limit < total_count
        has_prev = offset > 0
        
        # Build pagination URIs
        next_uri = None
        prev_uri = None
        
        if has_next:
            # Convert domain back to JSON string for URI
            domain_str = json.dumps(domain) if domain else None
            fields_str = ','.join(fields) if fields else None
            next_uri = build_search_uri(
                model, domain=domain_str, fields=fields_str,
                limit=limit, offset=offset + limit
            )
        
        if has_prev:
            prev_offset = max(0, offset - limit)
            # Convert domain back to JSON string for URI
            domain_str = json.dumps(domain) if domain else None
            fields_str = ','.join(fields) if fields else None
            prev_uri = build_search_uri(
                model, domain=domain_str, fields=fields_str,
                limit=limit, offset=prev_offset
            )
        
        # Use DatasetFormatter for rich formatting
        formatter = DatasetFormatter(model)
        return formatter.format_search_results(
            records=records,
            total_count=total_count,
            limit=limit,
            offset=offset,
            domain=domain,
            fields=fields,
            fields_metadata=fields_metadata,
            next_uri=next_uri,
            prev_uri=prev_uri,
            current_page=current_page,
            total_pages=total_pages
        )
    
    def _format_record(self, model: str, record: Dict[str, Any]) -> str:
        """Format a record for MCP consumption.
        
        Args:
            model: The model name
            record: The record data
            
        Returns:
            Formatted text representation
        """
        # Get field metadata if available
        try:
            fields_metadata = self.connection.fields_get(model)
        except Exception as e:
            logger.debug(f"Could not retrieve field metadata: {e}")
            fields_metadata = None
        
        # Use RecordFormatter for rich formatting
        formatter = RecordFormatter(model)
        return formatter.format_record(record, fields_metadata)


def register_resources(app: FastMCP, connection: OdooConnection, 
                      access_controller: AccessController, config: OdooConfig) -> OdooResourceHandler:
    """Register all Odoo resources with the FastMCP app.
    
    Args:
        app: FastMCP application instance
        connection: Odoo connection instance
        access_controller: Access control instance
        config: Odoo configuration instance
        
    Returns:
        The resource handler instance
    """
    handler = OdooResourceHandler(app, connection, access_controller, config)
    logger.info("Registered Odoo MCP resources")
    return handler