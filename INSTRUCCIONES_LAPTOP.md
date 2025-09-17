# Instrucciones para Configurar MCP-Odoo en tu Laptop

## Paso 1: Instalar UV

Abre una terminal y ejecuta:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Después de la instalación, cierra y abre la terminal nuevamente.

## Paso 2: Localizar el archivo de configuración de Claude Desktop

El archivo está en diferentes ubicaciones según tu sistema operativo:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Paso 3: Editar el archivo de configuración

Abre el archivo con cualquier editor de texto y agrega esta configuración:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "uvx",
      "args": ["mcp-server-odoo"],
      "env": {
        "ODOO_URL": "https://xrtechnology-panama-asch-aampc-23703168.dev.odoo.com",
        "ODOO_API_KEY": "584310b1f097717abdc094a3740fea270b5cda0e",
        "ODOO_DB": "xrtechnology-panama-asch-aampc-23703168"  // REQUERIDO
      }
    }
  }
}
```

**IMPORTANTE**: Si ya tienes otros servidores MCP configurados, agrega "odoo" dentro del objeto "mcpServers" existente, separado por coma:

```json
{
  "mcpServers": {
    "otro-servidor": {
      // configuración existente
    },
    "odoo": {
      "command": "uvx",
      "args": ["mcp-server-odoo"],
      "env": {
        "ODOO_URL": "https://xrtechnology-panama-asch-aampc-23703168.dev.odoo.com",
        "ODOO_API_KEY": "584310b1f097717abdc094a3740fea270b5cda0e",
        "ODOO_DB": "xrtechnology-panama-asch-aampc-23703168"
      }
    }
  }
}
```

## Paso 4: Reiniciar Claude Desktop

1. Cierra completamente Claude Desktop
2. Vuelve a abrirlo
3. Ve a Settings (Configuración)
4. En la sección "MCP Servers" deberías ver:
   - **odoo** con estado "Connected" (verde)

## Paso 5: Probar la conexión

Una vez conectado, puedes probar estos comandos en Claude:

### Comandos de Ejemplo para Probar:

1. **Ver modelos disponibles:**
   "Lista todos los modelos habilitados en Odoo"

2. **Buscar órdenes de compra:**
   "Muestra las últimas 5 órdenes de compra"

3. **Buscar productos:**
   "Lista los productos disponibles"

4. **Ver información de un modelo:**
   "Muestra los campos disponibles del modelo purchase.order"

## Solución de Problemas

### Si aparece "Failed" o "Disconnected":

1. **Verifica que UV esté instalado:**
   ```bash
   uvx --version
   ```
   Si no funciona, reinstala UV.

2. **Prueba la conexión manualmente:**
   ```bash
   export ODOO_URL="https://xrtechnology-panama-asch-aampc-23703168.dev.odoo.com"
   export ODOO_API_KEY="584310b1f097717abdc094a3740fea270b5cda0e"
   export ODOO_DB="xrtechnology-panama-asch-aampc-23703168"
   uvx mcp-server-odoo
   ```

   Deberías ver:
   - "Successfully connected to Odoo"
   - "Successfully authenticated with MCP API key"

3. **Verifica el archivo de configuración:**
   - Asegúrate de que el JSON esté bien formateado (sin errores de sintaxis)
   - Verifica que las comillas sean correctas (" no ")
   - No debe haber comas extra al final

4. **Revisa los logs de Claude Desktop:**
   - En macOS: Ver Console.app y buscar "Claude"
   - En Windows: Event Viewer
   - En Linux: `journalctl -f`

### Si la primera vez descarga paquetes:

Es normal que la primera vez que se ejecuta, uvx descargue el paquete `mcp-server-odoo` y sus dependencias. Esto puede tomar 1-2 minutos. Las siguientes veces será instantáneo.

## Credenciales de Tu Sistema

Estas son las credenciales actuales configuradas:

- **URL de Odoo**: https://xrtechnology-panama-asch-aampc-23703168.dev.odoo.com
- **API Key**: 584310b1f097717abdc094a3740fea270b5cda0e
- **Base de Datos**: xrtechnology-panama-asch-aampc-23703168

## Para Configurar con Otra Instancia de Odoo

Si quieres usar otra instancia de Odoo, simplemente cambia estos valores en el archivo de configuración:

1. **ODOO_URL**: La URL de tu instancia Odoo
2. **ODOO_API_KEY**: Tu API key (se genera en Odoo: Settings → Users → API Keys)
3. **ODOO_DB**: El nombre de tu base de datos

## Notas Importantes

- El cliente MCP se ejecuta **localmente** en tu computadora
- No necesitas instalar Python por separado (uvx lo maneja)
- La conexión es segura mediante HTTPS y API key
- Los datos nunca pasan por servidores de terceros

## Siguiente Paso

Una vez configurado y conectado, puedes empezar a usar Claude para:
- Buscar información en Odoo
- Crear nuevos registros
- Actualizar datos existentes
- Generar reportes
- Analizar información empresarial

Todo mediante lenguaje natural, sin necesidad de navegar por los menús de Odoo.

---

*Si tienes problemas, revisa la documentación completa en DOCUMENTACION_COMPLETA_MCP_ODOO.md*