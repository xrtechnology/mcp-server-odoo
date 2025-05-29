"""Odoo XML-RPC connection management.

This module provides the OdooConnection class for managing connections
to Odoo via XML-RPC using MCP-specific endpoints.
"""

import xmlrpc.client
import socket
import logging
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse, urlunparse
from contextlib import contextmanager

from .config import OdooConfig

logger = logging.getLogger(__name__)


class OdooConnectionError(Exception):
    """Base exception for Odoo connection errors."""
    pass


class OdooConnection:
    """Manages XML-RPC connections to Odoo with MCP-specific endpoints.
    
    This class provides connection management, health checking, and
    proper resource cleanup for Odoo XML-RPC connections.
    """
    
    # MCP-specific endpoints
    MCP_DB_ENDPOINT = "/mcp/xmlrpc/db"
    MCP_COMMON_ENDPOINT = "/mcp/xmlrpc/common"
    MCP_OBJECT_ENDPOINT = "/mcp/xmlrpc/object"
    
    # Connection timeout in seconds
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, config: OdooConfig, timeout: int = DEFAULT_TIMEOUT):
        """Initialize connection with configuration.
        
        Args:
            config: OdooConfig object with connection parameters
            timeout: Connection timeout in seconds
        """
        self.config = config
        self.timeout = timeout
        self._url_components = self._parse_url(config.url)
        
        # XML-RPC proxies (created on connect)
        self._db_proxy: Optional[xmlrpc.client.ServerProxy] = None
        self._common_proxy: Optional[xmlrpc.client.ServerProxy] = None
        self._object_proxy: Optional[xmlrpc.client.ServerProxy] = None
        
        # Connection state
        self._connected = False
        self._uid: Optional[int] = None
        
        logger.info(f"Initialized OdooConnection for {self._url_components['host']}")
    
    def _parse_url(self, url: str) -> Dict[str, Any]:
        """Parse and validate Odoo URL.
        
        Args:
            url: The Odoo server URL
            
        Returns:
            Dictionary with URL components
            
        Raises:
            OdooConnectionError: If URL is invalid
        """
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme in ('http', 'https'):
                raise OdooConnectionError(
                    f"Invalid URL scheme: {parsed.scheme}. "
                    "Must be http or https"
                )
            
            if not parsed.hostname:
                raise OdooConnectionError("Invalid URL: missing hostname")
            
            port = parsed.port
            if not port:
                port = 443 if parsed.scheme == 'https' else 80
            
            return {
                'scheme': parsed.scheme,
                'host': parsed.hostname,
                'port': port,
                'path': parsed.path.rstrip('/') or '',
                'base_url': url.rstrip('/')
            }
            
        except Exception as e:
            raise OdooConnectionError(f"Failed to parse URL: {e}")
    
    def _create_transport(self) -> xmlrpc.client.Transport:
        """Create XML-RPC transport with timeout support.
        
        Returns:
            Configured Transport object
        """
        class TimeoutTransport(xmlrpc.client.Transport):
            def __init__(self, timeout, *args, **kwargs):
                self.timeout = timeout
                super().__init__(*args, **kwargs)
            
            def make_connection(self, host):
                connection = super().make_connection(host)
                if hasattr(connection, 'sock') and connection.sock:
                    connection.sock.settimeout(self.timeout)
                return connection
        
        return TimeoutTransport(self.timeout)
    
    def _build_endpoint_url(self, endpoint: str) -> str:
        """Build full URL for an MCP endpoint.
        
        Args:
            endpoint: The MCP endpoint path
            
        Returns:
            Full URL for the endpoint
        """
        return f"{self._url_components['base_url']}{endpoint}"
    
    def connect(self) -> None:
        """Establish connection to Odoo server.
        
        Creates XML-RPC proxies for MCP endpoints but doesn't
        authenticate yet.
        
        Raises:
            OdooConnectionError: If connection fails
        """
        if self._connected:
            logger.warning("Already connected to Odoo")
            return
        
        try:
            transport = self._create_transport()
            
            # Create proxies for MCP endpoints
            self._db_proxy = xmlrpc.client.ServerProxy(
                self._build_endpoint_url(self.MCP_DB_ENDPOINT),
                transport=transport,
                allow_none=True
            )
            
            self._common_proxy = xmlrpc.client.ServerProxy(
                self._build_endpoint_url(self.MCP_COMMON_ENDPOINT),
                transport=transport,
                allow_none=True
            )
            
            self._object_proxy = xmlrpc.client.ServerProxy(
                self._build_endpoint_url(self.MCP_OBJECT_ENDPOINT),
                transport=transport,
                allow_none=True
            )
            
            # Test connection by calling server_version
            self._test_connection()
            
            self._connected = True
            logger.info("Successfully connected to Odoo server")
            
        except socket.timeout:
            raise OdooConnectionError(
                f"Connection timeout after {self.timeout} seconds"
            )
        except socket.error as e:
            raise OdooConnectionError(
                f"Failed to connect to {self._url_components['host']}:"
                f"{self._url_components['port']}: {e}"
            )
        except Exception as e:
            raise OdooConnectionError(f"Connection failed: {e}")
    
    def _test_connection(self) -> None:
        """Test connection by calling server_version.
        
        Raises:
            OdooConnectionError: If test fails
        """
        try:
            # Try to get server version via common endpoint
            version = self._common_proxy.version()
            logger.debug(f"Server version: {version}")
        except Exception as e:
            raise OdooConnectionError(
                f"Connection test failed: {e}"
            )
    
    def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        if not self._connected:
            logger.warning("Not connected to Odoo")
            return
        
        # Close transport connections
        for proxy in (self._db_proxy, self._common_proxy, self._object_proxy):
            if proxy and hasattr(proxy, '_ServerProxy__transport'):
                try:
                    proxy._ServerProxy__transport.close()
                except Exception as e:
                    logger.warning(f"Error closing transport: {e}")
        
        # Clear proxies
        self._db_proxy = None
        self._common_proxy = None
        self._object_proxy = None
        
        # Clear connection state
        self._connected = False
        self._uid = None
        
        logger.info("Disconnected from Odoo server")
    
    def check_health(self) -> Tuple[bool, str]:
        """Check connection health.
        
        Returns:
            Tuple of (is_healthy, status_message)
        """
        if not self._connected:
            return False, "Not connected"
        
        try:
            # Try to get server version as health check
            version = self._common_proxy.version()
            return True, f"Connected to Odoo {version.get('server_version', 'unknown')}"
        except socket.timeout:
            return False, f"Health check timeout after {self.timeout} seconds"
        except Exception as e:
            return False, f"Health check failed: {e}"
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._connected
    
    @property
    def db_proxy(self) -> xmlrpc.client.ServerProxy:
        """Get database operations proxy.
        
        Returns:
            XML-RPC proxy for database operations
            
        Raises:
            OdooConnectionError: If not connected
        """
        if not self._connected or not self._db_proxy:
            raise OdooConnectionError("Not connected to Odoo")
        return self._db_proxy
    
    @property
    def common_proxy(self) -> xmlrpc.client.ServerProxy:
        """Get common operations proxy.
        
        Returns:
            XML-RPC proxy for common operations
            
        Raises:
            OdooConnectionError: If not connected
        """
        if not self._connected or not self._common_proxy:
            raise OdooConnectionError("Not connected to Odoo")
        return self._common_proxy
    
    @property
    def object_proxy(self) -> xmlrpc.client.ServerProxy:
        """Get object operations proxy.
        
        Returns:
            XML-RPC proxy for object operations
            
        Raises:
            OdooConnectionError: If not connected
        """
        if not self._connected or not self._object_proxy:
            raise OdooConnectionError("Not connected to Odoo")
        return self._object_proxy
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.disconnect()
        except Exception:
            pass
    
    def list_databases(self) -> List[str]:
        """List all available databases on the Odoo server.
        
        Returns:
            List of database names
            
        Raises:
            OdooConnectionError: If listing fails or not connected
        """
        if not self._connected:
            raise OdooConnectionError("Not connected to Odoo")
        
        try:
            # Call list_db method on database proxy
            databases = self.db_proxy.list()
            logger.info(f"Found {len(databases)} databases: {databases}")
            return databases
        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            raise OdooConnectionError(f"Failed to list databases: {e}")
    
    def database_exists(self, db_name: str) -> bool:
        """Check if a specific database exists.
        
        Args:
            db_name: Name of the database to check
            
        Returns:
            True if database exists, False otherwise
            
        Raises:
            OdooConnectionError: If check fails
        """
        try:
            databases = self.list_databases()
            return db_name in databases
        except Exception as e:
            logger.error(f"Failed to check database existence: {e}")
            raise OdooConnectionError(f"Failed to check database existence: {e}")
    
    def auto_select_database(self) -> str:
        """Automatically select an appropriate database.
        
        Selection logic:
        1. If config.database is set, validate and use it
        2. If only one database exists, use it
        3. If multiple databases exist and one is named 'odoo', use it
        4. Otherwise raise an error
        
        Returns:
            Selected database name
            
        Raises:
            OdooConnectionError: If no suitable database can be selected
        """
        # If database is explicitly configured, validate and use it
        if self.config.database:
            db_name = self.config.database
            logger.info(f"Using configured database: {db_name}")
            
            if not self.database_exists(db_name):
                raise OdooConnectionError(
                    f"Configured database '{db_name}' does not exist on server"
                )
            
            return db_name
        
        # List available databases
        try:
            databases = self.list_databases()
        except Exception as e:
            raise OdooConnectionError(f"Failed to list databases for auto-selection: {e}")
        
        # Handle different scenarios
        if not databases:
            raise OdooConnectionError("No databases found on Odoo server")
        
        if len(databases) == 1:
            db_name = databases[0]
            logger.info(f"Auto-selected only available database: {db_name}")
            return db_name
        
        # Multiple databases - check for 'odoo'
        if 'odoo' in databases:
            logger.info("Auto-selected 'odoo' database from multiple options")
            return 'odoo'
        
        # Cannot auto-select
        raise OdooConnectionError(
            f"Cannot auto-select database. Found {len(databases)} databases: "
            f"{', '.join(databases)}. Please specify ODOO_DB in configuration."
        )
    
    def validate_database_access(self, db_name: str) -> bool:
        """Validate that we can access the specified database.
        
        This method attempts to authenticate with the database to verify access.
        
        Args:
            db_name: Name of the database to validate
            
        Returns:
            True if database is accessible, False otherwise
            
        Raises:
            OdooConnectionError: If validation fails
        """
        if not self._connected:
            raise OdooConnectionError("Not connected to Odoo")
        
        try:
            # For API key auth, we'll need to implement a different check
            # For now, we just verify the database exists
            if self.config.uses_api_key:
                # API key validation would be done during actual authentication
                return self.database_exists(db_name)
            
            # For username/password auth, try to authenticate
            if self.config.uses_credentials:
                # Try to authenticate with the database
                # This will fail if we don't have access
                uid = self.common_proxy.authenticate(
                    db_name, 
                    self.config.username, 
                    self.config.password,
                    {}
                )
                if uid:
                    logger.info(f"Successfully validated access to database '{db_name}'")
                    return True
                else:
                    logger.warning(f"Authentication failed for database '{db_name}'")
                    return False
            
            # Should not reach here due to config validation
            raise OdooConnectionError("No authentication method configured")
            
        except xmlrpc.client.Fault as e:
            logger.error(f"XML-RPC fault validating database access: {e}")
            if "Access Denied" in str(e):
                return False
            raise OdooConnectionError(f"Failed to validate database access: {e}")
        except Exception as e:
            logger.error(f"Error validating database access: {e}")
            raise OdooConnectionError(f"Failed to validate database access: {e}")


@contextmanager
def create_connection(config: OdooConfig, timeout: int = OdooConnection.DEFAULT_TIMEOUT):
    """Create a connection context manager.
    
    Args:
        config: OdooConfig object
        timeout: Connection timeout in seconds
        
    Yields:
        Connected OdooConnection instance
        
    Example:
        with create_connection(config) as conn:
            # Use connection
            version = conn.common_proxy.version()
    """
    conn = OdooConnection(config, timeout)
    try:
        conn.connect()
        yield conn
    finally:
        conn.disconnect()