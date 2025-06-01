# MCP Server for Odoo

[![CI](https://github.com/ivnvxd/mcp-server-odoo/actions/workflows/ci.yml/badge.svg)](https://github.com/ivnvxd/mcp-server-odoo/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ivnvxd/mcp-server-odoo/branch/main/graph/badge.svg)](https://codecov.io/gh/ivnvxd/mcp-server-odoo)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

A Model Context Protocol (MCP) server that provides AI assistants with secure access to Odoo ERP systems. This server enables AI tools like Claude to interact with Odoo data through a standardized interface, supporting both read operations and basic tools for data retrieval.

## Features

### Implemented
- **Dual Authentication**: Supports both API key and username/password authentication
- **Database Discovery**: Automatic database detection with intelligent selection
- **XML-RPC Communication**: Full XML-RPC integration via MCP-specific endpoints
- **Model Access Control**: Integration with Odoo MCP module for permission checking
- **Environment Configuration**: Easy setup using `.env` files
- **Connection Management**: Robust connection handling with health checks
- **FastMCP Server**: Complete MCP protocol implementation with stdio transport
- **Resource URI Handling**: Complete odoo:// URI schema implementation
- **Data Formatting**: LLM-optimized hierarchical text formatting
- **Resource Operations**:
  - Individual record retrieval (`odoo://{model}/record/{id}`)
  - Search with domain filtering (`odoo://{model}/search`)
  - Browse multiple records (`odoo://{model}/browse?ids=1,2,3`)
  - Count records (`odoo://{model}/count`)
  - Field introspection (`odoo://{model}/fields`)
- **MCP Tools**:
  - `search_records` - Search for records with filters
  - `get_record` - Retrieve a specific record by ID
  - `list_models` - List all MCP-enabled models
- **Comprehensive Testing**: 89% test coverage with 223 tests

### Not Yet Implemented
- **Write Operation Tools**: create_record, update_record, delete_record
- **Advanced Features**: Prompts, performance optimization, webhook support

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

```bash
# Run the MCP server
uvx mcp-server-odoo

# Or with Python
python -m mcp_server_odoo

# With custom environment file
ODOO_ENV_FILE=/path/to/.env python -m mcp_server_odoo

# Show help
python -m mcp_server_odoo --help

# Show version
python -m mcp_server_odoo --version
```

### MCP Resources and Tools

The server provides both resources (for data retrieval) and tools (for operations):

#### Resources
Resources are accessed via URI patterns and return formatted data:

- **Get Record**: `odoo://res.partner/record/1`
- **Search**: `odoo://res.partner/search?domain=[["is_company","=",true]]&limit=10`
- **Browse**: `odoo://res.partner/browse?ids=1,2,3`
- **Count**: `odoo://res.partner/count?domain=[["is_company","=",true]]`
- **Fields**: `odoo://res.partner/fields`

#### Tools
Tools provide programmatic access to Odoo data:

- **search_records**: Search with filters and pagination
- **get_record**: Retrieve a specific record by ID
- **list_models**: List all MCP-enabled models

### Example Usage

```python
from mcp_server_odoo import OdooConnection, AccessController, load_config

# Load configuration
config = load_config()

# Test connection
with OdooConnection(config) as conn:
    conn.authenticate()
    
    # Search for partners
    partner_ids = conn.search("res.partner", [["is_company", "=", True]])
    
    # Read partner data
    partners = conn.read("res.partner", partner_ids, ["name", "email"])
    
    # Check access control
    controller = AccessController(config)
    models = controller.get_enabled_models()
    print(f"Found {len(models)} enabled models")
```

### Testing with MCP Inspector

```bash
# Test the MCP server with Inspector
npx @modelcontextprotocol/inspector python -m mcp_server_odoo

# Or with UV
npx @modelcontextprotocol/inspector uvx --from . mcp-server-odoo
```

## Development

### Project Structure

```
mcp-server-odoo/
├── mcp_server_odoo/
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── server.py               # FastMCP server implementation
│   ├── config.py               # Configuration management
│   ├── odoo_connection.py      # Odoo XML-RPC connection
│   ├── access_control.py       # Model access control
│   ├── resources.py            # MCP resource handlers
│   ├── tools.py                # MCP tool handlers
│   ├── formatters.py           # Data formatting for LLMs
│   └── uri_schema.py           # URI schema implementation
├── tests/
│   └── ...
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

# Run only unit tests (skip integration)
uv run pytest -k "not Integration"

# Run with coverage report
uv run pytest --cov=mcp_server_odoo --cov-report=term-missing

# Run MCP protocol validation tests
cd tests
./run_mcp_tests.sh
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
   - **Implemented**: Complete MCP server with resources and tools
   - **Resources**: All 5 operations (record, search, browse, count, fields)
   - **Tools**: Basic read operations (search_records, get_record, list_models)
   - **Features**: Authentication, access control, data formatting, pagination

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