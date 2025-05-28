# MCP Server for Odoo

A Model Context Protocol (MCP) server that provides AI assistants with secure access to Odoo ERP systems. This server acts as a bridge between AI tools and Odoo, enabling read and write operations on Odoo data while respecting the configured access controls.

## Features

- **Secure Authentication**: Supports both API key and username/password authentication
- **Model Access Control**: Fine-grained control over which Odoo models are accessible
- **MCP Protocol Compliance**: Full implementation of the Model Context Protocol for AI integration
- **Environment-Based Configuration**: Easy setup using environment variables
- **Comprehensive Error Handling**: Clear error messages and proper error categorization
- **Type-Safe Implementation**: Built with Python type hints for reliability

## Prerequisites

- Python 3.10 or higher
- Access to an Odoo instance (16.0+ recommended)
- The Odoo MCP module installed on your Odoo server (see `mcp_server`)
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
# Using uvx (recommended for isolated execution)
uvx mcp-server-odoo

# Or using Python module
python -m mcp_server_odoo

# With custom environment file
ODOO_ENV_FILE=/path/to/.env uvx mcp-server-odoo
```

### Testing with MCP Inspector

The MCP Inspector allows you to test the server's functionality interactively:

```bash
npx @modelcontextprotocol/inspector uvx --from . mcp-server-odoo
```

### Integration with AI Assistants

Once running, the server provides resources that AI assistants can access:

- **Individual Records**: `odoo://res.partner/record/1`
- **Search Operations**: `odoo://res.partner/search?domain=[["is_company","=",true]]`
- **Browse Multiple Records**: `odoo://res.partner/browse?ids=1,2,3`
- **Model Information**: `odoo://res.partner/fields`

## Development

### Project Structure

```
mcp-server-odoo/
├── mcp_server_odoo/
│   ├── __init__.py
│   ├── __main__.py        # Entry point for uvx execution
│   ├── server.py          # FastMCP server implementation
│   └── config.py          # Configuration management
├── tests/
│   ├── test_package_structure.py
│   └── test_config.py
├── .env.example           # Example configuration
├── pyproject.toml         # Package configuration
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

1. **Odoo Module** (`mcp_server`): Installed on your Odoo server, this module provides:
   - Configuration interface for enabling models and setting permissions
   - Security groups for access control
   - REST and XML-RPC endpoints for MCP communication
   - Audit logging capabilities

2. **Python Package** (this package): Runs separately and connects to Odoo via the MCP endpoints:
   - Implements the Model Context Protocol
   - Handles authentication and connection management
   - Formats Odoo data for AI consumption
   - Provides resource URIs for accessing Odoo data

## Security Considerations

- Always use HTTPS in production environments
- Generate unique API keys for each integration
- Configure model access carefully - only enable necessary models
- Use read-only permissions where possible
- Regularly review audit logs for suspicious activity
- Keep both the Odoo module and Python package updated

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure Odoo is running and the URL is correct
2. **Authentication Error**: Verify your API key or credentials are valid
3. **Model Not Found**: Check that the model is enabled in Odoo MCP settings
4. **Permission Denied**: Ensure your user has appropriate permissions in Odoo

### Debug Mode

Enable debug logging for more detailed information:

```bash
ODOO_MCP_LOG_LEVEL=DEBUG uvx mcp-server-odoo
```

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file for details.