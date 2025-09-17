#!/usr/bin/env python3
"""
MCP Server Bridge Multi-tenant para Digital Ocean
Conecta Claude Desktop con múltiples instancias de Odoo
"""

import os
import json
import logging
import xmlrpc.client
from aiohttp import web
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OdooXMLRPCClient:
    """Cliente para conectar con Odoo via XML-RPC usando el módulo MCP"""

    def __init__(self, url: str, api_key: str, db: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.db = db
        self.uid = None

        # Endpoints XML-RPC del módulo MCP
        self.common = xmlrpc.client.ServerProxy(f'{self.url}/mcp/xmlrpc/common')
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/mcp/xmlrpc/object')

    def authenticate(self):
        """Autenticar con API key"""
        try:
            # El módulo MCP maneja autenticación por API key en headers
            # Para XML-RPC, necesitamos obtener el UID primero
            version = self.common.version()
            logger.info(f"Connected to Odoo version: {version}")
            # En producción, el UID viene del módulo MCP
            self.uid = 2  # Usuario API típico
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def list_models(self):
        """Listar modelos habilitados en MCP"""
        try:
            # Usar el endpoint REST del módulo MCP para esto
            import requests
            response = requests.get(
                f"{self.url}/mcp/models",
                headers={"X-API-Key": self.api_key}
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"Failed to list models: {response.text}"}
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {"error": str(e)}

    def search_records(self, model: str, domain: list = None, fields: list = None, limit: int = 100):
        """Buscar registros usando XML-RPC"""
        try:
            if not self.uid:
                self.authenticate()

            # Búsqueda via XML-RPC
            record_ids = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                model, 'search',
                [domain or []],
                {'limit': limit}
            )

            # Leer los registros encontrados
            if record_ids:
                records = self.models.execute_kw(
                    self.db, self.uid, self.api_key,
                    model, 'read',
                    [record_ids],
                    {'fields': fields or []}
                )
                return {"success": True, "data": records}

            return {"success": True, "data": []}

        except xmlrpc.client.Fault as fault:
            logger.error(f"XML-RPC Fault: {fault}")
            return {"error": f"Odoo error: {fault.faultString}"}
        except Exception as e:
            logger.error(f"Error searching records: {e}")
            return {"error": str(e)}

    def get_record(self, model: str, record_id: int, fields: list = None):
        """Obtener un registro específico"""
        try:
            if not self.uid:
                self.authenticate()

            records = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                model, 'read',
                [[record_id]],
                {'fields': fields or []}
            )

            if records:
                return {"success": True, "data": records[0]}
            return {"error": "Record not found"}

        except Exception as e:
            logger.error(f"Error getting record: {e}")
            return {"error": str(e)}

    def create_record(self, model: str, values: dict):
        """Crear un nuevo registro"""
        try:
            if not self.uid:
                self.authenticate()

            record_id = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                model, 'create',
                [values]
            )

            return {"success": True, "data": {"id": record_id}}

        except Exception as e:
            logger.error(f"Error creating record: {e}")
            return {"error": str(e)}

    def update_record(self, model: str, record_id: int, values: dict):
        """Actualizar un registro existente"""
        try:
            if not self.uid:
                self.authenticate()

            result = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                model, 'write',
                [[record_id], values]
            )

            return {"success": True, "data": {"updated": result}}

        except Exception as e:
            logger.error(f"Error updating record: {e}")
            return {"error": str(e)}

    def delete_record(self, model: str, record_id: int):
        """Eliminar un registro"""
        try:
            if not self.uid:
                self.authenticate()

            result = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                model, 'unlink',
                [[record_id]]
            )

            return {"success": True, "data": {"deleted": result}}

        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            return {"error": str(e)}


class MCPMultiTenantServer:
    """Servidor MCP Multi-tenant para Digital Ocean"""

    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.clients_cache = {}

    def setup_routes(self):
        """Configurar rutas HTTP"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/mcp/info', self.get_server_info)

    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'service': 'mcp-server-odoo-multitenant',
            'timestamp': datetime.now().isoformat(),
            'mode': 'multi-tenant',
            'description': 'Bridge server for MCP-Odoo integration',
            'version': '2.0.0'
        })

    async def get_server_info(self, request):
        """Información del servidor"""
        return web.json_response({
            'name': 'MCP Odoo Bridge Server',
            'version': '2.0.0',
            'mode': 'multi-tenant',
            'supported_tools': [
                'list_models',
                'search_records',
                'get_record',
                'create_record',
                'update_record',
                'delete_record'
            ],
            'required_headers': [
                'X-Odoo-URL',
                'X-Odoo-API-Key',
                'X-Odoo-DB'
            ]
        })

    async def handle_mcp_request(self, request):
        """Manejar peticiones MCP"""
        try:
            # Obtener credenciales de headers
            odoo_url = request.headers.get('X-Odoo-URL')
            odoo_api_key = request.headers.get('X-Odoo-API-Key')
            odoo_db = request.headers.get('X-Odoo-DB')

            # Validar credenciales
            if not all([odoo_url, odoo_api_key, odoo_db]):
                return web.json_response(
                    {
                        'error': 'Missing required headers',
                        'required': ['X-Odoo-URL', 'X-Odoo-API-Key', 'X-Odoo-DB']
                    },
                    status=400
                )

            # Crear o reusar cliente
            client_key = f"{odoo_url}:{odoo_db}"
            if client_key not in self.clients_cache:
                self.clients_cache[client_key] = OdooXMLRPCClient(
                    odoo_url, odoo_api_key, odoo_db
                )
                self.clients_cache[client_key].authenticate()

            client = self.clients_cache[client_key]

            # Procesar petición
            data = await request.json()
            tool = data.get('tool')
            params = data.get('parameters', {})

            # Ejecutar herramienta
            tool_handlers = {
                'list_models': lambda: client.list_models(),
                'search_records': lambda: client.search_records(**params),
                'get_record': lambda: client.get_record(**params),
                'create_record': lambda: client.create_record(**params),
                'update_record': lambda: client.update_record(**params),
                'delete_record': lambda: client.delete_record(**params),
            }

            if tool not in tool_handlers:
                return web.json_response(
                    {'error': f'Unknown tool: {tool}'},
                    status=400
                )

            result = tool_handlers[tool]()
            return web.json_response(result)

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    def run(self, host='0.0.0.0', port=8080):
        """Ejecutar servidor"""
        logger.info(f"Starting Multi-Tenant MCP Server on http://{host}:{port}")
        logger.info("Each client must provide credentials via headers:")
        logger.info("  X-Odoo-URL: Your Odoo instance URL")
        logger.info("  X-Odoo-API-Key: Your API key")
        logger.info("  X-Odoo-DB: Your database name")
        web.run_app(self.app, host=host, port=port)


def main():
    """Entry point"""
    port = int(os.environ.get('PORT', '8080'))
    server = MCPMultiTenantServer()
    server.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()