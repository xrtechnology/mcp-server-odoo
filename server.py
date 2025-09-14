#!/usr/bin/env python3
"""
Digital Ocean MCP Server wrapper for mcp-server-odoo
This file runs the mcp-server-odoo package in HTTP mode for cloud deployment
"""

import os
import sys
import subprocess

def main():
    # Get port from environment variable (Digital Ocean sets this)
    port = os.environ.get("PORT", "8080")

    # Get Odoo configuration from environment variables
    odoo_url = os.environ.get("ODOO_URL", "http://localhost:8073")
    odoo_api_key = os.environ.get("ODOO_API_KEY", "")
    odoo_db = os.environ.get("ODOO_DB", "")

    print(f"Starting MCP Server for Odoo on port {port}")
    print(f"Connecting to Odoo at: {odoo_url}")
    print(f"Database: {odoo_db if odoo_db else 'Auto-detect'}")

    # Run mcp-server-odoo in HTTP transport mode
    cmd = [
        sys.executable, "-m", "mcp_server_odoo",
        "--transport", "streamable-http",
        "--port", port,
        "--host", "0.0.0.0"
    ]

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["ODOO_URL"] = odoo_url
    env["ODOO_API_KEY"] = odoo_api_key
    env["ODOO_DB"] = odoo_db

    # Execute the command
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    main()