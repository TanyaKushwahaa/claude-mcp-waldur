"""
mcp_instance.py

Creates and exports the MCP server instance for use by other modules.

Uses FastMCP from the MCP framework to create the instance.

"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp_tools")