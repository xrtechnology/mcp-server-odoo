#!/usr/bin/env node
/**
 * MCP Client for Multi-Tenant Odoo Server
 * This client bridges Claude Desktop with the multi-tenant MCP server
 */

const readline = require('readline');
const https = require('https');

// Get configuration from environment
const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'https://mcp-server-odoo-77666f7c4b.ondigitalocean.app/mcp';
const ODOO_URL = process.env.ODOO_URL;
const ODOO_API_KEY = process.env.ODOO_API_KEY;
const ODOO_DB = process.env.ODOO_DB || '';

// Create readline interface for stdio communication
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Log function that writes to stderr to avoid interfering with MCP protocol
function log(message) {
  process.stderr.write(`[MCP Client] ${message}\n`);
}

// Make HTTP request to MCP server
async function callMCPServer(tool, parameters) {
  return new Promise((resolve, reject) => {
    const url = new URL(MCP_SERVER_URL);
    const data = JSON.stringify({
      tool: tool,
      parameters: parameters
    });

    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length,
        'X-Odoo-URL': ODOO_URL,
        'X-Odoo-API-Key': ODOO_API_KEY,
        'X-Odoo-DB': ODOO_DB
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          resolve(result);
        } catch (e) {
          reject(new Error(`Failed to parse response: ${responseData}`));
        }
      });
    });

    req.on('error', (e) => {
      reject(e);
    });

    req.write(data);
    req.end();
  });
}

// Handle MCP protocol messages
async function handleMessage(message) {
  try {
    const request = JSON.parse(message);

    if (request.method === 'initialize') {
      // Respond with server capabilities
      const response = {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          capabilities: {
            tools: {
              search_records: {
                description: 'Search for records in an Odoo model',
                inputSchema: {
                  type: 'object',
                  properties: {
                    model: { type: 'string' },
                    domain: { type: 'array' },
                    fields: { type: 'array' },
                    limit: { type: 'integer' }
                  },
                  required: ['model']
                }
              },
              get_record: {
                description: 'Get a single record by ID',
                inputSchema: {
                  type: 'object',
                  properties: {
                    model: { type: 'string' },
                    record_id: { type: 'integer' },
                    fields: { type: 'array' }
                  },
                  required: ['model', 'record_id']
                }
              },
              create_record: {
                description: 'Create a new record',
                inputSchema: {
                  type: 'object',
                  properties: {
                    model: { type: 'string' },
                    values: { type: 'object' }
                  },
                  required: ['model', 'values']
                }
              },
              update_record: {
                description: 'Update an existing record',
                inputSchema: {
                  type: 'object',
                  properties: {
                    model: { type: 'string' },
                    record_id: { type: 'integer' },
                    values: { type: 'object' }
                  },
                  required: ['model', 'record_id', 'values']
                }
              },
              delete_record: {
                description: 'Delete a record',
                inputSchema: {
                  type: 'object',
                  properties: {
                    model: { type: 'string' },
                    record_id: { type: 'integer' }
                  },
                  required: ['model', 'record_id']
                }
              },
              list_models: {
                description: 'List available Odoo models',
                inputSchema: {
                  type: 'object',
                  properties: {}
                }
              }
            }
          }
        }
      };
      console.log(JSON.stringify(response));

    } else if (request.method === 'tools/call') {
      // Call the MCP server with the tool request
      const tool = request.params.name;
      const parameters = request.params.arguments;

      log(`Calling tool: ${tool}`);

      const result = await callMCPServer(tool, parameters);

      const response = {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }
          ]
        }
      };
      console.log(JSON.stringify(response));

    } else {
      // Unknown method
      const response = {
        jsonrpc: '2.0',
        id: request.id,
        error: {
          code: -32601,
          message: 'Method not found'
        }
      };
      console.log(JSON.stringify(response));
    }
  } catch (e) {
    log(`Error handling message: ${e.message}`);
    // Send error response if we have a request id
    try {
      const request = JSON.parse(message);
      if (request.id) {
        const response = {
          jsonrpc: '2.0',
          id: request.id,
          error: {
            code: -32603,
            message: e.message
          }
        };
        console.log(JSON.stringify(response));
      }
    } catch (parseError) {
      // Couldn't even parse the request
      log(`Failed to parse request: ${message}`);
    }
  }
}

// Main execution
log('Starting MCP Client for Multi-Tenant Odoo Server');
log(`Server URL: ${MCP_SERVER_URL}`);
log(`Odoo URL: ${ODOO_URL}`);
log(`Database: ${ODOO_DB || 'auto-detect'}`);

// Check for required credentials
if (!ODOO_URL || !ODOO_API_KEY) {
  log('ERROR: Missing required environment variables ODOO_URL or ODOO_API_KEY');
  process.exit(1);
}

// Listen for messages from Claude Desktop
rl.on('line', (line) => {
  handleMessage(line);
});

// Handle shutdown
process.on('SIGINT', () => {
  log('Shutting down MCP client');
  process.exit(0);
});