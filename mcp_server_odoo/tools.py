"""MCP tool handlers for Odoo operations.

This module implements MCP tools for performing operations on Odoo data.
Tools are different from resources - they can have side effects and perform
actions like creating, updating, or deleting records.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .access_control import AccessControlError, AccessController
from .config import OdooConfig
from .error_handling import (
    NotFoundError,
    ValidationError,
)
from .logging_config import get_logger, perf_logger
from .odoo_connection import OdooConnection, OdooConnectionError

logger = get_logger(__name__)

# Legacy error type alias for backward compatibility
ToolError = ValidationError


class OdooToolHandler:
    """Handles MCP tool requests for Odoo operations."""

    def __init__(
        self,
        app: FastMCP,
        connection: OdooConnection,
        access_controller: AccessController,
        config: OdooConfig,
    ):
        """Initialize tool handler.

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

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all tool handlers with FastMCP."""

        @self.app.tool()
        async def search_records(
            model: str,
            domain: Optional[List[List[Any]]] = None,
            fields: Optional[List[str]] = None,
            limit: int = 10,
            offset: int = 0,
            order: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Search for records in an Odoo model.

            Args:
                model: The Odoo model name (e.g., 'res.partner')
                domain: Odoo domain filter (e.g., [['is_company', '=', True]])
                fields: List of fields to return (None for all fields)
                limit: Maximum number of records to return
                offset: Number of records to skip
                order: Sort order (e.g., 'name asc')

            Returns:
                Dictionary with 'records' list and 'total' count
            """
            return await self._handle_search_tool(model, domain, fields, limit, offset, order)

        @self.app.tool()
        async def get_record(
            model: str,
            record_id: int,
            fields: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            """Get a specific record by ID.

            Args:
                model: The Odoo model name (e.g., 'res.partner')
                record_id: The record ID
                fields: List of fields to return (None for all fields)

            Returns:
                Dictionary with record data
            """
            return await self._handle_get_record_tool(model, record_id, fields)

        @self.app.tool()
        async def list_models() -> List[Dict[str, Any]]:
            """List all models enabled for MCP access.

            Returns:
                List of model information dictionaries
            """
            return await self._handle_list_models_tool()

        @self.app.tool()
        async def create_record(
            model: str,
            values: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Create a new record in an Odoo model.

            Args:
                model: The Odoo model name (e.g., 'res.partner')
                values: Field values for the new record

            Returns:
                Dictionary with created record details
            """
            return await self._handle_create_record_tool(model, values)

        @self.app.tool()
        async def update_record(
            model: str,
            record_id: int,
            values: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Update an existing record.

            Args:
                model: The Odoo model name (e.g., 'res.partner')
                record_id: The record ID to update
                values: Field values to update

            Returns:
                Dictionary with updated record details
            """
            return await self._handle_update_record_tool(model, record_id, values)

        @self.app.tool()
        async def delete_record(
            model: str,
            record_id: int,
        ) -> Dict[str, Any]:
            """Delete a record.

            Args:
                model: The Odoo model name (e.g., 'res.partner')
                record_id: The record ID to delete

            Returns:
                Dictionary with deletion confirmation
            """
            return await self._handle_delete_record_tool(model, record_id)

    async def _handle_search_tool(
        self,
        model: str,
        domain: Optional[List[List[Any]]],
        fields: Optional[List[str]],
        limit: int,
        offset: int,
        order: Optional[str],
    ) -> Dict[str, Any]:
        """Handle search tool request."""
        try:
            with perf_logger.track_operation("tool_search", model=model):
                # Check model access
                self.access_controller.validate_model_access(model, "read")

                # Ensure we're connected
                if not self.connection.is_authenticated:
                    raise ValidationError("Not authenticated with Odoo")

                # Set defaults
                if domain is None:
                    domain = []
                if limit <= 0 or limit > self.config.max_limit:
                    limit = self.config.default_limit

                # Get total count
                total_count = self.connection.search_count(model, domain)

                # Search for records
                record_ids = self.connection.search(
                    model, domain, limit=limit, offset=offset, order=order
                )

                # Read records
                records = []
                if record_ids:
                    records = self.connection.read(model, record_ids, fields)

                return {
                    "records": records,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "model": model,
                }

        except AccessControlError as e:
            raise ToolError(f"Access denied: {e}") from e
        except OdooConnectionError as e:
            raise ToolError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Error in search_records tool: {e}")
            raise ToolError(f"Search failed: {e}") from e

    async def _handle_get_record_tool(
        self,
        model: str,
        record_id: int,
        fields: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Handle get record tool request."""
        try:
            with perf_logger.track_operation("tool_get_record", model=model):
                # Check model access
                self.access_controller.validate_model_access(model, "read")

                # Ensure we're connected
                if not self.connection.is_authenticated:
                    raise ValidationError("Not authenticated with Odoo")

                # Read the record
                records = self.connection.read(model, [record_id], fields)

                if not records:
                    raise ToolError(f"Record not found: {model} with ID {record_id}")

                return records[0]

        except NotFoundError as e:
            raise ToolError(str(e)) from e
        except AccessControlError as e:
            raise ToolError(f"Access denied: {e}") from e
        except OdooConnectionError as e:
            raise ToolError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Error in get_record tool: {e}")
            raise ToolError(f"Failed to get record: {e}") from e

    async def _handle_list_models_tool(self) -> List[Dict[str, Any]]:
        """Handle list models tool request."""
        try:
            with perf_logger.track_operation("tool_list_models"):
                models = self.access_controller.get_enabled_models()
                return models
        except Exception as e:
            logger.error(f"Error in list_models tool: {e}")
            raise ToolError(f"Failed to list models: {e}") from e

    async def _handle_create_record_tool(
        self,
        model: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle create record tool request."""
        try:
            with perf_logger.track_operation("tool_create_record", model=model):
                # Check model access
                self.access_controller.validate_model_access(model, "create")

                # Ensure we're connected
                if not self.connection.is_authenticated:
                    raise ValidationError("Not authenticated with Odoo")

                # Validate required fields
                if not values:
                    raise ValidationError("No values provided for record creation")

                # Create the record
                record_id = self.connection.create(model, values)

                # Read the created record to return full details
                records = self.connection.read(model, [record_id])
                if not records:
                    raise ToolError(f"Failed to read created record: {model} with ID {record_id}")

                return {
                    "success": True,
                    "record": records[0],
                    "message": f"Successfully created {model} record with ID {record_id}",
                }

        except AccessControlError as e:
            raise ToolError(f"Access denied: {e}") from e
        except OdooConnectionError as e:
            raise ToolError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Error in create_record tool: {e}")
            raise ToolError(f"Failed to create record: {e}") from e

    async def _handle_update_record_tool(
        self,
        model: str,
        record_id: int,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle update record tool request."""
        try:
            with perf_logger.track_operation("tool_update_record", model=model):
                # Check model access
                self.access_controller.validate_model_access(model, "write")

                # Ensure we're connected
                if not self.connection.is_authenticated:
                    raise ValidationError("Not authenticated with Odoo")

                # Validate input
                if not values:
                    raise ValidationError("No values provided for record update")

                # Check if record exists
                existing = self.connection.read(model, [record_id])
                if not existing:
                    raise NotFoundError(f"Record not found: {model} with ID {record_id}")

                # Update the record
                success = self.connection.write(model, [record_id], values)

                # Read the updated record to return full details
                records = self.connection.read(model, [record_id])
                if not records:
                    raise ToolError(f"Failed to read updated record: {model} with ID {record_id}")

                return {
                    "success": success,
                    "record": records[0],
                    "message": f"Successfully updated {model} record with ID {record_id}",
                }

        except NotFoundError as e:
            raise ToolError(str(e)) from e
        except AccessControlError as e:
            raise ToolError(f"Access denied: {e}") from e
        except OdooConnectionError as e:
            raise ToolError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Error in update_record tool: {e}")
            raise ToolError(f"Failed to update record: {e}") from e

    async def _handle_delete_record_tool(
        self,
        model: str,
        record_id: int,
    ) -> Dict[str, Any]:
        """Handle delete record tool request."""
        try:
            with perf_logger.track_operation("tool_delete_record", model=model):
                # Check model access
                self.access_controller.validate_model_access(model, "unlink")

                # Ensure we're connected
                if not self.connection.is_authenticated:
                    raise ValidationError("Not authenticated with Odoo")

                # Check if record exists
                existing = self.connection.read(model, [record_id])
                if not existing:
                    raise NotFoundError(f"Record not found: {model} with ID {record_id}")

                # Store some info about the record before deletion
                record_name = existing[0].get(
                    "name", existing[0].get("display_name", f"ID {record_id}")
                )

                # Delete the record
                success = self.connection.unlink(model, [record_id])

                return {
                    "success": success,
                    "deleted_id": record_id,
                    "deleted_name": record_name,
                    "message": f"Successfully deleted {model} record '{record_name}' (ID: {record_id})",
                }

        except NotFoundError as e:
            raise ToolError(str(e)) from e
        except AccessControlError as e:
            raise ToolError(f"Access denied: {e}") from e
        except OdooConnectionError as e:
            raise ToolError(f"Connection error: {e}") from e
        except Exception as e:
            logger.error(f"Error in delete_record tool: {e}")
            raise ToolError(f"Failed to delete record: {e}") from e


def register_tools(
    app: FastMCP,
    connection: OdooConnection,
    access_controller: AccessController,
    config: OdooConfig,
) -> OdooToolHandler:
    """Register all Odoo tools with the FastMCP app.

    Args:
        app: FastMCP application instance
        connection: Odoo connection instance
        access_controller: Access control instance
        config: Odoo configuration instance

    Returns:
        The tool handler instance
    """
    handler = OdooToolHandler(app, connection, access_controller, config)
    logger.info("Registered Odoo MCP tools")
    return handler
