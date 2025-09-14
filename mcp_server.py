#!/usr/bin/env python3
"""
MCP Server for Odoo - HTTP Transport Implementation
Provides MCP tools to interact with Odoo via REST API
"""

import os
import sys
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
import aiohttp
from aiohttp import web
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OdooClient:
    """Client for interacting with Odoo REST API"""

    def __init__(self, url: str, api_key: str, db: str = None):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })

    def search_records(self, model: str, domain: List = None, fields: List = None, limit: int = 100):
        """Search records in Odoo"""
        try:
            endpoint = f"{self.url}/mcp/records/{model}/search"
            data = {
                'domain': domain or [],
                'fields': fields or [],
                'limit': limit
            }
            if self.db:
                data['db'] = self.db

            response = self.session.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            return {'error': str(e)}

    def get_record(self, model: str, record_id: int, fields: List = None):
        """Get a single record by ID"""
        try:
            endpoint = f"{self.url}/mcp/records/{model}/{record_id}"
            params = {}
            if fields:
                params['fields'] = ','.join(fields)
            if self.db:
                params['db'] = self.db

            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting record: {e}")
            return {'error': str(e)}

    def create_record(self, model: str, values: Dict):
        """Create a new record"""
        try:
            endpoint = f"{self.url}/mcp/records/{model}"
            data = {'values': values}
            if self.db:
                data['db'] = self.db

            response = self.session.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error creating record: {e}")
            return {'error': str(e)}

    def update_record(self, model: str, record_id: int, values: Dict):
        """Update an existing record"""
        try:
            endpoint = f"{self.url}/mcp/records/{model}/{record_id}"
            data = {'values': values}
            if self.db:
                data['db'] = self.db

            response = self.session.put(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            return {'error': str(e)}

    def delete_record(self, model: str, record_id: int):
        """Delete a record"""
        try:
            endpoint = f"{self.url}/mcp/records/{model}/{record_id}"
            params = {}
            if self.db:
                params['db'] = self.db

            response = self.session.delete(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            return {'error': str(e)}

    def list_models(self):
        """List available models"""
        try:
            endpoint = f"{self.url}/mcp/models"
            params = {}
            if self.db:
                params['db'] = self.db

            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {'error': str(e)}

class MCPServer:
    """MCP Server with HTTP transport"""

    def __init__(self, odoo_client: OdooClient):
        self.odoo_client = odoo_client
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP routes for MCP protocol"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/mcp', self.get_server_info)

    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'service': 'mcp-server-odoo',
            'timestamp': datetime.now().isoformat(),
            'odoo_url': self.odoo_client.url
        })

    async def get_server_info(self, request):
        """Get server information and available tools"""
        return web.json_response({
            'name': 'mcp-server-odoo',
            'version': '1.0.0',
            'protocol': 'mcp',
            'tools': [
                {
                    'name': 'search_records',
                    'description': 'Search for records in an Odoo model',
                    'parameters': {
                        'model': 'string',
                        'domain': 'array (optional)',
                        'fields': 'array (optional)',
                        'limit': 'integer (optional)'
                    }
                },
                {
                    'name': 'get_record',
                    'description': 'Get a single record by ID',
                    'parameters': {
                        'model': 'string',
                        'record_id': 'integer',
                        'fields': 'array (optional)'
                    }
                },
                {
                    'name': 'create_record',
                    'description': 'Create a new record',
                    'parameters': {
                        'model': 'string',
                        'values': 'object'
                    }
                },
                {
                    'name': 'update_record',
                    'description': 'Update an existing record',
                    'parameters': {
                        'model': 'string',
                        'record_id': 'integer',
                        'values': 'object'
                    }
                },
                {
                    'name': 'delete_record',
                    'description': 'Delete a record',
                    'parameters': {
                        'model': 'string',
                        'record_id': 'integer'
                    }
                },
                {
                    'name': 'list_models',
                    'description': 'List available Odoo models',
                    'parameters': {}
                }
            ]
        })

    async def handle_mcp_request(self, request):
        """Handle MCP tool requests"""
        try:
            data = await request.json()
            tool = data.get('tool')
            params = data.get('parameters', {})

            # Route to appropriate handler
            if tool == 'search_records':
                result = self.odoo_client.search_records(
                    model=params.get('model'),
                    domain=params.get('domain'),
                    fields=params.get('fields'),
                    limit=params.get('limit', 100)
                )
            elif tool == 'get_record':
                result = self.odoo_client.get_record(
                    model=params.get('model'),
                    record_id=params.get('record_id'),
                    fields=params.get('fields')
                )
            elif tool == 'create_record':
                result = self.odoo_client.create_record(
                    model=params.get('model'),
                    values=params.get('values')
                )
            elif tool == 'update_record':
                result = self.odoo_client.update_record(
                    model=params.get('model'),
                    record_id=params.get('record_id'),
                    values=params.get('values')
                )
            elif tool == 'delete_record':
                result = self.odoo_client.delete_record(
                    model=params.get('model'),
                    record_id=params.get('record_id')
                )
            elif tool == 'list_models':
                result = self.odoo_client.list_models()
            else:
                return web.json_response(
                    {'error': f'Unknown tool: {tool}'},
                    status=400
                )

            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    def run(self, host='0.0.0.0', port=8080):
        """Run the MCP server"""
        logger.info(f"Starting MCP Server on http://{host}:{port}")
        logger.info(f"Connected to Odoo at: {self.odoo_client.url}")
        logger.info(f"Health check: http://{host}:{port}/health")
        logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
        web.run_app(self.app, host=host, port=port)

def main():
    """Main entry point"""
    # Get configuration from environment
    odoo_url = os.environ.get('ODOO_URL', 'http://localhost:8073')
    odoo_api_key = os.environ.get('ODOO_API_KEY', '')
    odoo_db = os.environ.get('ODOO_DB', '')
    port = int(os.environ.get('PORT', '8080'))

    # Validate configuration
    if not odoo_api_key:
        logger.warning("ODOO_API_KEY not set - API calls may fail")

    # Create Odoo client
    odoo_client = OdooClient(
        url=odoo_url,
        api_key=odoo_api_key,
        db=odoo_db if odoo_db else None
    )

    # Create and run MCP server
    server = MCPServer(odoo_client)
    server.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()