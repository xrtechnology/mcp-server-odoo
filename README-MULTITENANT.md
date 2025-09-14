# MCP Server Odoo - Multi-Tenant Bridge 🌐

Un servidor MCP **multi-tenant** desplegado en Digital Ocean que permite a múltiples usuarios de Claude Desktop conectarse a sus propias instancias de Odoo a través de un único servidor centralizado.

## 🎯 ¿Qué es esto?

Este NO es el cliente MCP original. Es un **servidor puente** que:
- ✅ Permite que MÚLTIPLES clientes usen el mismo servidor
- ✅ Cada cliente envía SUS propias credenciales de Odoo
- ✅ Un solo deploy sirve a todos los clientes
- ✅ No necesitas instalar nada localmente (solo configurar Claude)

## 🏗️ Arquitectura

```
[Claude Cliente A] → [Servidor MCP en DO] → [Odoo Cliente A]
[Claude Cliente B] → [Servidor MCP en DO] → [Odoo Cliente B]
[Claude Cliente C] → [Servidor MCP en DO] → [Odoo Cliente C]
```

## 📋 Para el ADMINISTRADOR (tú que despliegas el servidor)

### Desplegar en Digital Ocean:

1. **Fork este repositorio**
2. **En Digital Ocean App Platform:**
   - Create App → Git Repository
   - Conecta tu fork
   - El servidor se desplegará automáticamente

3. **Variables de entorno (solo necesitas una):**
   ```
   PORT = 8080
   ```

4. **Tu servidor estará en:**
   ```
   https://tu-app.ondigitalocean.app
   ```

### Verificar que funciona:
```bash
curl https://tu-app.ondigitalocean.app/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "mcp-server-odoo-multi-tenant",
  "mode": "multi-tenant",
  "info": "Send Odoo credentials via headers..."
}
```

## 👥 Para los CLIENTES (usuarios de Claude)

### Configuración en Claude Desktop:

Cada cliente debe configurar su `claude_desktop_config.json` con SUS propias credenciales:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python3",
      "args": ["/ruta/a/mcp_client_wrapper.py"],
      "env": {
        "MCP_SERVER_URL": "https://tu-servidor-mcp.ondigitalocean.app",
        "ODOO_URL": "https://MI-INSTANCIA.odoo.com",
        "ODOO_API_KEY": "MI-API-KEY-PERSONAL",
        "ODOO_DB": "MI-BASE-DE-DATOS"
      }
    }
  }
}
```

### Cada cliente necesita:

1. **Su propia URL de Odoo** (`ODOO_URL`)
2. **Su propia API Key** (`ODOO_API_KEY`) - Generada en su Odoo
3. **Su nombre de base de datos** (`ODOO_DB`)
4. **La URL del servidor MCP compartido** (`MCP_SERVER_URL`)

## 🔒 Seguridad

- ✅ Cada cliente usa SUS propias credenciales
- ✅ El servidor NO almacena credenciales
- ✅ Las credenciales se envían con cada petición
- ✅ Cada cliente solo accede a SU Odoo

## 💡 Ventajas del Modo Multi-Tenant

1. **Un solo servidor para todos**: No necesitas deploy por cliente
2. **Sin instalación local**: Los clientes solo configuran Claude
3. **Escalable**: Agrega clientes sin cambiar el servidor
4. **Económico**: $5/mes en Digital Ocean sirve muchos clientes
5. **Centralizado**: Actualizas una vez, todos reciben mejoras

## 🛠️ Configuración Avanzada

### Para limitar acceso (opcional):

Si quieres que solo ciertos clientes usen tu servidor, puedes agregar autenticación:

```python
# En mcp_server.py, agregar validación de token
MCP_ACCESS_TOKEN = os.environ.get('MCP_ACCESS_TOKEN')

if request.headers.get('X-MCP-Token') != MCP_ACCESS_TOKEN:
    return web.json_response({'error': 'Unauthorized'}, status=401)
```

Luego cada cliente debe incluir:
```json
{
  "env": {
    "MCP_ACCESS_TOKEN": "token-compartido",
    ...
  }
}
```

## 📊 Monitoreo

En Digital Ocean Dashboard puedes ver:
- Cantidad de requests
- Clientes activos
- Logs en tiempo real
- Uso de recursos

## 🚀 Ejemplos de Uso

Una vez configurado, cada cliente puede usar Claude con su propio Odoo:

**Cliente A (empresa de retail):**
- "Muéstrame el inventario de la tienda principal"
- "Crea una orden de compra para el proveedor X"

**Cliente B (empresa de servicios):**
- "Lista los proyectos activos de este mes"
- "Actualiza las horas trabajadas del empleado Y"

**Cliente C (empresa manufacturera):**
- "Verifica el stock de materias primas"
- "Genera una orden de producción"

Cada uno accede SOLO a su propia información.

## 🤝 Contribuir

Si quieres mejorar el servidor multi-tenant:
1. Fork este repo
2. Haz tus cambios
3. Pull request
4. ¡Todos los clientes se benefician!

## 📝 Licencia

Este proyecto es de código abierto. Úsalo como quieras.

---

**¿Preguntas?** Abre un issue en GitHub.