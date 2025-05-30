"""Tests for XML-RPC operations in OdooConnection.

This module tests the XML-RPC communication layer including execute methods
and core Odoo operations.
"""

import pytest
import socket
from unittest.mock import Mock, patch, MagicMock
from xmlrpc.client import Fault

from mcp_server_odoo.odoo_connection import OdooConnection, OdooConnectionError
from mcp_server_odoo.config import OdooConfig


def is_odoo_server_running(host="localhost", port=8069):
    """Check if Odoo server is running."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    except Exception:
        return False
    finally:
        sock.close()


class TestXMLRPCOperations:
    """Test XML-RPC operations functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return OdooConfig(
            url="http://localhost:8069",
            api_key="test_api_key",
            database="mcp"
        )
    
    @pytest.fixture
    def authenticated_connection(self, config):
        """Create authenticated connection."""
        conn = OdooConnection(config)
        conn._connected = True
        conn._authenticated = True
        conn._uid = 2
        conn._database = "mcp"
        conn._auth_method = "api_key"
        return conn
    
    def test_execute_not_authenticated(self, config):
        """Test execute raises error when not authenticated."""
        conn = OdooConnection(config)
        conn._connected = True
        
        with pytest.raises(OdooConnectionError, match="Not authenticated"):
            conn.execute("res.partner", "search", [])
    
    def test_execute_not_connected(self, config):
        """Test execute raises error when not connected."""
        conn = OdooConnection(config)
        conn._authenticated = True
        
        with pytest.raises(OdooConnectionError, match="Not connected"):
            conn.execute("res.partner", "search", [])
    
    def test_execute_kw_success(self, authenticated_connection):
        """Test successful execute_kw operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = [1, 2, 3]
        authenticated_connection._object_proxy = mock_proxy
        
        # Execute operation
        result = authenticated_connection.execute_kw(
            "res.partner", "search", [[['is_company', '=', True]]], {"limit": 10}
        )
        
        # Verify result
        assert result == [1, 2, 3]
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp",
            2,
            "test_api_key",
            "res.partner",
            "search",
            [[['is_company', '=', True]]],
            {"limit": 10}
        )
    
    def test_execute_simple(self, authenticated_connection):
        """Test simple execute method."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = {"id": 1, "name": "Test"}
        authenticated_connection._object_proxy = mock_proxy
        
        # Execute operation
        result = authenticated_connection.execute("res.partner", "read", [1])
        
        # Verify result
        assert result == {"id": 1, "name": "Test"}
        
        # Verify it called execute_kw correctly
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "read", [[1]], {}
        )
    
    def test_execute_kw_xmlrpc_fault(self, authenticated_connection):
        """Test execute_kw handles XML-RPC fault."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.side_effect = Fault(1, "Access Denied")
        authenticated_connection._object_proxy = mock_proxy
        
        # Should raise error
        with pytest.raises(OdooConnectionError, match="Access Denied"):
            authenticated_connection.execute_kw("res.partner", "unlink", [[1]], {})
    
    def test_execute_kw_timeout(self, authenticated_connection):
        """Test execute_kw handles timeout."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.side_effect = socket.timeout()
        authenticated_connection._object_proxy = mock_proxy
        
        # Should raise timeout error
        with pytest.raises(OdooConnectionError, match="timeout"):
            authenticated_connection.execute_kw("res.partner", "search", [[]], {})
    
    def test_search_operation(self, authenticated_connection):
        """Test search operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = [1, 2, 3]
        authenticated_connection._object_proxy = mock_proxy
        
        # Search
        result = authenticated_connection.search(
            "res.partner", 
            [['is_company', '=', True]], 
            limit=5
        )
        
        assert result == [1, 2, 3]
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "search",
            [[['is_company', '=', True]]], {"limit": 5}
        )
    
    def test_read_operation(self, authenticated_connection):
        """Test read operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = [
            {"id": 1, "name": "Company A"},
            {"id": 2, "name": "Company B"}
        ]
        authenticated_connection._object_proxy = mock_proxy
        
        # Read
        result = authenticated_connection.read(
            "res.partner", [1, 2], ["name", "email"]
        )
        
        assert len(result) == 2
        assert result[0]["name"] == "Company A"
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "read",
            [[1, 2]], {"fields": ["name", "email"]}
        )
    
    def test_search_read_operation(self, authenticated_connection):
        """Test search_read operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = [
            {"id": 1, "name": "Company A", "email": "a@example.com"}
        ]
        authenticated_connection._object_proxy = mock_proxy
        
        # Search and read
        result = authenticated_connection.search_read(
            "res.partner",
            [['is_company', '=', True]],
            ["name", "email"],
            limit=1
        )
        
        assert len(result) == 1
        assert result[0]["email"] == "a@example.com"
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "search_read",
            [[['is_company', '=', True]]], 
            {"fields": ["name", "email"], "limit": 1}
        )
    
    def test_fields_get_operation(self, authenticated_connection):
        """Test fields_get operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = {
            "name": {"type": "char", "string": "Name", "required": True},
            "email": {"type": "char", "string": "Email"}
        }
        authenticated_connection._object_proxy = mock_proxy
        
        # Get fields
        result = authenticated_connection.fields_get("res.partner")
        
        assert "name" in result
        assert result["name"]["type"] == "char"
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "fields_get",
            [], {}
        )
    
    def test_search_count_operation(self, authenticated_connection):
        """Test search_count operation."""
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = 42
        authenticated_connection._object_proxy = mock_proxy
        
        # Count records
        result = authenticated_connection.search_count(
            "res.partner", [['is_company', '=', True]]
        )
        
        assert result == 42
        
        # Verify call
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "test_api_key", "res.partner", "search_count",
            [[['is_company', '=', True]]], {}
        )
    
    def test_password_auth_uses_password(self, config):
        """Test that password auth uses password for execute_kw."""
        config = OdooConfig(
            url="http://localhost:8069",
            username="admin",
            password="admin123",
            database="mcp"
        )
        conn = OdooConnection(config)
        conn._connected = True
        conn._authenticated = True
        conn._uid = 2
        conn._database = "mcp"
        conn._auth_method = "password"
        
        # Mock object proxy
        mock_proxy = Mock()
        mock_proxy.execute_kw.return_value = []
        conn._object_proxy = mock_proxy
        
        # Execute
        conn.search("res.partner", [])
        
        # Verify password was used
        mock_proxy.execute_kw.assert_called_once_with(
            "mcp", 2, "admin123", "res.partner", "search", [[]], {}
        )


