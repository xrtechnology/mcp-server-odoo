"""Pytest configuration and fixtures for Odoo MCP Server tests."""

import os
import socket
import pytest
import xmlrpc.client
from typing import Generator

from mcp_server_odoo.config import OdooConfig


def is_odoo_server_available(host: str = "localhost", port: int = 8069) -> bool:
    """Check if Odoo server is available at the given host and port."""
    try:
        # Try to connect to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return False
            
        # Try to access the XML-RPC endpoint
        try:
            proxy = xmlrpc.client.ServerProxy(f"http://{host}:{port}/xmlrpc/2/common")
            proxy.version()
            return True
        except:
            return False
            
    except:
        return False


# Global flag for Odoo server availability
ODOO_SERVER_AVAILABLE = is_odoo_server_available()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "odoo_required: mark test as requiring a running Odoo server"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip tests that require Odoo when it's not available."""
    if ODOO_SERVER_AVAILABLE:
        # Server is available, don't skip anything
        return
        
    skip_odoo = pytest.mark.skip(reason="Odoo server not available at localhost:8069")
    
    for item in items:
        # Skip tests marked with 'integration' when server is not available
        if "integration" in item.keywords:
            item.add_marker(skip_odoo)
        
        # Skip tests marked with 'odoo_required' when server is not available  
        if "odoo_required" in item.keywords:
            item.add_marker(skip_odoo)
            
        # Also check for specific test names that indicate they need a real server
        test_name = item.name.lower()
        if any(keyword in test_name for keyword in ["real_server", "integration"]):
            item.add_marker(skip_odoo)


@pytest.fixture
def odoo_server_required():
    """Fixture that skips test if Odoo server is not available."""
    if not ODOO_SERVER_AVAILABLE:
        pytest.skip("Odoo server not available at localhost:8069")


@pytest.fixture
def test_config_with_server_check(odoo_server_required) -> OdooConfig:
    """Create test configuration, but skip if server not available."""
    return OdooConfig(
        url="http://localhost:8069",
        api_key="test_api_key",
        database="mcp",
        log_level="INFO",
        default_limit=10,
        max_limit=100
    )