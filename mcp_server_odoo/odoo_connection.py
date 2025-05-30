"""Odoo XML-RPC connection management.

This module provides the OdooConnection class for managing connections
to Odoo via XML-RPC using MCP-specific endpoints.
"""

import xmlrpc.client
import socket
import logging
import json
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse, urlunparse
from contextlib import contextmanager
import urllib.request
import urllib.error

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
        self._database: Optional[str] = None
        self._authenticated = False
        self._auth_method: Optional[str] = None  # 'api_key' or 'password'
        
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
        self._database = None
        self._authenticated = False
        self._auth_method = None
        
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
    
    def test_connection(self) -> bool:
        """Test if connection to Odoo is working.
        
        Returns:
            True if connection is working, False otherwise
        """
        # If not connected, try to connect first
        if not self._connected:
            try:
                self.connect()
            except Exception as e:
                logger.error(f"Failed to connect: {e}")
                return False
        
        # Check health
        is_healthy, _ = self.check_health()
        return is_healthy
    
    def close(self) -> None:
        """Close the connection (alias for disconnect)."""
        self.disconnect()
    
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
    
    def _authenticate_api_key(self, database: str) -> bool:
        """Authenticate using API key.
        
        Args:
            database: Database name to authenticate against
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            OdooConnectionError: If API request fails
        """
        if not self.config.api_key:
            return False
        
        try:
            # Build URL for API key validation endpoint
            url = f"{self._url_components['base_url']}/mcp/auth/validate"
            
            # Create request with API key header
            req = urllib.request.Request(url)
            req.add_header('X-API-Key', self.config.api_key)
            
            # Make the request
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if data.get('success') and data.get('data', {}).get('valid'):
                    self._uid = data['data'].get('user_id')
                    self._database = database
                    self._auth_method = 'api_key'
                    self._authenticated = True
                    logger.info(f"Successfully authenticated with API key for user ID {self._uid}")
                    return True
                else:
                    logger.warning("API key validation failed")
                    return False
                    
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.warning("Invalid API key")
                return False
            else:
                logger.error(f"HTTP error during API key validation: {e}")
                raise OdooConnectionError(f"Failed to validate API key: {e}")
        except Exception as e:
            logger.error(f"Error during API key validation: {e}")
            raise OdooConnectionError(f"Failed to validate API key: {e}")
    
    def _authenticate_password(self, database: str) -> bool:
        """Authenticate using username and password.
        
        Args:
            database: Database name to authenticate against
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            OdooConnectionError: If authentication fails
        """
        if not self.config.username or not self.config.password:
            return False
        
        try:
            # Use common proxy to authenticate
            uid = self.common_proxy.authenticate(
                database,
                self.config.username,
                self.config.password,
                {}
            )
            
            if uid:
                self._uid = uid
                self._database = database
                self._auth_method = 'password'
                self._authenticated = True
                logger.info(f"Successfully authenticated with username/password for user ID {uid}")
                return True
            else:
                logger.warning("Username/password authentication failed")
                return False
                
        except xmlrpc.client.Fault as e:
            logger.warning(f"Authentication fault: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during password authentication: {e}")
            raise OdooConnectionError(f"Failed to authenticate: {e}")
    
    def authenticate(self, database: Optional[str] = None) -> None:
        """Authenticate with Odoo using available credentials.
        
        Tries API key authentication first, then falls back to username/password.
        
        Args:
            database: Database name. If not provided, uses auto-selection.
            
        Raises:
            OdooConnectionError: If authentication fails
        """
        if not self._connected:
            raise OdooConnectionError("Not connected to Odoo")
        
        # Get database name
        if database:
            db_name = database
        else:
            db_name = self.auto_select_database()
        
        # Try API key authentication first
        if self.config.uses_api_key:
            logger.info("Attempting API key authentication")
            if self._authenticate_api_key(db_name):
                return
            else:
                logger.info("API key authentication failed, trying username/password")
        
        # Try username/password authentication
        if self.config.uses_credentials:
            logger.info("Attempting username/password authentication")
            if self._authenticate_password(db_name):
                return
        
        # Authentication failed
        raise OdooConnectionError(
            "Authentication failed. Please check your credentials."
        )
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._authenticated
    
    @property
    def uid(self) -> Optional[int]:
        """Get authenticated user ID."""
        return self._uid
    
    @property
    def database(self) -> Optional[str]:
        """Get authenticated database name."""
        return self._database
    
    @property
    def auth_method(self) -> Optional[str]:
        """Get authentication method used ('api_key' or 'password')."""
        return self._auth_method
    
    def execute(self, model: str, method: str, *args) -> Any:
        """Execute an operation on an Odoo model.
        
        This is a simplified interface that calls execute_kw with empty kwargs.
        
        Args:
            model: The Odoo model name (e.g., 'res.partner')
            method: The method to call (e.g., 'search', 'read')
            *args: Arguments to pass to the method
            
        Returns:
            The result from Odoo
            
        Raises:
            OdooConnectionError: If not authenticated or execution fails
        """
        return self.execute_kw(model, method, list(args), {})
    
    def execute_kw(self, model: str, method: str, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        """Execute an operation on an Odoo model with keyword arguments.
        
        This is the main method for interacting with Odoo models via XML-RPC.
        
        Args:
            model: The Odoo model name (e.g., 'res.partner')
            method: The method to call (e.g., 'search_read')
            args: List of positional arguments for the method
            kwargs: Dictionary of keyword arguments for the method
            
        Returns:
            The result from Odoo
            
        Raises:
            OdooConnectionError: If not authenticated or execution fails
        """
        if not self._authenticated:
            raise OdooConnectionError("Not authenticated. Call authenticate() first.")
        
        if not self._connected:
            raise OdooConnectionError("Not connected to Odoo")
        
        # Get the appropriate password/token based on auth method
        password_or_token = (
            self.config.api_key if self._auth_method == 'api_key' 
            else self.config.password
        )
        
        try:
            # Log the operation
            logger.debug(
                f"Executing {method} on {model} with args={args}, kwargs={kwargs}"
            )
            
            # Execute via object proxy
            result = self.object_proxy.execute_kw(
                self._database,
                self._uid,
                password_or_token,
                model,
                method,
                args,
                kwargs
            )
            
            logger.debug(f"Operation completed successfully")
            return result
            
        except xmlrpc.client.Fault as e:
            logger.error(f"XML-RPC fault during {method} on {model}: {e}")
            raise OdooConnectionError(
                f"Failed to execute {method} on {model}: {e.faultString}"
            )
        except socket.timeout:
            logger.error(f"Timeout during {method} on {model}")
            raise OdooConnectionError(
                f"Operation timeout after {self.timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Error during {method} on {model}: {e}")
            raise OdooConnectionError(
                f"Failed to execute {method} on {model}: {e}"
            )
    
    def search(self, model: str, domain: List[List[Any]], **kwargs) -> List[int]:
        """Search for records matching a domain.
        
        Args:
            model: The Odoo model name
            domain: Odoo domain filter (e.g., [['is_company', '=', True]])
            **kwargs: Additional parameters (limit, offset, order)
            
        Returns:
            List of record IDs matching the domain
        """
        return self.execute_kw(model, 'search', [domain], kwargs)
    
    def read(self, model: str, ids: List[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Read records by IDs.
        
        Args:
            model: The Odoo model name
            ids: List of record IDs to read
            fields: List of field names to read (None for all fields)
            
        Returns:
            List of dictionaries containing record data
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        return self.execute_kw(model, 'read', [ids], kwargs)
    
    def search_read(self, model: str, domain: List[List[Any]], fields: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        """Search for records and read their data in one operation.
        
        Args:
            model: The Odoo model name
            domain: Odoo domain filter
            fields: List of field names to read (None for all fields)
            **kwargs: Additional parameters (limit, offset, order)
            
        Returns:
            List of dictionaries containing record data
        """
        if fields:
            kwargs['fields'] = fields
        return self.execute_kw(model, 'search_read', [domain], kwargs)
    
    def fields_get(self, model: str, attributes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """Get field definitions for a model.
        
        Args:
            model: The Odoo model name
            attributes: List of field attributes to return
            
        Returns:
            Dictionary mapping field names to their definitions
        """
        kwargs = {}
        if attributes:
            kwargs['attributes'] = attributes
        return self.execute_kw(model, 'fields_get', [], kwargs)
    
    def search_count(self, model: str, domain: List[List[Any]]) -> int:
        """Count records matching a domain.
        
        Args:
            model: The Odoo model name
            domain: Odoo domain filter
            
        Returns:
            Number of records matching the domain
        """
        return self.execute_kw(model, 'search_count', [domain], {})
    
    def get_server_version(self) -> Optional[Dict[str, Any]]:
        """Get Odoo server version information.
        
        Returns:
            Dictionary with version information or None if not connected
        """
        if not self._connected:
            return None
            
        try:
            return self.common_proxy.version()
        except Exception as e:
            logger.error(f"Failed to get server version: {e}")
            return None


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