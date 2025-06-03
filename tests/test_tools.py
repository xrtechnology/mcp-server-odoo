"""Test suite for MCP tools functionality."""

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_server_odoo.access_control import AccessControlError, AccessController
from mcp_server_odoo.config import OdooConfig
from mcp_server_odoo.error_handling import (
    ValidationError,
)
from mcp_server_odoo.odoo_connection import OdooConnection, OdooConnectionError
from mcp_server_odoo.tools import OdooToolHandler, register_tools


class TestOdooToolHandler:
    """Test cases for OdooToolHandler class."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock FastMCP app."""
        app = MagicMock(spec=FastMCP)
        # Store registered tools
        app._tools = {}

        def tool_decorator():
            def decorator(func):
                # Store the function in our tools dict
                app._tools[func.__name__] = func
                return func

            return decorator

        app.tool = tool_decorator
        return app

    @pytest.fixture
    def mock_connection(self):
        """Create a mock OdooConnection."""
        connection = MagicMock(spec=OdooConnection)
        connection.is_authenticated = True
        return connection

    @pytest.fixture
    def mock_access_controller(self):
        """Create a mock AccessController."""
        controller = MagicMock(spec=AccessController)
        return controller

    @pytest.fixture
    def valid_config(self):
        """Create a valid config."""
        return OdooConfig(
            url="http://localhost:8069",
            api_key="test_api_key",
            database="test_db",
            default_limit=10,
            max_limit=100,
        )

    @pytest.fixture
    def handler(self, mock_app, mock_connection, mock_access_controller, valid_config):
        """Create an OdooToolHandler instance."""
        return OdooToolHandler(mock_app, mock_connection, mock_access_controller, valid_config)

    def test_handler_initialization(self, handler, mock_app):
        """Test handler is properly initialized."""
        assert handler.app == mock_app
        assert handler.connection is not None
        assert handler.access_controller is not None
        assert handler.config is not None

    def test_tools_registered(self, handler, mock_app):
        """Test that tools are registered with FastMCP."""
        # Check that all three tools are registered
        assert "search_records" in mock_app._tools
        assert "get_record" in mock_app._tools
        assert "list_models" in mock_app._tools

    @pytest.mark.asyncio
    async def test_search_records_success(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test successful search_records operation."""
        # Setup mocks
        mock_access_controller.validate_model_access.return_value = None
        mock_connection.search_count.return_value = 5
        mock_connection.search.return_value = [1, 2, 3]
        mock_connection.read.return_value = [
            {"id": 1, "name": "Record 1"},
            {"id": 2, "name": "Record 2"},
            {"id": 3, "name": "Record 3"},
        ]

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Call the tool
        result = await search_records(
            model="res.partner",
            domain=[["is_company", "=", True]],
            fields=["name", "email"],
            limit=3,
            offset=0,
            order="name asc",
        )

        # Verify result
        assert result["model"] == "res.partner"
        assert result["total"] == 5
        assert result["limit"] == 3
        assert result["offset"] == 0
        assert len(result["records"]) == 3

        # Verify calls
        mock_access_controller.validate_model_access.assert_called_once_with("res.partner", "read")
        mock_connection.search_count.assert_called_once_with(
            "res.partner", [["is_company", "=", True]]
        )
        mock_connection.search.assert_called_once_with(
            "res.partner", [["is_company", "=", True]], limit=3, offset=0, order="name asc"
        )

    @pytest.mark.asyncio
    async def test_search_records_access_denied(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test search_records with access denied."""
        # Setup mocks
        mock_access_controller.validate_model_access.side_effect = AccessControlError(
            "Access denied"
        )

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await search_records(model="res.partner", domain=[], fields=None, limit=10)

        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_records_not_authenticated(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test search_records when not authenticated."""
        # Setup mocks
        mock_connection.is_authenticated = False

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await search_records(model="res.partner")

        assert "Not authenticated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_records_connection_error(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test search_records with connection error."""
        # Setup mocks
        mock_connection.search_count.side_effect = OdooConnectionError("Connection lost")

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await search_records(model="res.partner")

        assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_record_success(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test successful get_record operation."""
        # Setup mocks
        mock_access_controller.validate_model_access.return_value = None
        mock_connection.read.return_value = [
            {"id": 123, "name": "Test Partner", "email": "test@example.com"}
        ]

        # Get the registered get_record function
        get_record = mock_app._tools["get_record"]

        # Call the tool
        result = await get_record(model="res.partner", record_id=123, fields=["name", "email"])

        # Verify result
        assert result["id"] == 123
        assert result["name"] == "Test Partner"
        assert result["email"] == "test@example.com"

        # Verify calls
        mock_access_controller.validate_model_access.assert_called_once_with("res.partner", "read")
        mock_connection.read.assert_called_once_with("res.partner", [123], ["name", "email"])

    @pytest.mark.asyncio
    async def test_get_record_not_found(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test get_record when record doesn't exist."""
        # Setup mocks
        mock_connection.read.return_value = []

        # Get the registered get_record function
        get_record = mock_app._tools["get_record"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await get_record(model="res.partner", record_id=999)

        assert "Record not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_record_access_denied(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test get_record with access denied."""
        # Setup mocks
        mock_access_controller.validate_model_access.side_effect = AccessControlError(
            "Access denied"
        )

        # Get the registered get_record function
        get_record = mock_app._tools["get_record"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await get_record(model="res.partner", record_id=1)

        assert "Access denied" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_record_not_authenticated(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test get_record when not authenticated."""
        # Setup mocks
        mock_connection.is_authenticated = False

        # Get the registered get_record function
        get_record = mock_app._tools["get_record"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await get_record(model="res.partner", record_id=1)

        assert "Not authenticated" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_record_connection_error(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test get_record with connection error."""
        # Setup mocks
        mock_connection.read.side_effect = OdooConnectionError("Connection lost")

        # Get the registered get_record function
        get_record = mock_app._tools["get_record"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await get_record(model="res.partner", record_id=1)

        assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_models_success(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test successful list_models operation."""
        # Setup mocks
        mock_access_controller.get_enabled_models.return_value = [
            {"model": "res.partner", "name": "Contact", "operations": ["read", "write"]},
            {"model": "sale.order", "name": "Sales Order", "operations": ["read"]},
        ]

        # Get the registered list_models function
        list_models = mock_app._tools["list_models"]

        # Call the tool
        result = await list_models()

        # Verify result
        assert len(result) == 2
        assert result[0]["model"] == "res.partner"
        assert result[1]["model"] == "sale.order"

        # Verify calls
        mock_access_controller.get_enabled_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_models_error(
        self, handler, mock_connection, mock_access_controller, mock_app
    ):
        """Test list_models with error."""
        # Setup mocks
        mock_access_controller.get_enabled_models.side_effect = Exception("API error")

        # Get the registered list_models function
        list_models = mock_app._tools["list_models"]

        # Call the tool and expect error
        with pytest.raises(ValidationError) as exc_info:
            await list_models()

        assert "Failed to list models" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_records_with_defaults(
        self, handler, mock_connection, mock_access_controller, mock_app, valid_config
    ):
        """Test search_records with default values."""
        # Setup mocks
        mock_connection.search_count.return_value = 0
        mock_connection.search.return_value = []
        mock_connection.read.return_value = []

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Call with minimal params
        result = await search_records(model="res.partner")

        # Verify defaults were applied
        assert result["limit"] == valid_config.default_limit
        assert result["offset"] == 0
        assert result["total"] == 0
        assert result["records"] == []

        # Verify domain default
        mock_connection.search_count.assert_called_with("res.partner", [])

    @pytest.mark.asyncio
    async def test_search_records_limit_validation(
        self, handler, mock_connection, mock_access_controller, mock_app, valid_config
    ):
        """Test search_records limit validation."""
        # Setup mocks
        mock_connection.search_count.return_value = 100
        mock_connection.search.return_value = []
        mock_connection.read.return_value = []

        # Get the registered search_records function
        search_records = mock_app._tools["search_records"]

        # Test with limit exceeding max
        result = await search_records(model="res.partner", limit=500)

        # Should use default limit since 500 > max_limit
        assert result["limit"] == valid_config.default_limit

        # Test with negative limit
        result = await search_records(model="res.partner", limit=-1)

        # Should use default limit
        assert result["limit"] == valid_config.default_limit


class TestRegisterTools:
    """Test cases for register_tools function."""

    def test_register_tools_success(self):
        """Test successful registration of tools."""
        # Create mocks
        mock_app = MagicMock(spec=FastMCP)
        mock_connection = MagicMock(spec=OdooConnection)
        mock_access_controller = MagicMock(spec=AccessController)
        config = OdooConfig(
            url="http://localhost:8069",
            api_key="test_key",
            database="test_db",
        )

        # Register tools
        handler = register_tools(mock_app, mock_connection, mock_access_controller, config)

        # Verify handler is returned
        assert isinstance(handler, OdooToolHandler)
        assert handler.app == mock_app
        assert handler.connection == mock_connection
        assert handler.access_controller == mock_access_controller
        assert handler.config == config


class TestToolIntegration:
    """Integration tests for tools with real server components."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_search_tool_with_real_server(self):
        """Test search tool with real server components."""
        # This test would require a running Odoo instance
        # Skipping for unit tests
        pytest.skip("Integration test requires running Odoo instance")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tools_in_mcp_context(self):
        """Test tools in full MCP context."""
        # This test would validate tools work correctly in MCP protocol
        # Skipping for unit tests
        pytest.skip("Integration test requires MCP setup")
