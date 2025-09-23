import os
import json
import httpx
from src.mcp_instance import mcp

import environ

env = environ.Env(
    WALDUR_BASE_URL=(str, ''),           # (type, default_if_missing)
    MCP_DATA_PATH=(str, ''),
    VERIFY_SSL=(bool, False),            # This will properly convert "False" string to False boolean
)
# This line reads the .env file
environ.Env.read_env()

WALDUR_BASE_URL = env("WALDUR_BASE_URL")
MCP_DATA_PATH = env("MCP_DATA_PATH")
VERIFY_SSL=env("VERIFY_SSL")

def validate_config():
    missing = []
    if not WALDUR_BASE_URL:
        missing.append("WALDUR_BASE_URL")
    if missing:
        return f"Missing environment variables: {', '.join(missing)}"
    return None