#!/usr/bin/env node
/**
 * Bridge local para conectar Claude Desktop con el servidor MCP remoto en Digital Ocean
 */

const readline = require('readline');
const https = require('https');

const MCP_SERVER_URL = 'https://odoo-mcp-doonet-c7qe3.ondigitalocean.app/mcp';
const ODOO_URL = 'https://xrtechnology-panama-asch-aampc-23703168.dev.odoo.com';
const ODOO_API_KEY = '584310b1f097717abdc094a3740fea270b5cda0e';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

function log(message) {
  process.stderr.write(`[Bridge] ${message}\n`);
}

async function callRemoteServer(tool, parameters) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify({ tool, parameters });
    const url = new URL(MCP_SERVER_URL);

    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length,
        'X-Odoo-URL': ODOO_URL,
        'X-Odoo-API-Key': ODOO_API_KEY,
        'X-Odoo-DB': ''
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => { responseData += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(responseData));
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function handleMessage(message) {
  try {
    const request = JSON.parse(message);

    if (request.method === 'initialize') {
      const response = {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          capabilities: {
            tools: {
              list_models: { description: 'List available Odoo models' },
              search_records: { description: 'Search records in Odoo' },
              get_record: { description: 'Get a single record' },
              create_record: { description: 'Create a new record' },
              update_record: { description: 'Update a record' },
              delete_record: { description: 'Delete a record' }
            }
          }
        }
      };
      console.log(JSON.stringify(response));
    } else if (request.method === 'tools/call') {
      const result = await callRemoteServer(request.params.name, request.params.arguments);
      const response = {
        jsonrpc: '2.0',
        id: request.id,
        result: {
          content: [{
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }]
        }
      };
      console.log(JSON.stringify(response));
    }
  } catch (e) {
    log(`Error: ${e.message}`);
  }
}

log('Starting MCP Bridge to Digital Ocean');
rl.on('line', handleMessage);