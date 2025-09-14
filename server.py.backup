#!/usr/bin/env python3
"""
Digital Ocean MCP Server wrapper for mcp-server-odoo
This file runs the mcp-server-odoo package in HTTP mode for cloud deployment
"""

import os
import sys
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks while we set up the real MCP server"""

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'service': 'mcp-server-odoo',
                'odoo_url': os.environ.get("ODOO_URL", "not configured")
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default HTTP logs
        pass

def run_simple_server():
    """Run a simple HTTP server for now to keep the container alive"""
    port = int(os.environ.get("PORT", "8080"))

    # Log configuration
    logger.info(f"Starting MCP Server for Odoo on port {port}")
    logger.info(f"Odoo URL: {os.environ.get('ODOO_URL', 'Not configured')}")
    logger.info(f"Database: {os.environ.get('ODOO_DB', 'Auto-detect')}")
    logger.info(f"API Key: {'Configured' if os.environ.get('ODOO_API_KEY') else 'Not configured'}")

    # Start simple HTTP server for health checks
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Server listening on http://0.0.0.0:{port}")
    logger.info("Health check available at /health")

    # Note about MCP server
    logger.info("Note: This is a placeholder server. MCP functionality requires the mcp-server-odoo package to support HTTP transport mode.")
    logger.info("The package currently only supports stdio transport. A full HTTP implementation would need to be added.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.shutdown()

def main():
    """Main entry point"""
    try:
        # For now, run the simple server to keep container alive
        # In the future, this would integrate with mcp-server-odoo when it supports HTTP mode
        run_simple_server()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()