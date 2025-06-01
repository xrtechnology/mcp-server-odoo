#!/bin/bash
# Script to run MCP client validation tests with proper setup

echo "MCP Client Validation Test Runner"
echo "================================="
echo ""
echo "Prerequisites:"
echo "1. Odoo server must be running at localhost:8069"
echo "2. MCP module must be installed in Odoo"
echo "3. API key must be valid"
echo ""

# Check if Odoo is running
echo -n "Checking Odoo server... "
if curl -s http://localhost:8069/mcp/health > /dev/null; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    echo "Error: Odoo server is not running or MCP module is not installed"
    echo "Please start Odoo with: "
    echo "  /Users/ve/dev/src/tmp/odoo/odoo/.venv/bin/python /Users/ve/dev/src/tmp/odoo/odoo/odoo-bin \\"
    echo "    --config=/Users/ve/dev/src/code/odoo_mcp_server/odoo.conf \\"
    echo "    -d mcp -u mcp_server --dev=all"
    exit 1
fi

# Set up environment
export ODOO_URL=http://localhost:8069
export ODOO_DB=mcp
export ODOO_API_KEY=0ef5b399e9ee9c11b053dfb6eeba8de473c29fcd
export ODOO_MCP_LOG_LEVEL=INFO

# Enable MCP tests by setting environment variable
export RUN_MCP_TESTS=1

echo ""
echo "Configuration:"
echo "  ODOO_URL: $ODOO_URL"
echo "  ODOO_DB: $ODOO_DB"
echo "  ODOO_API_KEY: ${ODOO_API_KEY:0:10}..."
echo "  RUN_MCP_TESTS: $RUN_MCP_TESTS"
echo ""

# Change to the mcp-server-odoo directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Run tests
echo "Running MCP client validation tests..."
echo ""

uv run pytest tests/test_mcp_client_validation.py -v -s -x --tb=short

echo ""
echo "To test with MCP Inspector instead, run:"
echo "  npx @modelcontextprotocol/inspector python -m mcp_server_odoo"