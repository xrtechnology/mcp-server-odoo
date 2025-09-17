#!/usr/bin/env node
/**
 * Cliente MCP Bridge - Conecta Claude Desktop con servidor remoto
 *
 * Este archivo debe ser instalado localmente por cada cliente
 * Conecta Claude Desktop con el servidor multi-tenant en Digital Ocean
 */

const readline = require('readline');
const https = require('https');

// CONFIGURACIÓN - Los clientes deben actualizar estos valores
const CONFIG = {
  // URL del servidor bridge en Digital Ocean
  BRIDGE_SERVER: process.env.BRIDGE_SERVER || 'https://odoo-mcp-doonet-c7qe3.ondigitalocean.app/mcp',

  // Credenciales del cliente - CADA CLIENTE DEBE PONER SUS PROPIAS CREDENCIALES
  ODOO_URL: process.env.ODOO_URL || 'https://tu-instancia.odoo.com',
  ODOO_API_KEY: process.env.ODOO_API_KEY || 'tu-api-key-aqui',
  ODOO_DB: process.env.ODOO_DB || 'tu-base-datos'  // REQUERIDO para XML-RPC
};

// Crear interfaz para comunicación con Claude Desktop
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Logger para debug (escribe a stderr para no interferir con MCP)
function log(message) {
  if (process.env.DEBUG === 'true') {
    process.stderr.write(`[MCP Bridge] ${new Date().toISOString()} - ${message}\n`);
  }
}

// Hacer llamada al servidor bridge
async function callBridgeServer(tool, parameters) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ tool, parameters });
    const url = new URL(CONFIG.BRIDGE_SERVER);

    const options = {
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
        // Enviar credenciales en headers
        'X-Odoo-URL': CONFIG.ODOO_URL,
        'X-Odoo-API-Key': CONFIG.ODOO_API_KEY,
        'X-Odoo-DB': CONFIG.ODOO_DB
      }
    };

    log(`Calling bridge server: ${tool}`);

    const req = https.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        try {
          const result = JSON.parse(responseData);
          log(`Response received: ${res.statusCode}`);
          resolve(result);
        } catch (e) {
          log(`Error parsing response: ${e.message}`);
          reject(new Error(`Failed to parse response: ${responseData}`));
        }
      });
    });

    req.on('error', (e) => {
      log(`Request error: ${e.message}`);
      reject(e);
    });

    req.write(data);
    req.end();
  });
}

// Manejar mensajes del protocolo MCP
async function handleMessage(message) {
  try {
    const request = JSON.parse(message);
    log(`Received MCP request: ${request.method}`);

    if (request.method === 'initialize') {
      // Responder con capacidades del servidor
      const response = {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {
              list_models: {
                description: 'List all MCP-enabled models in Odoo',
                inputSchema: {
                  type: 'object',
                  properties: {}
                }
              },
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
                description: 'Get a specific record by ID',
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
              }
            }
          },
          serverInfo: {
            name: 'MCP Odoo Bridge Client',
            version: '1.0.0'
          }
        }
      };
      console.log(JSON.stringify(response));

    } else if (request.method === 'notifications/initialized') {
      // Cliente inicializado, no responder
      log('Client initialized');

    } else if (request.method === 'tools/call') {
      // Llamar herramienta
      const tool = request.params.name;
      const args = request.params.arguments || {};

      log(`Calling tool: ${tool}`);

      try {
        const result = await callBridgeServer(tool, args);

        const response = {
          jsonrpc: '2.0',
          id: request.id,
          result: {
            content: [
              {
                type: 'text',
                text: typeof result === 'string' ? result : JSON.stringify(result, null, 2)
              }
            ]
          }
        };
        console.log(JSON.stringify(response));

      } catch (error) {
        const response = {
          jsonrpc: '2.0',
          id: request.id,
          error: {
            code: -32603,
            message: error.message
          }
        };
        console.log(JSON.stringify(response));
      }

    } else {
      // Método desconocido
      log(`Unknown method: ${request.method}`);
      if (request.id) {
        const response = {
          jsonrpc: '2.0',
          id: request.id,
          error: {
            code: -32601,
            message: `Method not found: ${request.method}`
          }
        };
        console.log(JSON.stringify(response));
      }
    }
  } catch (e) {
    log(`Error handling message: ${e.message}`);
  }
}

// Verificar configuración al inicio
function checkConfiguration() {
  const errors = [];

  if (CONFIG.ODOO_URL === 'https://tu-instancia.odoo.com') {
    errors.push('ODOO_URL not configured - update with your Odoo instance URL');
  }
  if (CONFIG.ODOO_API_KEY === 'tu-api-key-aqui') {
    errors.push('ODOO_API_KEY not configured - update with your API key');
  }
  if (CONFIG.ODOO_DB === 'tu-base-datos') {
    errors.push('ODOO_DB not configured - update with your database name');
  }

  if (errors.length > 0) {
    console.error('Configuration errors:');
    errors.forEach(err => console.error(`  - ${err}`));
    console.error('\nPlease update the configuration in this file or set environment variables.');
    process.exit(1);
  }
}

// Inicio del programa
log('Starting MCP Bridge Client');
log(`Bridge Server: ${CONFIG.BRIDGE_SERVER}`);
log(`Odoo URL: ${CONFIG.ODOO_URL}`);
log(`Database: ${CONFIG.ODOO_DB}`);

// Verificar configuración
checkConfiguration();

// Escuchar mensajes de Claude Desktop
rl.on('line', (line) => {
  handleMessage(line);
});

// Manejar cierre limpio
process.on('SIGINT', () => {
  log('Shutting down MCP Bridge Client');
  process.exit(0);
});

process.on('SIGTERM', () => {
  log('Shutting down MCP Bridge Client');
  process.exit(0);
});