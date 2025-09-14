#!/usr/bin/env python3
"""
MCP Client Wrapper for Multi-tenant Server
This wrapper adds Odoo credentials to each request
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict
import aiohttp

class MCPClientWrapper:
    """Wrapper that adds credentials to MCP requests"""

    def __init__(self):
        # Get credentials from environment
        self.odoo_url = os.environ.get('ODOO_URL')
        self.odoo_api_key = os.environ.get('ODOO_API_KEY')
        self.odoo_db = os.environ.get('ODOO_DB', '')
        self.mcp_server = os.environ.get('MCP_SERVER_URL', 'https://odoo-mcp-doonet.ondigitalocean.app')

        if not self.odoo_url or not self.odoo_api_key:
            print("Error: ODOO_URL and ODOO_API_KEY must be set in environment variables")
            sys.exit(1)

    async def send_request(self, tool: str, parameters: Dict[str, Any]) -> Dict:
        """Send request to MCP server with credentials"""

        headers = {
            'Content-Type': 'application/json',
            'X-Odoo-URL': self.odoo_url,
            'X-Odoo-API-Key': self.odoo_api_key,
            'X-Odoo-DB': self.odoo_db
        }

        data = {
            'tool': tool,
            'parameters': parameters
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.mcp_server}/mcp',
                headers=headers,
                json=data
            ) as response:
                return await response.json()

    async def process_stdio(self):
        """Process requests from stdin and send to MCP server"""
        while True:
            try:
                # Read from stdin (from Claude)
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break

                # Parse JSON request
                request = json.loads(line.strip())

                # Extract tool and parameters
                tool = request.get('tool')
                parameters = request.get('parameters', {})

                # Send to MCP server with credentials
                result = await self.send_request(tool, parameters)

                # Return result to stdout (to Claude)
                print(json.dumps(result))
                sys.stdout.flush()

            except Exception as e:
                error_response = {'error': str(e)}
                print(json.dumps(error_response))
                sys.stdout.flush()

async def main():
    """Main entry point"""
    wrapper = MCPClientWrapper()
    await wrapper.process_stdio()

if __name__ == '__main__':
    asyncio.run(main())