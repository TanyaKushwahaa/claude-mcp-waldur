"""
read-only.py
Part of the MCP (Model Context Protocol) project: a protocol for managing AI models and tools.
This script imports various MCP tools to connect Claude (MCP Host) with Waldur for HPC resource 
management and project insights.

"""
from config import validate_config

error = validate_config()
if error:
    print(f"Configuration error: {error}") # just to alert you when running script directly

# Tools
from src.waldur_get_tools import get_from_waldur, get_uuid
from src.waldur_auth_tool import get_waldur_api_token
from src.misc_tools import greet_user, check_query_type, infer_http_method
from src.retrieve_api_endpoint_tool import retrieve_api_endpoint

# Prompts
from src.prompts import task_planner

from src.mcp_instance import mcp

if __name__=="__main__":
    mcp.run(transport="stdio")