@pytest.mark.skipif(
    not is_odoo_server_running(),
    reason="Odoo server not running at localhost:8069"
)
class TestXMLRPCOperationsIntegration:
    """Integration tests with real Odoo server."""
    
    @pytest.fixture
    def real_config(self):
        """Create configuration with real credentials."""
        return OdooConfig(
            url="http://localhost:8069",
            api_key="0ef5b399e9ee9c11b053dfb6eeba8de473c29fcd",
            database=None  # Auto-select
        )
    
    def test_real_search_partners(self, real_config):
        """Test searching partners on real server."""
        with OdooConnection(real_config) as conn:
            conn.authenticate()
            
            # Search for companies
            partner_ids = conn.search(
                "res.partner", 
                [['is_company', '=', True]],
                limit=5
            )
            
            assert isinstance(partner_ids, list)
            print(f"Found {len(partner_ids)} company partners")
    
    def test_real_read_partners(self, real_config):
        """Test reading partner data on real server."""
        with OdooConnection(real_config) as conn:
            conn.authenticate()
            
            # Search for a partner
            partner_ids = conn.search("res.partner", [], limit=1)
            
            if partner_ids:
                # Read partner data
                partners = conn.read(
                    "res.partner", 
                    partner_ids, 
                    ["name", "email", "is_company"]
                )
                
                assert len(partners) == 1
                assert "name" in partners[0]
                print(f"Partner: {partners[0].get('name')}")
    
    def test_real_search_read_partners(self, real_config):
        """Test search_read on real server."""
        with OdooConnection(real_config) as conn:
            conn.authenticate()
            
            # Search and read in one operation
            partners = conn.search_read(
                "res.partner",
                [['is_company', '=', True]],
                ["name", "email", "phone"],
                limit=3
            )
            
            assert isinstance(partners, list)
            for partner in partners:
                assert "name" in partner
                print(f"Company: {partner.get('name')}")
    
    def test_real_fields_get(self, real_config):
        """Test getting field definitions on real server."""
        with OdooConnection(real_config) as conn:
            conn.authenticate()
            
            # Get partner fields
            fields = conn.fields_get("res.partner", ["string", "type", "required"])
            
            assert isinstance(fields, dict)
            assert "name" in fields
            assert fields["name"]["type"] == "char"
            print(f"Found {len(fields)} fields in res.partner")
    
    def test_real_search_count(self, real_config):
        """Test counting records on real server."""
        with OdooConnection(real_config) as conn:
            conn.authenticate()
            
            # Count all partners
            total_count = conn.search_count("res.partner", [])
            
            # Count companies
            company_count = conn.search_count(
                "res.partner", 
                [['is_company', '=', True]]
            )
            
            assert total_count >= company_count
            print(f"Total partners: {total_count}, Companies: {company_count}")
    
    def test_real_execute_method(self, real_config):
        """Test generic execute method on real server."""
        with OdooConnection(real_config) as conn:
            try:
                conn.authenticate()
            except OdooConnectionError as e:
                if "429" in str(e) or "Too many requests" in str(e).lower():
                    pytest.skip("Rate limited by server")
                raise
            
            # Use execute to call name_search
            result = conn.execute(
                "res.partner", 
                "name_search",
                "Admin",  # search term
                [],       # domain
                "ilike",  # operator
                100       # limit
            )
            
            assert isinstance(result, list)
            print(f"Name search returned {len(result)} results")
    
    def test_real_error_handling(self, real_config):
        """Test error handling with real server."""
        with OdooConnection(real_config) as conn:
            try:
                conn.authenticate()
            except OdooConnectionError as e:
                if "429" in str(e) or "Too many requests" in str(e).lower():
                    pytest.skip("Rate limited by server")
                raise
            
            # Try to access non-existent model
            with pytest.raises(OdooConnectionError):
                conn.search("non.existent.model", [])
            
            # Try invalid method
            with pytest.raises(OdooConnectionError):
                conn.execute("res.partner", "invalid_method")


if __name__ == "__main__":
    # Run integration tests when executed directly
    pytest.main([__file__, "-v", "-k", "Integration"])