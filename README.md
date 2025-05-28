# MCP Server for Odoo

A Model Context Protocol (MCP) server that provides AI assistants with access to Odoo ERP systems.

## Installation

```bash
# Install the package
uv pip install -e .

# Or install with development dependencies
uv pip install -e ".[dev]"
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Odoo connection details:
   - `ODOO_URL`: Your Odoo server URL
   - `ODOO_DB`: Database name
   - `ODOO_USERNAME`: Username for authentication
   - `ODOO_PASSWORD`: Password (or use `ODOO_API_KEY` instead)

## Usage

### Running the server

```bash
# Using uvx (recommended)
uvx mcp-server-odoo

# Or using Python module
python -m mcp_server_odoo
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uvx --from /path/to/mcp-server-odoo mcp-server-odoo
```

## Development

### Running tests

```bash
# Run all tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_package_structure.py -v
```

### Code formatting and linting

```bash
# Format code
uv run black .

# Run linter
uv run ruff check .

# Type checking
uv run mypy .
```

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file for details.