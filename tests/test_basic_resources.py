"""Tests for basic MCP resource handling."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from mcp.server.fastmcp import FastMCP

from mcp_server_odoo.config import OdooConfig
from mcp_server_odoo.odoo_connection import OdooConnection, OdooConnectionError
from mcp_server_odoo.access_control import AccessController, AccessControlError
from mcp_server_odoo.resources import (
    OdooResourceHandler,
    ResourceError,
    ResourceNotFoundError,
    ResourcePermissionError,
    register_resources
)


@pytest.fixture
def test_config():
    """Create test configuration."""
    # Load real config from environment for integration tests
    from mcp_server_odoo.config import get_config
    return get_config()


@pytest.fixture
def mock_connection():
    """Create mock OdooConnection."""
    conn = Mock(spec=OdooConnection)
    conn.is_authenticated = True
    conn.search = Mock()
    conn.read = Mock()
    return conn


@pytest.fixture
def mock_access_controller():
    """Create mock AccessController."""
    controller = Mock(spec=AccessController)
    controller.validate_model_access = Mock()
    return controller


@pytest.fixture
def mock_app():
    """Create mock FastMCP app."""
    app = Mock(spec=FastMCP)
    app.resource = Mock()
    # Make resource decorator return the function as-is
    app.resource.return_value = lambda func: func
    return app


@pytest.fixture
def resource_handler(mock_app, mock_connection, mock_access_controller):
    """Create OdooResourceHandler instance."""
    return OdooResourceHandler(mock_app, mock_connection, mock_access_controller)


class TestOdooResourceHandler:
    """Test OdooResourceHandler functionality."""
    
    def test_init(self, mock_app, mock_connection, mock_access_controller):
        """Test handler initialization."""
        handler = OdooResourceHandler(mock_app, mock_connection, mock_access_controller)
        
        assert handler.app == mock_app
        assert handler.connection == mock_connection
        assert handler.access_controller == mock_access_controller
        
        # Check that resources were registered
        mock_app.resource.assert_called_once_with("odoo://{model}/record/{record_id}")
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_success(self, resource_handler, mock_connection, mock_access_controller):
        """Test successful record retrieval."""
        # Setup mocks
        mock_connection.search.return_value = [1]
        mock_connection.read.return_value = [{
            'id': 1,
            'name': 'Test Partner',
            'display_name': 'Test Partner',
            'email': 'test@example.com',
            'is_company': True,
            'country_id': (1, 'United States'),
            'child_ids': [2, 3, 4],
            'phone': False,
            '__last_update': '2025-01-01 00:00:00'
        }]
        
        # Test retrieval
        result = await resource_handler._handle_record_retrieval('res.partner', '1')
        
        # Verify calls
        mock_access_controller.validate_model_access.assert_called_once_with('res.partner', 'read')
        mock_connection.search.assert_called_once_with('res.partner', [('id', '=', 1)])
        mock_connection.read.assert_called_once_with('res.partner', [1])
        
        # Check result format
        assert 'Resource: res.partner/record/1' in result
        assert 'Name: Test Partner' in result
        assert 'ID: 1' in result
        assert 'email: test@example.com' in result
        assert 'is_company: True' in result
        assert 'country_id: United States (ID: 1)' in result
        assert 'child_ids: 3 record(s)' in result
        assert 'phone: Not set' in result
        assert '__last_update' not in result  # Should be skipped
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_not_found(self, resource_handler, mock_connection, mock_access_controller):
        """Test record not found error."""
        # Setup mocks
        mock_connection.search.return_value = []
        
        # Test retrieval
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', '999')
        
        assert "Record not found: res.partner with ID 999 does not exist" in str(exc_info.value)
        
        # Verify calls
        mock_access_controller.validate_model_access.assert_called_once_with('res.partner', 'read')
        mock_connection.search.assert_called_once_with('res.partner', [('id', '=', 999)])
        mock_connection.read.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_invalid_id(self, resource_handler):
        """Test invalid record ID."""
        # Test with non-numeric ID
        with pytest.raises(ResourceError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', 'abc')
        
        assert "Invalid record ID 'abc'" in str(exc_info.value)
        
        # Test with negative ID
        with pytest.raises(ResourceError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', '-5')
        
        assert "Record ID must be positive" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_permission_denied(self, resource_handler, mock_access_controller):
        """Test permission denied error."""
        # Setup mock to raise permission error
        mock_access_controller.validate_model_access.side_effect = AccessControlError("Access denied for res.partner")
        
        # Test retrieval
        with pytest.raises(ResourcePermissionError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', '1')
        
        assert "Access denied:" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_not_authenticated(self, resource_handler, mock_connection):
        """Test error when not authenticated."""
        # Setup mock
        mock_connection.is_authenticated = False
        
        # Test retrieval
        with pytest.raises(ResourceError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', '1')
        
        assert "Not authenticated with Odoo" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_record_retrieval_connection_error(self, resource_handler, mock_connection, mock_access_controller):
        """Test connection error during retrieval."""
        # Setup mock to raise connection error
        mock_connection.search.side_effect = OdooConnectionError("Connection lost")
        
        # Test retrieval
        with pytest.raises(ResourceError) as exc_info:
            await resource_handler._handle_record_retrieval('res.partner', '1')
        
        assert "Connection error:" in str(exc_info.value)
    
    def test_format_record(self, resource_handler):
        """Test record formatting."""
        record = {
            'id': 42,
            'name': 'Acme Corp',
            'email': 'info@acme.com',
            'partner_id': (10, 'Parent Company'),
            'child_ids': [1, 2, 3],
            'active': True,
            'credit_limit': 5000.0,
            'comment': None,
            '__last_update': '2025-01-01'
        }
        
        result = resource_handler._format_record('res.partner', record)
        
        # Check formatting
        assert 'Resource: res.partner/record/42' in result
        assert 'Name: Acme Corp' in result
        assert 'ID: 42' in result
        assert 'email: info@acme.com' in result
        assert 'partner_id: Parent Company (ID: 10)' in result
        assert 'child_ids: 3 record(s)' in result
        assert 'active: True' in result
        assert 'credit_limit: 5000.0' in result
        assert 'comment: Not set' in result
        assert '__last_update' not in result
    
    def test_format_field_value(self, resource_handler):
        """Test field value formatting."""
        # Test None/False
        assert resource_handler._format_field_value('field', None) == "Not set"
        assert resource_handler._format_field_value('field', False) == "Not set"
        
        # Test many2one
        assert resource_handler._format_field_value('field', (1, 'Name')) == "Name (ID: 1)"
        
        # Test empty list
        assert resource_handler._format_field_value('field', []) == "None"
        
        # Test non-empty list
        assert resource_handler._format_field_value('field', [1, 2, 3]) == "3 record(s)"
        
        # Test other types
        assert resource_handler._format_field_value('field', 'text') == "text"
        assert resource_handler._format_field_value('field', 123) == "123"
        assert resource_handler._format_field_value('field', True) == "True"


class TestRegisterResources:
    """Test register_resources function."""
    
    def test_register_resources(self, mock_app, mock_connection, mock_access_controller):
        """Test resource registration."""
        handler = register_resources(mock_app, mock_connection, mock_access_controller)
        
        assert isinstance(handler, OdooResourceHandler)
        assert handler.app == mock_app
        assert handler.connection == mock_connection
        assert handler.access_controller == mock_access_controller
        
        # Check that resources were registered
        mock_app.resource.assert_called_once()


class TestResourceIntegration:
    """Integration tests with real Odoo server."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_record_retrieval(self, test_config):
        """Test record retrieval with real server."""
        # Create real connection
        connection = OdooConnection(test_config)
        connection.connect()
        connection.authenticate()
        
        # Create access controller
        access_controller = AccessController(test_config)
        
        # Create FastMCP app
        app = FastMCP("test-app")
        
        # Register resources
        handler = register_resources(app, connection, access_controller)
        
        try:
            # Search for a partner record
            partner_ids = connection.search('res.partner', [], limit=1)
            
            if partner_ids:
                # Test retrieval
                result = await handler._handle_record_retrieval('res.partner', str(partner_ids[0]))
                
                # Verify result format
                assert f'Resource: res.partner/record/{partner_ids[0]}' in result
                assert 'ID:' in result
                assert '=' * 50 in result  # Separator line
                
        finally:
            connection.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_record_not_found(self, test_config):
        """Test record not found with real server."""
        # Create real connection
        connection = OdooConnection(test_config)
        connection.connect()
        connection.authenticate()
        
        # Create access controller
        access_controller = AccessController(test_config)
        
        # Create FastMCP app
        app = FastMCP("test-app")
        
        # Register resources
        handler = register_resources(app, connection, access_controller)
        
        try:
            # Test with non-existent ID
            with pytest.raises(ResourceNotFoundError):
                await handler._handle_record_retrieval('res.partner', '999999999')
                
        finally:
            connection.disconnect()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_permission_denied(self, test_config):
        """Test permission denied with real server."""
        # Create real connection
        connection = OdooConnection(test_config)
        connection.connect()
        connection.authenticate()
        
        # Create access controller
        access_controller = AccessController(test_config)
        
        # Create FastMCP app
        app = FastMCP("test-app")
        
        # Register resources
        handler = register_resources(app, connection, access_controller)
        
        try:
            # Test with non-enabled model
            with pytest.raises(ResourcePermissionError):
                await handler._handle_record_retrieval('account.invoice', '1')
                
        finally:
            connection.disconnect()