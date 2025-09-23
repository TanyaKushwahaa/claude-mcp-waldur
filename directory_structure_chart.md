# Claude MCP Waldur - Directory Structure Chart

```
claude-mcp-waldur/
├── .env                                    # Environment variables (local config)
├── .env.example                           # Environment variables template
├── .git/                                  # Git repository data
├── .gitignore                             # Git ignore file
├── .python-version                        # Python version specification
├── .venv/                                 # Virtual environment directory
├── config.py                              # Main configuration file
├── pyproject.toml                         # Python project configuration
├── README.md                              # Project documentation
├── uv.lock                               # UV package manager lock file
│
├── example_config_claude/
│   └── claude_desktop_config_example.json # Example Claude desktop configuration
│
├── servers/
│   ├── read-only.py                       # Read-only MCP server
│   └── read-write.py                      # Read-write MCP server
│
└── src/
    ├── directory_structure_chart.md       # This file (directory structure chart)
    ├── mcp_instance.py                    # MCP instance configuration
    ├── misc_tools.py                      # Miscellaneous utility tools
    ├── openportal_tools.py                # OpenPortal-specific tools
    ├── retrieve_api_endpoint_tool.py      # API endpoint retrieval tool
    ├── utils.py                           # General utility functions
    ├── waldur_auth_tool.py                # Waldur authentication tools
    ├── waldur_delete_tools.py             # Waldur DELETE operation tools
    ├── waldur_get_tools.py                # Waldur GET operation tools
    ├── waldur_patch_tools.py              # Waldur PATCH operation tools
    ├── waldur_post_tools.py               # Waldur POST operation tools
    │
    └── prompts/
        └── task_planner.py                # Task planning prompt utilities
```

## File Categories

### 📁 **Configuration Files**
- `.env` / `.env.example` - Environment configuration
- `config.py` - Main application configuration
- `pyproject.toml` - Python project and dependency management
- `.python-version` - Python version specification

### 🖥️ **MCP Servers**
- `servers/read-only.py` - Read-only operations server
- `servers/read-write.py` - Read-write operations server

### 🔧 **Core Source Code**
- `src/mcp_instance.py` - MCP instance management
- `src/utils.py` - General utilities
- `src/misc_tools.py` - Miscellaneous tools

### 🌐 **API Tools**
- `src/waldur_auth_tool.py` - Authentication
- `src/waldur_get_tools.py` - GET operations
- `src/waldur_post_tools.py` - POST operations
- `src/waldur_patch_tools.py` - PATCH operations  
- `src/waldur_delete_tools.py` - DELETE operations
- `src/retrieve_api_endpoint_tool.py` - Endpoint retrieval
- `src/openportal_tools.py` - OpenPortal integration

### 🤖 **AI/Prompt Tools**
- `src/prompts/task_planner.py` - Task planning utilities

### 📖 **Documentation & Examples**
- `README.md` - Project documentation
- `example_config_claude/claude_desktop_config_example.json` - Configuration example
- `directory_structure_chart.md` - This structure chart

### 🔒 **Development & Version Control**
- `.git/` - Git repository data
- `.gitignore` - Git ignore rules
- `.venv/` - Python virtual environment
- `uv.lock` - Package lock file

---

**Total**: 22 files across 5 directories
