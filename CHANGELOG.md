# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-06-19

### Added
- **Write Operations**: Enabled full CRUD functionality with `create_record`, `update_record`, and `delete_record` tools (#5)

### Changed
- **Resource Simplification**: Removed query parameters from resource URIs due to FastMCP limitations - use tools for advanced queries (#4)

### Fixed
- **Domain Parameter Parsing**: Fixed `search_records` tool to accept both JSON strings and Python-style domain strings, supporting various format variations

## [0.1.2] - 2025-06-19

### Added
- **Resource Discovery**: Added `list_resource_templates` tool to provide resource URI template information
- **HTTP Transport**: Added streamable-http transport support for web and remote access

## [0.1.1] - 2025-06-16

### Fixed
- **HTTPS Connection**: Fixed SSL/TLS support by using `SafeTransport` for HTTPS URLs instead of regular `Transport`
- **Database Validation**: Skip database existence check when database is explicitly configured, as listing may be restricted for security

## [0.1.0] - 2025-06-08

### Added

#### Core Features
- **MCP Server**: Full Model Context Protocol implementation using FastMCP with stdio transport
- **Dual Authentication**: API key and username/password authentication
- **Resource System**: Complete `odoo://` URI schema with 5 operations (record, search, browse, count, fields)
- **Tools**: `search_records`, `get_record`, `list_models` with smart field selection
- **Auto-Discovery**: Automatic database detection and connection management

#### Data & Performance
- **LLM-Optimized Output**: Hierarchical text formatting for AI consumption
- **Connection Pooling**: Efficient connection reuse with health checks
- **Pagination**: Smart handling of large datasets
- **Caching**: Performance optimization for frequently accessed data
- **Error Handling**: Comprehensive error sanitization and user-friendly messages

#### Security & Access Control
- **Multi-layered Security**: Odoo permissions + MCP-specific access controls
- **Session Management**: Automatic credential injection and session handling
- **Audit Logging**: Complete operation logging for security

## Limitations
- **No Prompts**: Guided workflows not available
- **Alpha Status**: API may change before 1.0.0

**Note**: This alpha release provides production-ready data access for Odoo via AI assistants.