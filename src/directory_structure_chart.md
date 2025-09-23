# MCP GitHub src/ Directory Structure Chart

```
src/
├── 📁 Core MCP Components
│   └── mcp_instance.py                    # MCP instance management and configuration
│
├── 📁 Utility Modules  
│   ├── misc_tools.py                      # Miscellaneous utility tools
│   ├── utils.py                           # General utility functions
│   └── retrieve_api_endpoint_tool.py      # API endpoint retrieval functionality
│
├── 📁 External Service Integration
│   └── openportal_tools.py                # OpenPortal service integration tools
│
├── 📁 Authentication
│   └── waldur_auth_tool.py                # Waldur authentication and authorization
│
├── 📁 Waldur API Operations
│   ├── waldur_get_tools.py                # GET operations for Waldur API
│   ├── waldur_post_tools.py               # POST operations for Waldur API  
│   ├── waldur_patch_tools.py              # PATCH operations for Waldur API
│   └── waldur_delete_tools.py             # DELETE operations for Waldur API
│
└── 📁 Prompts & Templates
    └── prompts/
        └── task_planner.py                # Task planning prompt templates and logic
```

## Directory Structure Summary

### File Count
- **Total Files**: 11 Python files
- **Total Directories**: 2 (src + prompts subdirectory)

### Functional Organization

#### 1. **Core Infrastructure** (1 file)
- `mcp_instance.py` - Central MCP system management

#### 2. **Utilities & Tools** (3 files)  
- `misc_tools.py` - General purpose tools
- `utils.py` - Common utility functions
- `retrieve_api_endpoint_tool.py` - API discovery tools

#### 3. **Authentication Layer** (1 file)
- `waldur_auth_tool.py` - Security and access management

#### 4. **Waldur API Interface** (4 files)
- Complete CRUD operations coverage:
  - **GET**: Data retrieval operations
  - **POST**: Data creation operations  
  - **PATCH**: Data update operations
  - **DELETE**: Data removal operations

#### 5. **External Integrations** (1 file)
- `openportal_tools.py` - Third-party service connectivity

#### 6. **Prompts & AI Logic** (1 file)
- `prompts/task_planner.py` - AI task planning and orchestration

## Architecture Notes

This directory structure follows a clean separation of concerns:

- **Single Responsibility**: Each file handles specific operations (auth, CRUD, utilities)
- **API-First Design**: Comprehensive HTTP method coverage for Waldur integration  
- **Modular Organization**: Clear boundaries between authentication, operations, and utilities
- **AI Integration**: Dedicated prompt management for intelligent task planning

The structure supports scalable MCP server development with clear extension points for additional tools and integrations.
