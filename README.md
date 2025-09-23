# Claude MCP Waldur Integration

This project provides MCP (Model Context Protocol) servers and tools for interacting with [Waldur API Documentation](https://docs.waldur.com/) through Claude.

It includes both read-only and read-write MCP servers, utility tools, and Waldur API operation modules.

## Features :rocket:

- **Two MCP servers**
  - **read-only**: Safe, non-destructive queries.
  - **read-write**: Full access to create, update, and delete resources in Waldur.
- Waldur API integration
  - Separate modules for GET, POST, PATCH, and DELETE.
  - Authentication helpers (waldur_auth_tool.py) to manage tokens and access.
- Task planning with Claude
  - prompts/task_planner.py to structure and guide actions on which tools to use and in what order.
- Utility modules
  - Miscellaneous helpers and reusable functions.
  - Endpoint retrieval tool (retrieve_api_endpoint_tool) to dynamically discover API routes.
- Extensible design
  - Modular src/ structure for easy contributions and new tools.

## Project Structure :open_file_folder:

claude-mcp-waldur/
├── .env                     # Environment variables (local config)
├── .env.example             # Template for environment variables
├── config.py                # Main configuration file
├── pyproject.toml           # Python project configuration
├── README.md                # Project documentation
├── uv.lock                  # UV package manager lock file
│
├── example_config_claude/
│   └── claude_desktop_config_example.json
│
├── servers/
│   ├── read-only.py         # Read-only MCP server
│   └── read-write.py        # Read-write MCP server
│
└── src/
    ├── mcp_instance.py      # MCP instance configuration
    ├── misc_tools.py        # Miscellaneous tools
    ├── openportal_tools.py  # OpenPortal-specific tools
    ├── retrieve_api_endpoint_tool.py
    ├── utils.py             # General utilities
    ├── waldur_auth_tool.py  # Waldur authentication
    ├── waldur_delete_tools.py
    ├── waldur_get_tools.py
    ├── waldur_patch_tools.py
    ├── waldur_post_tools.py
    │
    └── prompts/
        └── task_planner.py  # Prompt utilities for planning

## Installation :gear:

git clone https://github.com/yourusername/claude-mcp-waldur.git
cd claude-mcp-waldur
Create and activate a virtual environment:
python -m venv .venv
source .venv/bin/activate   # On Linux/Mac
.venv\Scripts\activate      # On Windows
Install dependencies with [UV](https://docs.astral.sh/uv/)
uv sync

## Configuration :key:

This project requires environment variables defined in a .env file in the root directory.

1. Copy the example config:
  cp .env.example .env
2. Edit .env and fill in your Waldur API base URL, tokens, and other values.
Example .env.example:
  WALDUR_BASE_URL=https://waldur.example.com/api/
  MCP_DATA_PATH=./data
  VERIFY_SSL=True
3. Place the claude_desktop_config_example.json file in the Claude config directory on your system (e.g., AppData\Roaming\Claude on Windows or ~/.config/Claude on Linux/Mac).

## Documentation :book:

- [Waldur API Reference](https://docs.waldur.com/latest/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/docs/getting-started/intro)

## Contributing

1. Fork the repo
2. Create a feature branch (git checkout -b feature/my-tool)
3. Commit your changes (git commit -m 'Add my new tool')
4. Push to your fork and open a PR

## License :scroll:

This project is licensed under the terms of the MIT license.
MIT License — see [LICENSE](./LICENSE) for details.
