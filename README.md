# MCP Server for Odoo

A Model Context Protocol (MCP) server that provides AI assistants with secure access to Odoo ERP systems. This server acts as a bridge between AI tools and Odoo, enabling read and write operations on Odoo data while respecting the configured access controls.

**Note**: This package is currently in development. The MCP protocol implementation is not yet complete.

## Features

### Implemented
- **Dual Authentication**: Supports both API key and username/password authentication
- **Database Discovery**: Automatic database detection with intelligent selection
- **XML-RPC Communication**: Full XML-RPC integration via MCP-specific endpoints
- **Model Access Control**: Integration with Odoo MCP module for permission checking
- **Environment Configuration**: Easy setup using `.env` files
- **Connection Management**: Robust connection handling with health checks
- **Comprehensive Testing**: 89% test coverage with unit and integration tests

### In Progress
- **MCP Protocol Implementation**: FastMCP server implementation
- **Resource URI Handling**: Support for odoo:// URI scheme
- **Data Formatting**: Field-type specific formatting for AI consumption

## Prerequisites

- Python 3.10 or higher
- Access to an Odoo instance (18.0+ recommended)
- The Odoo MCP module installed on your Odoo server (see `/odoo-apps/mcp_server`)
- An API key generated in Odoo (Settings > Users > API Keys)

## Installation

```bash
# Install using uv (recommended)
uv pip install mcp-server-odoo

# Or install from source
git clone https://github.com/ivnvxd/mcp-server-odoo.git
cd mcp-server-odoo
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Odoo connection details:

   ```env
   # Required: Odoo server URL
   ODOO_URL=http://localhost:8069
   
   # Authentication (use one method):
   # Method 1: API Key (preferred)
   ODOO_API_KEY=your-api-key-here
   
   # Method 2: Username/Password
   # ODOO_USER=your-username
   # ODOO_PASSWORD=your-password
   
   # Optional settings:
   ODOO_DB=your-database-name  # Auto-detected if not specified
   ODOO_MCP_LOG_LEVEL=INFO     # DEBUG, INFO, WARNING, ERROR, CRITICAL
   ODOO_MCP_DEFAULT_LIMIT=10   # Default pagination limit
   ODOO_MCP_MAX_LIMIT=100      # Maximum allowed limit
   ```

## Usage

### Running the Server

**Note**: The MCP server implementation is not yet complete. The following shows current capabilities:

```bash
# Test connection and authentication
python -m mcp_server_odoo

# With custom environment file
ODOO_ENV_FILE=/path/to/.env python -m mcp_server_odoo
```

### Current Capabilities

The package currently provides:

1. **Connection Management**:
   ```python
   from mcp_server_odoo import OdooConnection, load_config
   
   config = load_config()
   with OdooConnection(config) as conn:
       conn.authenticate()
       
       # Search for partners
       partner_ids = conn.search("res.partner", [["is_company", "=", True]])
       
       # Read partner data
       partners = conn.read("res.partner", partner_ids, ["name", "email"])
   ```

2. **Access Control**:
   ```python
   from mcp_server_odoo import AccessController
   
   controller = AccessController(config)
   
   # Check if model is enabled
   if controller.is_model_enabled("res.partner"):
       # Check specific operation
       allowed, msg = controller.check_operation_allowed("res.partner", "read")
   ```

### Testing with MCP Inspector

The MCP Inspector integration is planned but not yet available:

```bash
# Coming soon
npx @modelcontextprotocol/inspector uvx --from . mcp-server-odoo
```

## Development

### Project Structure

```
mcp-server-odoo/
├── mcp_server_odoo/
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── server.py               # FastMCP server (in progress)
│   ├── config.py               # Configuration management
│   ├── odoo_connection.py      # Odoo XML-RPC connection
│   └── access_control.py       # Model access control
├── tests/
│   ├── test_config.py
│   ├── test_odoo_connection_basic.py
│   ├── test_database_discovery.py
│   ├── test_authentication.py
│   ├── test_xmlrpc_operations.py
│   ├── test_access_control.py
│   └── test_package_structure.py
├── .env.example                # Example configuration
├── pyproject.toml              # Package configuration
└── README.md
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_config.py -v

# Run with coverage report
uv run pytest --cov=mcp_server_odoo --cov-report=term-missing
```

### Code Quality

```bash
# Format code with black
uv run black .

# Check code style with ruff
uv run ruff check .

# Type checking with mypy
uv run mypy .

# Run all checks
uv run black . && uv run ruff check . && uv run mypy .
```

## Architecture

The MCP Server for Odoo consists of two main components:

1. **Odoo Module** (`/odoo-apps/mcp_server`): Installed on your Odoo server (18.0+), this module provides:
   - Configuration interface for enabling models and setting permissions
   - Security groups (MCP Administrator, MCP User) for access control
   - REST API endpoints:
     - `/mcp/health` - Health check
     - `/mcp/auth/validate` - API key validation
     - `/mcp/models` - List enabled models
     - `/mcp/models/{model}/access` - Check model permissions
   - XML-RPC endpoints with MCP-specific access controls:
     - `/mcp/xmlrpc/common` - Authentication
     - `/mcp/xmlrpc/db` - Database operations
     - `/mcp/xmlrpc/object` - Model operations

2. **Python Package** (this package): Runs separately and connects to Odoo:
   - **Implemented**: Connection management, authentication, XML-RPC operations, access control
   - **In Progress**: MCP protocol implementation via FastMCP
   - **Planned**: Resource URI handling, data formatting for AI consumption

## Security Considerations

- Always use HTTPS in production environments
- Generate unique API keys for each integration
- Configure model access carefully - only enable necessary models
- Use read-only permissions where possible
- Regularly review audit logs for suspicious activity
- Keep both the Odoo module and Python package updated

## Troubleshooting

### Common Issues

1. **Connection Failed**: 
   - Ensure Odoo is running and accessible
   - Verify the URL in your `.env` file
   - Check that MCP endpoints are available (test with `/mcp/health`)

2. **Authentication Error**: 
   - Verify your API key is valid and active in Odoo
   - For username/password auth, ensure credentials are correct
   - API key must have appropriate scope (read/write)

3. **Model Not Found**: 
   - Check that the model is enabled in Odoo MCP settings
   - Navigate to Settings > MCP Server > Enabled Models in Odoo
   - Ensure the model name is spelled correctly (e.g., `res.partner`)

4. **Permission Denied**: 
   - Verify the model has the required operation enabled (read/write/create/unlink)
   - Check user's security group (MCP User or MCP Administrator)
   - Review model-specific permissions in Odoo

### Debug Mode

Enable debug logging for more detailed information:

```bash
ODOO_MCP_LOG_LEVEL=DEBUG python -m mcp_server_odoo
```

### Testing Connection

Test your setup with this simple script:

```python
from mcp_server_odoo import OdooConnection, AccessController, load_config

# Load configuration
config = load_config()

# Test connection and authentication
with OdooConnection(config) as conn:
    print("✓ Connected to Odoo")
    
    conn.authenticate()
    print(f"✓ Authenticated as user ID: {conn.uid}")
    print(f"✓ Using database: {conn.database}")
    
    # Test access control
    controller = AccessController(config)
    models = controller.get_enabled_models()
    print(f"✓ Found {len(models)} enabled models")
```

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file for details.